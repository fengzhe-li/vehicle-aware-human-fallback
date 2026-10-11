"""AutoVLA physical action codebook tokenizer and SE(2) trajectory rollout decoder.

Implements exact trajectory decoding compatible with `ucla-mobility/AutoVLA`
(`autovla/models/tokenizer/action_tokenizer.py`), mapping discrete `<action_k>`
tokens (`k in [0, 2047]`) via the 2048-entry vehicle bounding-box displacement
codebook (`agent_vocab.pkl`) into 10 time-indexed SE(2) ego poses `(x_m, y_m, heading_rad)`
over a 5.0 s horizon (`dt = 0.5 s`).
"""

from __future__ import annotations

import math
import pickle
import re
from pathlib import Path

import numpy as np

from extensions.vla_handover_feasibility.schemas import TrajectoryWaypoint


DEFAULT_CODEBOOK_PATH = Path(__file__).resolve().parent / "data" / "agent_vocab.pkl"
BASE_QWEN_VOCAB_SIZE = 151665
ACTION_VOCAB_SIZE = 2048
DEFAULT_DT_S = 0.5
DEFAULT_HORIZON_STEPS = 10
ACTION_TAG_REGEX = re.compile(r"<action_(\d+)>")


def wrap_angle_rad(angle_rad: float | np.ndarray) -> float | np.ndarray:
    """Wrap angle(s) in radians to [-pi, pi]."""
    wrapped = (angle_rad + math.pi) % (2.0 * math.pi) - math.pi
    if isinstance(angle_rad, (int, float, np.floating)):
        return float(wrapped)
    return wrapped


def corners_to_center_and_heading(corners: np.ndarray) -> np.ndarray:
    """Convert 4-corner vehicle bounding box coordinates (..., 4, 2) to pose (..., 3) = (x, y, heading).

    Matches `ActionTokenizer.rollout` in `ucla-mobility/AutoVLA`
    (`autovla/models/tokenizer/action_tokenizer.py`, lines 110-112):
    - `center = corners.mean(axis=-2)`
    - `diff_xy = corners[..., 0, :] - corners[..., 3, :]`
    - `heading = arctan2(diff_xy[..., 1], diff_xy[..., 0])`
    """
    arr = np.asarray(corners, dtype=np.float64)
    if arr.shape[-2:] != (4, 2):
        raise ValueError(f"Expected corners shape (..., 4, 2), got {arr.shape}")
    center = arr.mean(axis=-2)  # (..., 2)
    direction = arr[..., 0, :] - arr[..., 3, :]
    heading = np.arctan2(direction[..., 1], direction[..., 0])[..., None]  # (..., 1)
    return np.concatenate([center, heading], axis=-1)


class AutoVLAActionTokenizer:
    """Decodes AutoVLA discrete `<action_k>` tokens into physical ego-frame trajectories."""

    def __init__(
        self,
        codebook_path: str | Path = DEFAULT_CODEBOOK_PATH,
        base_vocab_offset: int = BASE_QWEN_VOCAB_SIZE,
        dt_s: float = DEFAULT_DT_S,
    ) -> None:
        self.codebook_path = Path(codebook_path)
        if not self.codebook_path.exists():
            raise FileNotFoundError(f"AutoVLA action codebook not found at {self.codebook_path}")
        with open(self.codebook_path, "rb") as f:
            raw = pickle.load(f)
        if "token_all" not in raw or "veh" not in raw["token_all"]:
            raise ValueError(f"Invalid codebook structure in {self.codebook_path}; expected ['token_all']['veh']")
        # Shape: (2048, 6, 4, 2)
        self.raw_corners = np.asarray(raw["token_all"]["veh"], dtype=np.float64)
        if self.raw_corners.ndim != 4 or self.raw_corners.shape[2:] != (4, 2):
            raise ValueError(f"Unexpected codebook shape: {self.raw_corners.shape}")
        # Shape: (2048, 6, 3) where last dim is (dx_m, dy_m, dheading_rad)
        self.codebook_poses = corners_to_center_and_heading(self.raw_corners)
        self.n_bins = int(self.codebook_poses.shape[0])
        self.base_vocab_offset = int(base_vocab_offset)
        self.dt_s = float(dt_s)

    @property
    def step_displacements(self) -> np.ndarray:
        """Return (2048, 3) relative SE(2) displacements at the end of each 0.5 s token step."""
        return self.codebook_poses[:, -1, :]

    def extract_codebook_indices_from_text(self, text: str) -> list[int]:
        """Extract integer codebook indices k from `<action_k>` tags in generated text."""
        matches = ACTION_TAG_REGEX.findall(text)
        indices = [int(m) for m in matches]
        for idx in indices:
            if idx < 0 or idx >= self.n_bins:
                raise ValueError(f"Action index {idx} out of valid codebook range [0, {self.n_bins - 1}]")
        return indices

    def extract_codebook_indices_from_token_ids(self, token_ids: list[int] | np.ndarray) -> list[int]:
        """Extract codebook indices from raw LLM token IDs (`token_id >= base_vocab_offset`)."""
        indices: list[int] = []
        for tid in token_ids:
            tid_int = int(tid)
            if tid_int >= self.base_vocab_offset:
                code_idx = tid_int - self.base_vocab_offset
                if 0 <= code_idx < self.n_bins:
                    indices.append(code_idx)
        return indices

    def rollout_indices(self, action_indices: list[int] | np.ndarray) -> np.ndarray:
        """Roll out a sequence of discrete action codebook indices into ego-frame poses (N, 3).

        Matches `ActionTokenizer.rollout` in `ucla-mobility/AutoVLA`:
        At each step k, the relative displacement `(dx_rel, dy_rel, dpsi_rel)` from
        `codebook_poses[a_k, -1]` is rotated by the accumulated heading `psi_{k-1}` and
        added to `(x_{k-1}, y_{k-1})`.
        """
        idx_arr = np.asarray(action_indices, dtype=np.int64)
        if idx_arr.ndim != 1:
            raise ValueError(f"Expected 1D sequence of action indices, got shape {idx_arr.shape}")
        if len(idx_arr) == 0:
            return np.zeros((0, 3), dtype=np.float64)
        if np.any(idx_arr < 0) or np.any(idx_arr >= self.n_bins):
            raise ValueError(f"Action indices out of range [0, {self.n_bins - 1}]: {idx_arr.tolist()}")

        cur_x = 0.0
        cur_y = 0.0
        cur_heading = 0.0
        poses = np.zeros((len(idx_arr), 3), dtype=np.float64)

        for step_i, code_idx in enumerate(idx_arr):
            rel = self.codebook_poses[int(code_idx), -1]  # (dx, dy, dheading)
            dx_rel = float(rel[0])
            dy_rel = float(rel[1])
            dheading = float(rel[2])
            cos_h = math.cos(cur_heading)
            sin_h = math.sin(cur_heading)
            next_x = cur_x + (dx_rel * cos_h - dy_rel * sin_h)
            next_y = cur_y + (dx_rel * sin_h + dy_rel * cos_h)
            next_heading = float(wrap_angle_rad(cur_heading + dheading))
            poses[step_i, 0] = next_x
            poses[step_i, 1] = next_y
            poses[step_i, 2] = next_heading
            cur_x, cur_y, cur_heading = next_x, next_y, next_heading

        return poses

    def decode_indices_to_waypoints(self, action_indices: list[int] | np.ndarray) -> list[TrajectoryWaypoint]:
        """Decode codebook indices into time-indexed `TrajectoryWaypoint` instances."""
        poses = self.rollout_indices(action_indices)
        waypoints: list[TrajectoryWaypoint] = []
        for i in range(poses.shape[0]):
            t_s = round((i + 1) * self.dt_s, 4)
            waypoints.append(
                TrajectoryWaypoint(
                    step=i + 1,
                    t_s=t_s,
                    x_m=round(float(poses[i, 0]), 5),
                    y_m=round(float(poses[i, 1]), 5),
                    heading_rad=round(float(poses[i, 2]), 5),
                )
            )
        return waypoints

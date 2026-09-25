"""Canonical data loader for the TU Delft L3 Takeover Dataset (D003).

Provides reproducible access to the 513 trials across 57 participants, mapping
raw simulation channels to standardized canonical names while preserving source
field traceability.

LEGACY (Phase R1 notice, 2026-09-22): kept unchanged for the pre-audit H1 scripts
and existing tests. Known limitations: the raw laneGap header is
"[00].VehicleUpdate-roadInfo-laneGap.0,time" and its cells are "<value>,<time>"
pairs, so the `lane_gap` column here is always NaN; rows with an empty timestamp
(the trailing export footer) are dropped silently; cells are coerced by pandas.
New work must use `src/data/d003_ingest.py`.
"""

from __future__ import annotations

import io
import os
import re
import warnings
import zipfile
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

RAW_TO_CANONICAL_COLUMNS: Dict[str, str] = {
    "time": "time",
    "[00].VehicleUpdate-pos.001": "pos_x",
    "[00].VehicleUpdate-pos.002": "pos_y",
    "[00].VehicleUpdate-pos.003": "pos_z",
    "[00].VehicleUpdate-pos.004": "roll",
    "[00].VehicleUpdate-pos.005": "pitch",
    "[00].VehicleUpdate-pos.006": "yaw",
    "[00].VehicleUpdate-COGPos.001": "cog_x",
    "[00].VehicleUpdate-COGPos.002": "cog_y",
    "[00].VehicleUpdate-COGPos.003": "cog_z",
    "[00].VehicleUpdate-speed.001": "longitudinal_speed",
    "[00].VehicleUpdate-speed.002": "lateral_speed",
    "[00].VehicleUpdate-speed.003": "vertical_speed",
    "[00].VehicleUpdate-accel.001": "longitudinal_acceleration",
    "[00].VehicleUpdate-accel.002": "lateral_acceleration",
    "[00].VehicleUpdate-accel.003": "vertical_acceleration",
    "[00].VehicleUpdate-state": "vehicle_state",
    "[00].VehicleUpdate-lights": "vehicle_lights",
    "[00].VehicleUpdate-steeringWheelAngle": "steering_angle",
    "[00].VehicleUpdate-steeringWheelSpeed": "steering_speed",
    "[00].VehicleUpdate-steeringTorq": "steering_torque",
    "[00].VehicleUpdate-accelerator": "accelerator",
    "[00].VehicleUpdate-brake": "brake_force",
    "[00].VehicleUpdate-indicators": "indicators",
    "[00].VehicleUpdate-roadInfo-roadId.0": "road_id",
    "[00].VehicleUpdate-roadInfo-roadAbscissa.0": "road_abscissa",
    "[00].VehicleUpdate-roadInfo-roadGap.0": "road_gap",
    "[00].VehicleUpdate-roadInfo-roadAngle.0": "road_angle",
    "[00].VehicleUpdate-roadInfo-laneId.0": "lane_id",
    "[00].VehicleUpdate-roadInfo-laneGap.0": "lane_gap",
    "[72 (Time/Time_Takeover_Request)].ExportChannel-val": "TOR_request",
    "[73 (Time/Time_Manual_Start)].ExportChannel-val": "manual_start",
    "[74 (Time/Time_Manual_Stop)].ExportChannel-val": "manual_stop",
    "[77 (Time/Time_TTC)].ExportChannel-val": "TTC",
    "[78 (Time/Time_Lane_Change)].ExportChannel-val": "lane_change_time",
    "[82 (Distance/Distance_to_Following_Vehicle)].ExportChannel-val": "distance_to_following",
    "[83 (Distance/Distance_to_Leading_Vehicle_Next_Lane)].ExportChannel-val": "distance_to_lead_left",
    "[84 (Distance/Distance_to_Following_Vehicle_Next_Lane)].ExportChannel-val": "distance_to_following_left",
    "[85 (Distance/Distance_to_Construction)].ExportChannel-val": "distance_to_obstacle",
}

CANONICAL_TO_RAW_COLUMNS: Dict[str, str] = {v: k for k, v in RAW_TO_CANONICAL_COLUMNS.items()}


@dataclass(frozen=True)
class TrialMeta:
    """Metadata parsed from a trial filename."""
    density: int
    nback: int
    participant_id: int
    scenario_id: str
    trial_id: str
    relative_path: str


def parse_trial_filename(path_or_filename: str) -> Optional[TrialMeta]:
    """Extract scenario and participant metadata from a file path."""
    basename = os.path.basename(path_or_filename)
    # Expected pattern: density_{0|10|20}_nback_{0|1|2}_id_{1..57}_simulator_data.csv
    match = re.search(r"density_(\d+)_nback_(\d+)_id_(\d+)_simulator_data\.csv", basename)
    if not match:
        return None
    density = int(match.group(1))
    nback = int(match.group(2))
    pid = int(match.group(3))
    scenario_id = f"density_{density}_nback_{nback}"
    trial_id = f"{scenario_id}_id_{pid}"
    return TrialMeta(
        density=density,
        nback=nback,
        participant_id=pid,
        scenario_id=scenario_id,
        trial_id=trial_id,
        relative_path=path_or_filename,
    )


class D003Dataset:
    """Interface to the TU Delft L3 Takeover Dataset (D003)."""

    def __init__(self, archive_path: str):
        warnings.warn(
            "D003Dataset is the DEPRECATED pre-audit loader (all-NaN lane_gap, silent footer drop, "
            "pandas coercion). It is kept only to reproduce historical outputs. Use "
            "src.data.d003_ingest.D003Archive for any new work.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.archive_path = archive_path
        if not os.path.exists(archive_path):
            raise FileNotFoundError(f"D003 archive not found at: {archive_path}")
        self._zip_file: Optional[zipfile.ZipFile] = None
        self._trial_index: Optional[List[TrialMeta]] = None

    @property
    def zip_ref(self) -> zipfile.ZipFile:
        if self._zip_file is None:
            self._zip_file = zipfile.ZipFile(self.archive_path, "r")
        return self._zip_file

    def list_trials(self) -> List[TrialMeta]:
        """Enumerate all simulator trial files in the archive."""
        if self._trial_index is not None:
            return self._trial_index

        trials = []
        for name in self.zip_ref.namelist():
            if name.startswith("__MACOSX"):
                continue
            if name.endswith("_simulator_data.csv"):
                meta = parse_trial_filename(name)
                if meta is not None:
                    trials.append(meta)

        trials.sort(key=lambda m: (m.participant_id, m.density, m.nback))
        self._trial_index = trials
        return trials

    def load_trial(self, trial: Union[TrialMeta, str]) -> Tuple[pd.DataFrame, TrialMeta]:
        """Load a trial into a standardized DataFrame with canonical columns.

        Returns:
            (DataFrame with canonical column names, TrialMeta object)
        """
        if isinstance(trial, str):
            meta = parse_trial_filename(trial)
            if meta is None:
                # Find matching trial in index
                matches = [t for t in self.list_trials() if trial in t.relative_path or trial == t.trial_id]
                if not matches:
                    raise KeyError(f"Trial not found: {trial}")
                meta = matches[0]
        else:
            meta = trial

        raw_bytes = self.zip_ref.read(meta.relative_path)
        # Parse CSV
        df_raw = pd.read_csv(io.BytesIO(raw_bytes))
        # Drop any trailing empty lines where time is NaN
        if "time" in df_raw.columns:
            df_raw = df_raw.dropna(subset=["time"]).reset_index(drop=True)

        # Build canonical dataframe
        df_canonical = pd.DataFrame()
        raw_col_map: Dict[str, str] = {}

        for raw_col in df_raw.columns:
            # Handle potential whitespace or comma artifacts in raw names
            cleaned = raw_col.strip()
            if cleaned in RAW_TO_CANONICAL_COLUMNS:
                canonical_name = RAW_TO_CANONICAL_COLUMNS[cleaned]
                df_canonical[canonical_name] = df_raw[raw_col]
                raw_col_map[canonical_name] = raw_col
            else:
                # Keep unmapped columns with stripped name
                df_canonical[cleaned] = df_raw[raw_col]
                raw_col_map[cleaned] = raw_col

        # Ensure standard canonical columns are present (fill with NaN if absent from raw)
        for canon_col in CANONICAL_TO_RAW_COLUMNS.keys():
            if canon_col not in df_canonical.columns:
                df_canonical[canon_col] = np.nan

        # Attach metadata to DataFrame attrs
        df_canonical.attrs["meta"] = meta
        df_canonical.attrs["raw_to_canonical"] = RAW_TO_CANONICAL_COLUMNS
        df_canonical.attrs["source_columns"] = raw_col_map

        # Add trial context columns directly
        df_canonical["participant_id"] = meta.participant_id
        df_canonical["scenario_id"] = meta.scenario_id
        df_canonical["density"] = meta.density
        df_canonical["nback"] = meta.nback
        df_canonical["trial_id"] = meta.trial_id

        return df_canonical, meta

    def load_data_dictionary(self) -> pd.DataFrame:
        """Load data_dictionary.csv if present in archive."""
        for name in self.zip_ref.namelist():
            if name.endswith("data_dictionary.csv") and not name.startswith("__MACOSX"):
                data = self.zip_ref.read(name)
                return pd.read_csv(io.BytesIO(data))
        raise FileNotFoundError("data_dictionary.csv not found in archive")

    def load_driver_characteristics(self) -> pd.DataFrame:
        """Load driver_characteristic_answers.csv if present."""
        for name in self.zip_ref.namelist():
            if name.endswith("driver_characteristic_answers.csv") and not name.startswith("__MACOSX"):
                data = self.zip_ref.read(name)
                return pd.read_csv(io.BytesIO(data))
        raise FileNotFoundError("driver_characteristic_answers.csv not found in archive")

    def close(self):
        if self._zip_file is not None:
            self._zip_file.close()
            self._zip_file = None

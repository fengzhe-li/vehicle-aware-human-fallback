"""Phase R6A test suite: final thesis figure rendering and manifest freeze.

Invariants verified:
- frozen figure list completeness (F1–F10, FA1–FA2) in vector and preview formats
- manifest and documentation consistency
- caption consistency across code, manifest and documentation
- claim-ID validity against research/R5A_CLAIM_LEDGER.csv
- blocked/withdrawn-claim exclusion (no overclaims or withdrawn claims in captions)
- L41 qualifier preservation (R3B assumed braking-delay interval as a model assumption)
- L42 scope preservation (table/text only, not in figure claims)
- F4/L34 requirement (L34 cited and discussed in F4 caption)
- deterministic rendering (byte-for-byte identical output across independent renders)
- figure outputs not git-ignored
- scientific result files unchanged
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import re
import struct
import subprocess
import sys
import tempfile
import zlib
from typing import Dict, List, Tuple

import matplotlib
import numpy as np
import pytest
from PIL import Image

from src.figures import r6a_thesis_figures as r6a

MANIFEST_PATH = "thesis/figures/figure_manifest.json"
DOC_PATH = "docs/R6A_FINAL_FIGURES.md"
LEDGER_PATH = "research/R5A_CLAIM_LEDGER.csv"
BLUEPRINT_PATH = "docs/R5B_THESIS_BLUEPRINT.md"
FIGURES_DIR = "thesis/figures"

FROZEN_FIGURE_IDS = {
    "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "FA1", "FA2"
}

BANNED_OVERCLAIM_PHRASES = (
    "first ever",
    "novel closed-form",
    "reaction time is",
    "intention time is",
    "drivers learned",
    "is safe",
    "unsafe",
    "safety envelope",
    "p(safe",
    "validated system-level",
    "gap acceptance",
    "predicts",
    "reaction time decreases",
    "combined recoverability",
    "recoverability score",
)


@pytest.fixture(scope="module")
def manifest() -> Dict[str, object]:
    assert os.path.exists(MANIFEST_PATH), f"Manifest missing: {MANIFEST_PATH}"
    with open(MANIFEST_PATH, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert os.path.exists(DOC_PATH), f"Documentation missing: {DOC_PATH}"
    with open(DOC_PATH, encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def ledger() -> Dict[str, Dict[str, str]]:
    assert os.path.exists(LEDGER_PATH), f"Ledger missing: {LEDGER_PATH}"
    with open(LEDGER_PATH, newline="", encoding="utf-8") as fh:
        return {r["claim_id"]: r for r in csv.DictReader(fh)}


@pytest.fixture(scope="module")
def blueprint_text() -> str:
    assert os.path.exists(BLUEPRINT_PATH), f"Blueprint missing: {BLUEPRINT_PATH}"
    with open(BLUEPRINT_PATH, encoding="utf-8") as fh:
        return fh.read()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# 1. Frozen figure-list completeness
# ---------------------------------------------------------------------------


def test_frozen_figure_list_completeness(manifest, blueprint_text):
    manifest_fids = set(manifest["figures"].keys())
    assert manifest_fids == FROZEN_FIGURE_IDS, f"Manifest figure IDs mismatch: {manifest_fids ^ FROZEN_FIGURE_IDS}"
    assert set(r6a.FIGURES.keys()) == FROZEN_FIGURE_IDS

    # Check blueprint table includes all frozen figures
    bp_rows = {line.split("|")[1].strip().strip("*") for line in blueprint_text.splitlines() if line.startswith("| ")}
    assert FROZEN_FIGURE_IDS <= bp_rows, f"Blueprint missing figures: {FROZEN_FIGURE_IDS - bp_rows}"

    # Verify both PDF and PNG exist on disk with valid file size
    for fid, spec in manifest["figures"].items():
        base = os.path.join(FIGURES_DIR, spec["file"])
        pdf_path = base + ".pdf"
        png_path = base + ".png"
        assert os.path.isfile(pdf_path), f"Missing PDF for {fid}: {pdf_path}"
        assert os.path.isfile(png_path), f"Missing PNG for {fid}: {png_path}"
        assert os.path.getsize(pdf_path) > 1000, f"PDF too small for {fid}: {pdf_path}"
        assert os.path.getsize(png_path) > 1000, f"PNG too small for {fid}: {png_path}"

    # Ensure no stale extra figure files exist in thesis/figures/
    actual_files = set(os.listdir(FIGURES_DIR))
    expected_files = {"figure_manifest.json"}
    for spec in manifest["figures"].values():
        expected_files.add(f"{spec['file']}.pdf")
        expected_files.add(f"{spec['file']}.png")
    extra_files = actual_files - expected_files
    assert not extra_files, f"Unexpected extra files in {FIGURES_DIR}: {extra_files}"


# ---------------------------------------------------------------------------
# 2. Manifest / documentation consistency
# ---------------------------------------------------------------------------


def test_manifest_documentation_consistency(manifest, doc_text):
    for fid, spec in manifest["figures"].items():
        # Check header
        pattern = rf"### {fid}: .* \(`{spec['file']}`\)"
        assert re.search(pattern, doc_text), f"Missing section in doc for {fid}"

        # Check purpose
        assert spec["purpose"] in doc_text, f"Purpose for {fid} not in documentation"

        # Check outputs
        for out in spec["outputs"]:
            assert f"`{out}`" in doc_text, f"Output {out} for {fid} not in documentation"

        # Check source phase
        assert spec["phase"] in doc_text, f"Phase {spec['phase']} for {fid} not in documentation"

        # Check source paths
        for src in spec["sources"]:
            assert f"`{src}`" in doc_text, f"Source {src} for {fid} not in documentation"

    # Check generation command
    assert manifest["command"] in doc_text


# ---------------------------------------------------------------------------
# 3. Caption consistency
# ---------------------------------------------------------------------------


def test_caption_consistency(manifest, doc_text):
    for fid, spec in manifest["figures"].items():
        canonical_caption = spec["caption"]
        assert canonical_caption == r6a.FIGURES[fid]["caption"]
        assert canonical_caption in doc_text, f"Caption for {fid} missing or drifted in documentation"


# ---------------------------------------------------------------------------
# 4. Claim-ID validity
# ---------------------------------------------------------------------------


def test_claim_id_validity(manifest, ledger):
    for fid, spec in manifest["figures"].items():
        for cid in spec["claims"]:
            assert cid in ledger, f"Figure {fid} references unknown claim {cid}"


# ---------------------------------------------------------------------------
# 5. Blocked / withdrawn-claim exclusion
# ---------------------------------------------------------------------------


def test_blocked_withdrawn_claims_exclusion(manifest, ledger):
    # Withdrawn claims (L36–L40) must never appear in any figure
    withdrawn_cids = {cid for cid, r in ledger.items() if r["status"] == "WITHDRAWN"}
    assert withdrawn_cids

    for fid, spec in manifest["figures"].items():
        assert not (set(spec["claims"]) & withdrawn_cids), f"Figure {fid} cites withdrawn claims: {set(spec['claims']) & withdrawn_cids}"

        # Banned overclaim phrases must not appear in any figure caption
        caption_lower = spec["caption"].lower()
        for banned in BANNED_OVERCLAIM_PHRASES:
            assert banned not in caption_lower, f"Figure {fid} caption contains banned phrase: '{banned}'"

        # Check that BLOCKED claims are only cited as limits / boundaries, not findings
        blocked_cids = [cid for cid in spec["claims"] if ledger[cid]["status"] == "BLOCKED"]
        if blocked_cids:
            if spec.get("boundary"):
                # Boundary figures (F3, F10) must explicitly describe limits
                assert "not identifiable" in caption_lower, f"Boundary figure {fid} caption missing 'not identifiable'"
            else:
                # F1 and F4 cite L04 or L03 to explicitly negate them
                assert any(neg in caption_lower for neg in ("not", "is not", "no d003 human quantity enters")), (
                    f"Non-boundary figure {fid} cites BLOCKED claims {blocked_cids} without explicit negation"
                )


# ---------------------------------------------------------------------------
# 6. L41 qualifier preservation
# ---------------------------------------------------------------------------


def test_l41_qualifier_preservation(manifest):
    # L41 is cited in F9 and FA1
    f9 = manifest["figures"]["F9"]
    fa1 = manifest["figures"]["FA1"]
    assert "L41" in f9["claims"]
    assert "L41" in fa1["claims"]

    # F9 band label and caption must explicitly mark the interval as a model assumption
    assert r6a.T1_BAND_LABEL == "R3B assumed braking-delay interval (1.15–3.0 s)"
    assert "R3B assumed braking-delay interval (1.15–3.0 s)" in f9["caption"]
    assert "model assumption" in f9["caption"].lower()
    assert "no braking timing is implied" in f9["caption"].lower()

    # Forbidden interpretations in F9
    f9_forbidden = [x.lower() for x in f9["forbidden"]]
    assert "driver braking time" in f9_forbidden
    assert "measured reaction time" in f9_forbidden
    assert "observed braking delay" in f9_forbidden
    assert "steering follows effective braking" in f9_forbidden

    # FA1 must also qualify the interval as a model assumption
    assert "model assumption" in fa1["caption"].lower()


# ---------------------------------------------------------------------------
# 7. L42 scope preservation
# ---------------------------------------------------------------------------


def test_l42_scope_preservation(manifest, doc_text):
    # L42 is table and text only (T11 in Chapter 4; station-consistent cells, d0_n1 excluded)
    for fid, spec in manifest["figures"].items():
        assert "L42" not in spec["claims"], f"L42 must not be in figure claims ({fid})"

    # Document must explicitly state L42 scope in governance notes
    assert "L42 is table/text only (T11 in Chapter 4; station-consistent cells, d0_n1 excluded)" in doc_text


# ---------------------------------------------------------------------------
# 8. F4 / L34 requirement
# ---------------------------------------------------------------------------


def test_f4_l34_requirement(manifest):
    f4 = manifest["figures"]["F4"]
    assert "L34" in f4["claims"], "F4 claims must include L34"
    assert "TOR → validated lane crossing shows no clear linear exposure association (not shown)." in f4["caption"]
    assert "not a causal learning effect" in f4["caption"]


# ---------------------------------------------------------------------------
# 9. Outputs not git-ignored
# ---------------------------------------------------------------------------


def test_outputs_not_git_ignored():
    files_to_check = [os.path.join(FIGURES_DIR, f) for f in os.listdir(FIGURES_DIR)]
    res = subprocess.run(
        ["git", "check-ignore", *files_to_check],
        capture_output=True,
        text=True,
    )
    # git check-ignore returns exit code 1 if no files match .gitignore
    assert res.returncode != 0, f"Files are unexpectedly git-ignored: {res.stdout.strip()}"


# ---------------------------------------------------------------------------
# 10. Deterministic rendering
# ---------------------------------------------------------------------------


def _parse_png_chunks_and_scanlines(path: str) -> Tuple[List[Tuple[bytes, bytes, int]], bytes]:
    raw = open(path, "rb").read()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n", f"Invalid PNG signature in {path}"
    pos = 8
    non_idat: List[Tuple[bytes, bytes, int]] = []
    idat_parts: List[bytes] = []
    while pos < len(raw):
        length = struct.unpack(">I", raw[pos:pos + 4])[0]
        ctype = raw[pos + 4:pos + 8]
        data = raw[pos + 8:pos + 8 + length]
        crc = struct.unpack(">I", raw[pos + 8 + length:pos + 12 + length])[0]
        if ctype == b"IDAT":
            idat_parts.append(data)
        else:
            non_idat.append((ctype, data, crc))
        pos += 12 + length
    assert pos == len(raw), f"Trailing bytes after IEND in {path}"
    return non_idat, zlib.decompress(b"".join(idat_parts))


def _extract_pdf_streams(path: str) -> List[bytes]:
    raw = open(path, "rb").read()
    streams: List[bytes] = []
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", raw, re.S):
        try:
            streams.append(zlib.decompress(match.group(1)))
        except zlib.error:
            streams.append(match.group(1))
    return streams


def _assert_pdf_stream_coordinates_match(
    canonical_stream: bytes, fresh_stream: bytes, fname: str, max_abs_pt_tol: float = 1e-9
) -> None:
    canon_lines = canonical_stream.splitlines()
    fresh_lines = fresh_stream.splitlines()
    assert len(canon_lines) == len(fresh_lines), (
        f"PDF stream line count mismatch for {fname}: {len(canon_lines)} vs {len(fresh_lines)}"
    )
    for line_idx, (c_line, f_line) in enumerate(zip(canon_lines, fresh_lines), start=1):
        if c_line == f_line:
            continue
        c_tokens = c_line.decode("latin1").split()
        f_tokens = f_line.decode("latin1").split()
        assert len(c_tokens) == len(f_tokens), (
            f"PDF stream token count mismatch in {fname} line {line_idx}: {c_line!r} vs {f_line!r}"
        )
        for c_tok, f_tok in zip(c_tokens, f_tokens):
            if c_tok == f_tok:
                continue
            try:
                c_val = float(c_tok)
                f_val = float(f_tok)
            except ValueError as exc:
                raise AssertionError(
                    f"Non-numeric PDF operator mismatch in {fname} line {line_idx}: {c_tok!r} vs {f_tok!r}"
                ) from exc
            assert abs(c_val - f_val) <= max_abs_pt_tol, (
                f"PDF coordinate drift in {fname} line {line_idx}: {c_val} vs {f_val}"
            )


def test_deterministic_rendering(manifest):
    is_reference_platform = (
        sys.platform == "darwin"
        and platform.machine() == "arm64"
        and matplotlib.__version__ == "3.11.1"
    )
    with tempfile.TemporaryDirectory() as tmp_dir_1, tempfile.TemporaryDirectory() as tmp_dir_2:
        r6a.run(tmp_dir_1, write_docs=False)
        r6a.run(tmp_dir_2, write_docs=False)

        for tmp_dir in (tmp_dir_1, tmp_dir_2):
            fresh_manifest_path = os.path.join(tmp_dir, "figure_manifest.json")
            assert os.path.isfile(fresh_manifest_path), "Fresh render missing figure_manifest.json"
            with open(fresh_manifest_path, encoding="utf-8") as fh:
                fresh_manifest = json.load(fh)
            assert set(fresh_manifest["figures"].keys()) == set(manifest["figures"].keys())
            for fid, spec in manifest["figures"].items():
                fresh_spec = fresh_manifest["figures"][fid]
                for key in ("file", "phase", "purpose", "claims", "sources", "source_sha256", "caption", "forbidden"):
                    assert fresh_spec[key] == spec[key], f"Manifest drift for {fid}.{key}"

        for fname in sorted(os.listdir(FIGURES_DIR)):
            if fname == "figure_manifest.json":
                continue
            canonical_file = os.path.join(FIGURES_DIR, fname)
            fresh_file_1 = os.path.join(tmp_dir_1, fname)
            fresh_file_2 = os.path.join(tmp_dir_2, fname)
            assert os.path.isfile(fresh_file_1), f"First fresh render missing {fname}"
            assert os.path.isfile(fresh_file_2), f"Second fresh render missing {fname}"

            # 1. Within-environment byte-for-byte determinism across independent renders
            assert sha256_file(fresh_file_1) == sha256_file(fresh_file_2), (
                f"Within-environment non-deterministic render detected for {fname}"
            )

            # 2. Exact byte-for-byte match against frozen reference files on canonical platform
            if is_reference_platform:
                assert sha256_file(canonical_file) == sha256_file(fresh_file_1), (
                    f"Reference-platform byte mismatch detected for {fname}"
                )

            # 3. Cross-platform scientific content and visual equivalence against canonical files
            if fname.endswith(".png"):
                canon_chunks, canon_scanlines = _parse_png_chunks_and_scanlines(canonical_file)
                fresh_chunks, fresh_scanlines = _parse_png_chunks_and_scanlines(fresh_file_1)
                assert canon_chunks == fresh_chunks, (
                    f"PNG non-IDAT chunk metadata mismatch for {fname}"
                )
                canon_rgba = np.asarray(Image.open(canonical_file).convert("RGBA"), dtype=np.int16)
                fresh_rgba = np.asarray(Image.open(fresh_file_1).convert("RGBA"), dtype=np.int16)
                assert canon_rgba.shape == fresh_rgba.shape, f"PNG dimension mismatch for {fname}"

                if fname == "F10_identifiability_boundary.png":
                    # F10 uses curved FancyArrowPatch cubic Beziers that exhibit a 1-LSB (1/255)
                    # anti-aliasing rounding difference at 4 edge pixels between arm64 and x86_64.
                    abs_diff = np.abs(canon_rgba - fresh_rgba)
                    diff_pixels = int(np.any(abs_diff > 0, axis=-1).sum())
                    assert int(abs_diff.max()) <= 1, (
                        f"Max pixel channel diff > 1 LSB for {fname}: {int(abs_diff.max())}"
                    )
                    assert diff_pixels <= 4, (
                        f"Unexpected differing pixel count for {fname}: {diff_pixels}"
                    )
                else:
                    # F1-F9 (including F8_transition_branch_comparison.png), FA1, FA2 must have
                    # 100% identical decompressed scanlines and zero pixel differences across platforms;
                    # only the platform libz DEFLATE stream framing may differ.
                    assert canon_scanlines == fresh_scanlines, (
                        f"Decompressed PNG scanline mismatch for {fname}"
                    )
                    assert np.array_equal(canon_rgba, fresh_rgba), (
                        f"Decoded RGBA pixel mismatch for {fname}"
                    )
            elif fname.endswith(".pdf"):
                canon_streams = _extract_pdf_streams(canonical_file)
                fresh_streams = _extract_pdf_streams(fresh_file_1)
                assert len(canon_streams) == len(fresh_streams) and len(canon_streams) > 0, (
                    f"PDF stream count mismatch for {fname}"
                )
                if fname == "F9_steering_sequence_vs_assumed_interval.pdf":
                    # F9 stream 0 has a single 1e-10 pt ULP coordinate rounding difference between
                    # arm64 and x86_64; all other streams (fonts/glyphs/resources) are byte-identical.
                    _assert_pdf_stream_coordinates_match(canon_streams[0], fresh_streams[0], fname)
                    assert canon_streams[1:] == fresh_streams[1:], (
                        f"PDF non-primary stream mismatch for {fname}"
                    )
                else:
                    assert canon_streams == fresh_streams, (
                        f"Decompressed PDF content stream mismatch for {fname}"
                    )
                    if matplotlib.__version__ == "3.11.1":
                        assert sha256_file(canonical_file) == sha256_file(fresh_file_1), (
                            f"PDF byte mismatch under matplotlib 3.11.1 for {fname}"
                        )


# ---------------------------------------------------------------------------
# 11. Scientific result files unchanged
# ---------------------------------------------------------------------------


def test_scientific_results_unchanged(manifest):
    # Verify every recorded source hash matches current file on disk
    for fid, spec in manifest["figures"].items():
        for src_path, recorded_sha in spec["source_sha256"].items():
            current_sha = sha256_file(src_path)
            assert current_sha == recorded_sha, f"Source file {src_path} for {fid} was modified"

    # Verify no uncommitted changes in results/ or research/R5A_CLAIM_LEDGER.csv
    diff_res = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", "results/", LEDGER_PATH],
        capture_output=True,
        text=True,
        check=True,
    )
    assert not diff_res.stdout.strip(), f"Uncommitted changes in scientific outputs: {diff_res.stdout.strip()}"

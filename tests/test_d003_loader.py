"""Tests for the D003 TU Delft dataset loader."""

import pytest
from src.data.d003_loader import (
    RAW_TO_CANONICAL_COLUMNS,
    CANONICAL_TO_RAW_COLUMNS,
    parse_trial_filename,
    TrialMeta,
)


def test_column_mapping_bijective():
    """Verify raw-to-canonical and canonical-to-raw mappings are consistent."""
    assert len(RAW_TO_CANONICAL_COLUMNS) == len(CANONICAL_TO_RAW_COLUMNS)
    for raw, canonical in RAW_TO_CANONICAL_COLUMNS.items():
        assert CANONICAL_TO_RAW_COLUMNS[canonical] == raw


def test_parse_trial_filename():
    """Test parsing of standardized TU Delft trial file names."""
    path = "4. simulator_data/density_20_nback_0/density_20_nback_0_id_53_simulator_data.csv"
    meta = parse_trial_filename(path)
    assert meta is not None
    assert meta.density == 20
    assert meta.nback == 0
    assert meta.participant_id == 53
    assert meta.scenario_id == "density_20_nback_0"
    assert meta.trial_id == "density_20_nback_0_id_53"

    # Test irregular or non-matching names
    assert parse_trial_filename("summary.csv") is None
    assert parse_trial_filename(".DS_Store") is None

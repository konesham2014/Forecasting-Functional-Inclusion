"""
tests/test_data.py
Basic data-integrity and pipeline-output tests.
Run: pytest tests/ -v   (from project root)
"""
import os
import pandas as pd
import pytest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RAW = os.path.join(BASE, "data/raw/ethiopia_fi_unified_data.csv")
REF = os.path.join(BASE, "data/raw/reference_codes.csv")
ENRICHED = os.path.join(BASE, "data/processed/ethiopia_fi_enriched.csv")
ASSOC = os.path.join(BASE, "models/association_matrix.csv")
FORECAST = os.path.join(BASE, "models/forecast_access_usage.csv")

VALID_RECORD_TYPES = {"observation", "event", "impact_link", "target"}
VALID_CONFIDENCE = {"high", "medium", "low"}


@pytest.fixture(scope="module")
def raw_df():
    assert os.path.exists(RAW), "Run `python src/build_dataset.py` first"
    return pd.read_csv(RAW)


@pytest.fixture(scope="module")
def enriched_df():
    assert os.path.exists(ENRICHED), "Run `python src/build_dataset.py` first"
    return pd.read_csv(ENRICHED)


def test_raw_file_exists_and_nonempty(raw_df):
    assert len(raw_df) > 0


def test_reference_codes_exists():
    assert os.path.exists(REF)
    ref = pd.read_csv(REF)
    assert len(ref) > 0


def test_record_type_values_are_valid(enriched_df):
    assert set(enriched_df["record_type"].dropna().unique()) <= VALID_RECORD_TYPES


def test_confidence_values_are_valid(enriched_df):
    conf_vals = set(enriched_df["confidence"].dropna().unique())
    assert conf_vals <= VALID_CONFIDENCE


def test_events_have_no_pillar_preassigned(enriched_df):
    """Per schema design: events must NOT be pre-assigned a pillar; effects
    are captured only through impact_link records."""
    events = enriched_df[enriched_df.record_type == "event"]
    assert events["pillar"].fillna("").eq("").all()


def test_impact_links_reference_valid_parent_events(enriched_df):
    events_ids = set(enriched_df[enriched_df.record_type == "event"]["id"])
    links = enriched_df[enriched_df.record_type == "impact_link"]
    assert links["parent_id"].isin(events_ids).all()


def test_enrichment_added_new_records(raw_df, enriched_df):
    assert len(enriched_df) > len(raw_df)


def test_no_duplicate_ids(enriched_df):
    assert enriched_df["id"].is_unique


def test_observation_values_are_reasonable_percentages(enriched_df):
    obs = enriched_df[enriched_df.record_type == "observation"]
    pct_obs = obs[obs.unit.astype(str).str.startswith("pct")]
    assert (pct_obs["value_numeric"] >= 0).all()
    assert (pct_obs["value_numeric"] <= 100).all()


def test_association_matrix_generated():
    if os.path.exists(ASSOC):
        m = pd.read_csv(ASSOC, index_col=0)
        assert m.shape[0] > 0 and m.shape[1] > 0


def test_forecast_output_generated_and_sane():
    if os.path.exists(FORECAST):
        fc = pd.read_csv(FORECAST)
        assert set(fc["scenario"].unique()) == {"pessimistic", "base", "optimistic"}
        assert set(fc["year"].unique()) == {2025, 2026, 2027}
        # optimistic should be >= pessimistic for every year/indicator
        for (ind, yr), grp in fc.groupby(["indicator_code", "year"]):
            pess = grp[grp.scenario == "pessimistic"]["point_forecast"].iloc[0]
            opt = grp[grp.scenario == "optimistic"]["point_forecast"].iloc[0]
            assert opt >= pess

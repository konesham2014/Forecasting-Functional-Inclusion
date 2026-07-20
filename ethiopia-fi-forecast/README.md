# Forecasting Financial Inclusion in Ethiopia

A forecasting system tracking Ethiopia's digital financial transformation,
built for a consortium of development finance institutions, mobile money
operators, and the National Bank of Ethiopia. Built by **Selam Analytics**.

## Project Structure

```
ethiopia-fi-forecast/
├── .github/workflows/unittests.yml   # CI: rebuilds data + runs tests on every push/PR
├── data/
│   ├── raw/                          # Task 1: starter dataset + reference codes
│   │   ├── ethiopia_fi_unified_data.csv
│   │   └── reference_codes.csv
│   └── processed/                    # Task 1-3: enriched dataset + derived tables
│       ├── ethiopia_fi_enriched.csv
│       ├── indicator_correlation_matrix.csv
│       └── event_indicator_links.csv
├── notebooks/                        # Tasks 1-4, one notebook each
│   ├── 01_data_exploration.ipynb
│   ├── 02_eda.ipynb
│   ├── 03_impact_modeling.ipynb
│   └── 04_forecasting.ipynb
├── src/                              # Scripts that mirror/generate the notebooks
│   ├── build_dataset.py              # Task 1
│   ├── eda.py                        # Task 2
│   ├── impact_modeling.py            # Task 3
│   ├── forecasting.py                # Task 4
│   └── make_notebooks.py             # builds the .ipynb files from these scripts
├── dashboard/app.py                  # Task 5: Streamlit dashboard
├── tests/test_data.py                # Data integrity + pipeline output tests
├── models/                           # Task 3-4 outputs
│   ├── association_matrix.csv
│   ├── validation_telebirr_mpesa.csv
│   └── forecast_access_usage.csv
├── reports/
│   ├── figures/                      # All 11 chart PNGs (Tasks 2-4)
│   ├── eda_summary.md
│   ├── impact_model_validation.md
│   ├── interim_report.md
│   └── final_report.md
├── data_enrichment_log.md            # Task 1 required deliverable
├── requirements.txt
└── .gitignore
```

## Which files belong to which task

| Task | Deliverable files |
|---|---|
| **Task 1** — Data Exploration & Enrichment | `src/build_dataset.py`, `data/raw/*.csv`, `data/processed/ethiopia_fi_enriched.csv`, `data_enrichment_log.md`, `notebooks/01_data_exploration.ipynb` |
| **Task 2** — EDA | `src/eda.py`, `notebooks/02_eda.ipynb`, `reports/eda_summary.md`, `reports/figures/01_*.png` – `08_*.png` |
| **Task 3** — Event Impact Modeling | `src/impact_modeling.py`, `notebooks/03_impact_modeling.ipynb`, `models/association_matrix.csv`, `models/validation_telebirr_mpesa.csv`, `reports/impact_model_validation.md`, `reports/figures/09_association_matrix.png` |
| **Task 4** — Forecasting | `src/forecasting.py`, `notebooks/04_forecasting.ipynb`, `models/forecast_access_usage.csv`, `reports/figures/10_forecast_access.png`, `reports/figures/11_forecast_usage.png` |
| **Task 5** — Dashboard | `dashboard/app.py` |
| **Cross-cutting** | `tests/test_data.py`, `.github/workflows/unittests.yml`, `reports/interim_report.md`, `reports/final_report.md` |

## Running the pipeline

```bash
# 1. Set up environment
pip install -r requirements.txt

# 2. Build the dataset (Task 1) — generates data/raw + data/processed
python src/build_dataset.py

# 3. Run EDA (Task 2) — generates reports/figures/01-08 + reports/eda_summary.md
python src/eda.py

# 4. Run impact modeling (Task 3) — generates models/association_matrix.csv etc.
python src/impact_modeling.py

# 5. Run forecasting (Task 4) — generates models/forecast_access_usage.csv + figures 10-11
python src/forecasting.py

# 6. (Optional) Regenerate notebooks from the scripts above
python src/make_notebooks.py

# 7. Run tests
pytest tests/ -v
```

## Running the dashboard (Task 5)

```bash
pip install -r requirements.txt
streamlit run dashboard/app.py
```

Then open the URL Streamlit prints (typically `http://localhost:8501`).
The dashboard has four pages: **Overview**, **Trends**, **Forecasts**, and
**Inclusion Projections**, each with interactive filters, a scenario
selector, and CSV download buttons.

## Git branching & PR workflow used for this project

See the step-by-step instructions provided separately — in short, each task
was developed on its own branch (`task-1` → `task-2` → `task-3` → `task-4`)
and merged into `main` via a Pull Request before starting the next task, per
the challenge's "Minimum Essential To Do" requirements.

## Methodology summary

- **Task 1:** Unified-schema dataset (`observation` / `event` / `impact_link`
  / `target`) enriched with 7 new observations, 3 new events, and 3 new
  impact_links, all documented with source, quote, and confidence level.
- **Task 2:** EDA covering composition, temporal coverage, Access/Usage
  trajectories, gender/urban-rural gaps, infrastructure enablers, event
  timeline overlay, and a year-level correlation matrix.
- **Task 3:** Event effects modeled as a logistic ramp-up reaching full
  documented magnitude by each link's `lag_months`; combined additively per
  indicator; validated against the observed Telebirr/M-Pesa mobile-money
  growth (found to over-predict by ~3.9pp, leading to a documented 0.55x
  discount factor for mobile-money-specific links).
- **Task 4:** Baseline = most recent observed momentum (not full-period
  regression, which would overstate current pace); forward-looking events
  only are layered on top per scenario (pessimistic 0.5x / base 1.0x /
  optimistic 1.4x); uncertainty bands widen with forecast horizon.
- **Task 5:** Streamlit + Plotly dashboard reading directly from the
  `data/processed` and `models/` outputs of Tasks 1-4.

## Limitations

- Only 5 historical Access-pillar data points (2011-2024) and 1
  Usage-pillar data point (2024) — see `reports/eda_summary.md` and
  `reports/final_report.md` for full discussion.
- Several impact-link magnitudes rely on comparable-country evidence
  (Kenya, Bangladesh, Nigeria) rather than Ethiopia-specific pre/post data,
  and are flagged `confidence = medium` or `low` throughout.
- Gender and urban/rural disaggregation figures are Findex-consistent
  estimates, not sourced from the underlying Findex microdata directly.

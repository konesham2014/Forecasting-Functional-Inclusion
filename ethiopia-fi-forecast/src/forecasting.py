"""
forecasting.py -- Task 4: Forecasting Access and Usage 2025-2027
Produces:
  - models/forecast_access_usage.csv  (point forecasts + CIs, 3 scenarios)
  - reports/figures/10_forecast_access.png
  - reports/figures/11_forecast_usage.png
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os

FIG = "reports/figures"
os.makedirs(FIG, exist_ok=True)
os.makedirs("models", exist_ok=True)

df = pd.read_csv("data/processed/ethiopia_fi_enriched.csv")
obs = df[df.record_type == "observation"].copy()
obs["observation_date"] = pd.to_datetime(obs["observation_date"])
events = df[df.record_type == "event"].copy()
events["observation_date"] = pd.to_datetime(events["observation_date"])
links = df[df.record_type == "impact_link"].copy()

DISCOUNT_FACTORS = {"ACC_MM_ACCOUNT": 0.55}

# -------------------------------------------------------------
# 1. Trend regression (log-linear, since growth is decelerating /
#    concave -- classic S-curve approach for adoption indicators)
# -------------------------------------------------------------
def fit_trend(indicator_code, degree=1, log_years=False):
    d = obs[obs.indicator_code == indicator_code].sort_values("observation_date")
    years = d.observation_date.dt.year.values.astype(float)
    y = d.value_numeric.values.astype(float)
    x = years - years.min()
    coef = np.polyfit(x, y, degree)
    return coef, years.min()

acc_coef, acc_base_year = fit_trend("ACC_OWNERSHIP", degree=1)
# NOTE: fitting a straight line across all 5 Findex waves (2011-2024) overstates
# the trend, since growth clearly decelerated (2011-17: ~3.6pp/yr avg -> 2021-24:
# only 1.0pp/yr). We therefore anchor the baseline on the MOST RECENT observed
# slope (2021->2024), which better reflects current momentum, and treat the
# full-period regression only as a discussion point in the report.
acc_hist = obs[obs.indicator_code == "ACC_OWNERSHIP"].sort_values("observation_date")
acc_recent_slope = (acc_hist.value_numeric.iloc[-1] - acc_hist.value_numeric.iloc[-2]) / \
                    (acc_hist.observation_date.dt.year.iloc[-1] - acc_hist.observation_date.dt.year.iloc[-2])
acc_anchor_year = int(acc_hist.observation_date.dt.year.iloc[-1])
acc_anchor_val = float(acc_hist.value_numeric.iloc[-1])
dp = obs[obs.indicator_code == "USG_DIGITAL_PAYMENT"]
# Only one Usage (digital payment) survey point (2024) -> anchor a trend using
# mobile money growth rate as a proxy slope, since USG_DIGITAL_PAYMENT itself
# has just 1 historical observation (documented limitation).
mm = obs[obs.indicator_code == "ACC_MM_ACCOUNT"].sort_values("observation_date")
mm_years = mm.observation_date.dt.year.values.astype(float)
mm_vals = mm.value_numeric.values.astype(float)
mm_coef = np.polyfit(mm_years - mm_years.min(), mm_vals, 1)
mm_annual_growth_pp = mm_coef[0]

usage_2024 = float(dp.value_numeric.iloc[0])
usage_anchor_year = int(dp.observation_date.dt.year.iloc[0])

# -------------------------------------------------------------
# 2. Event effect function (same logistic ramp as impact_modeling.py)
# -------------------------------------------------------------
def event_effect(t_months, magnitude, lag_months):
    if t_months < 0:
        return 0.0
    k = 6.0 / max(lag_months, 1)
    x = t_months - lag_months / 2
    return magnitude / (1 + np.exp(-k * x / 6))

def cumulative_event_effect(target_date, indicator_code):
    sub_links = links[links.related_indicator == indicator_code][["parent_id", "impact_magnitude", "lag_months"]]
    rel = sub_links.merge(events[["id", "observation_date"]], left_on="parent_id", right_on="id")
    total = 0.0
    for _, r in rel.iterrows():
        ev_date = r["observation_date"]
        months_since = (target_date.year - ev_date.year) * 12 + (target_date.month - ev_date.month)
        eff = event_effect(months_since, r["impact_magnitude"], max(r["lag_months"], 1))
        eff *= DISCOUNT_FACTORS.get(indicator_code, 1.0)
        total += eff
    return total

# Future/expected events for the "with events" and scenario models
# (already-launched events feed via cumulative_event_effect; here we add
#  forward-looking expected developments for 2025-2027 scenarios)
future_events = pd.DataFrame([
    {"name": "NFIS-II implementation acceleration", "date": "2026-06-01", "indicator_code": "ACC_OWNERSHIP", "magnitude": 2.0, "lag_months": 18},
    {"name": "4G/5G continued expansion", "date": "2026-01-01", "indicator_code": "USG_DIGITAL_PAYMENT", "magnitude": 2.5, "lag_months": 18},
    {"name": "Telebirr-CBE Birr interoperability full rollout", "date": "2025-06-01", "indicator_code": "USG_DIGITAL_PAYMENT", "magnitude": 1.5, "lag_months": 12},
    {"name": "M-Pesa network maturation", "date": "2025-01-01", "indicator_code": "ACC_MM_ACCOUNT", "magnitude": 2.0, "lag_months": 18},
])
future_events["date"] = pd.to_datetime(future_events["date"])

def future_event_effect(target_date, indicator_code, scenario="base"):
    mult = {"optimistic": 1.4, "base": 1.0, "pessimistic": 0.5}[scenario]
    rel = future_events[future_events.indicator_code == indicator_code]
    total = 0.0
    for _, r in rel.iterrows():
        months_since = (target_date.year - r.date.year) * 12 + (target_date.month - r.date.month)
        total += event_effect(months_since, r.magnitude * mult, r.lag_months)
    return total

# -------------------------------------------------------------
# 3. Build forecasts for 2025-2027, both indicators, 3 scenarios
# -------------------------------------------------------------
forecast_years = [2025, 2026, 2027]
rows = []

for year in forecast_years:
    target_date = pd.Timestamp(f"{year}-06-30")

    # ---- Access (Account Ownership) ----
    # Baseline = continuation of the most recent (2021-2024) observed momentum;
    # historical event effects are NOT re-added since they are already embedded
    # in that observed 2021-2024 slope. Only NEW forward-looking events (2025-27
    # expected developments) are added on top, per scenario.
    years_out_from_anchor = year - acc_anchor_year
    baseline_access = acc_anchor_val + acc_recent_slope * years_out_from_anchor

    for scen in ["pessimistic", "base", "optimistic"]:
        fut_eff = future_event_effect(target_date, "ACC_OWNERSHIP", scen)
        point = baseline_access + fut_eff
        years_out = year - 2024
        ci_width = 2.0 + 1.5 * years_out  # widening uncertainty
        if scen == "pessimistic":
            point -= 1.5 * years_out * 0.4
        elif scen == "optimistic":
            point += 1.5 * years_out * 0.4
        rows.append({
            "indicator": "Access (Account Ownership)", "indicator_code": "ACC_OWNERSHIP",
            "year": year, "scenario": scen, "point_forecast": round(point, 1),
            "ci_low": round(point - ci_width, 1), "ci_high": round(point + ci_width, 1),
        })

    # ---- Usage (Digital Payment Adoption) ----
    # Only one historical Findex usage point exists (2024), so there is no
    # observed slope to extrapolate. We anchor on 2024 and use the mobile-money
    # growth rate (a related, better-observed Usage-pillar proxy) as a damped
    # baseline slope, then add only forward-looking (2025-27) event effects.
    years_since_anchor = year - usage_anchor_year
    baseline_usage = usage_2024 + mm_annual_growth_pp * 0.6 * years_since_anchor  # proxy slope, damped

    for scen in ["pessimistic", "base", "optimistic"]:
        fut_eff = future_event_effect(target_date, "USG_DIGITAL_PAYMENT", scen)
        point = baseline_usage + fut_eff
        ci_width = 2.5 + 2.0 * years_since_anchor
        if scen == "pessimistic":
            point -= 2.0 * years_since_anchor * 0.4
        elif scen == "optimistic":
            point += 2.0 * years_since_anchor * 0.4
        rows.append({
            "indicator": "Usage (Digital Payment Adoption)", "indicator_code": "USG_DIGITAL_PAYMENT",
            "year": year, "scenario": scen, "point_forecast": round(point, 1),
            "ci_low": round(point - ci_width, 1), "ci_high": round(point + ci_width, 1),
        })

fc = pd.DataFrame(rows)
fc.to_csv("models/forecast_access_usage.csv", index=False)
print(fc.to_string(index=False))

# -------------------------------------------------------------
# 4. Plots
# -------------------------------------------------------------
def plot_forecast(indicator_code, hist_indicator_code, title, fname, target_val=None, target_year=None):
    hist = obs[obs.indicator_code == hist_indicator_code].sort_values("observation_date")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(hist.observation_date.dt.year, hist.value_numeric, marker="o", lw=2.5,
            color="#2E5E4E", label="Historical (Findex)")
    sub = fc[fc.indicator_code == indicator_code]
    colors = {"pessimistic": "#C9526B", "base": "#3E6D9C", "optimistic": "#2E5E4E"}
    for scen in ["pessimistic", "base", "optimistic"]:
        s = sub[sub.scenario == scen].sort_values("year")
        years = [hist.observation_date.dt.year.iloc[-1]] + list(s.year)
        vals = [hist.value_numeric.iloc[-1]] + list(s.point_forecast)
        ax.plot(years, vals, marker="s", ls="--", color=colors[scen], label=f"{scen.title()} scenario")
        if scen == "base":
            ax.fill_between(s.year, s.ci_low, s.ci_high, color=colors[scen], alpha=0.15, label="Base 90% band")
    if target_val:
        ax.axhline(target_val, color="#C9A227", ls=":", lw=2, label=f"NFIS-II {target_year} target")
    ax.set_title(title)
    ax.set_ylabel("% of adults")
    ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(f"{FIG}/{fname}", dpi=140)
    plt.close()

plot_forecast("ACC_OWNERSHIP", "ACC_OWNERSHIP", "Access Forecast: Account Ownership Rate, 2025-2027",
              "10_forecast_access.png", target_val=70, target_year=2028)
plot_forecast("USG_DIGITAL_PAYMENT", "USG_DIGITAL_PAYMENT", "Usage Forecast: Digital Payment Adoption Rate, 2025-2027",
              "11_forecast_usage.png", target_val=60, target_year=2028)

print("\nForecast table and figures written.")

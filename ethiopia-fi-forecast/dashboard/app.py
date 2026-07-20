"""
Ethiopia Financial Inclusion Forecasting Dashboard
Task 5 deliverable -- Selam Analytics

Run locally:
    pip install -r requirements.txt
    streamlit run dashboard/app.py
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import os

st.set_page_config(page_title="Ethiopia Financial Inclusion Forecast",
                    layout="wide", page_icon="🇪🇹")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@st.cache_data
def load_data():
    df = pd.read_csv(os.path.join(BASE, "data/processed/ethiopia_fi_enriched.csv"))
    df["observation_date"] = pd.to_datetime(df["observation_date"], errors="coerce")
    fc = pd.read_csv(os.path.join(BASE, "models/forecast_access_usage.csv"))
    assoc = pd.read_csv(os.path.join(BASE, "models/association_matrix.csv"), index_col=0)
    return df, fc, assoc

df, fc, assoc = load_data()
obs = df[df.record_type == "observation"].copy()
events = df[df.record_type == "event"].copy()
targets = df[df.record_type == "target"].copy()

# --------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------
st.sidebar.title("🇪🇹 Selam Analytics")
page = st.sidebar.radio("Navigate", ["Overview", "Trends", "Forecasts", "Inclusion Projections"])
st.sidebar.markdown("---")
st.sidebar.caption("Financial inclusion forecasting system built for the "
                    "National Bank of Ethiopia consortium.")

# --------------------------------------------------------------
# Overview
# --------------------------------------------------------------
if page == "Overview":
    st.title("Ethiopia Financial Inclusion — Overview")
    st.caption("Global Findex-aligned Access & Usage indicators")

    acc = obs[obs.indicator_code == "ACC_OWNERSHIP"].sort_values("observation_date")
    mm = obs[obs.indicator_code == "ACC_MM_ACCOUNT"].sort_values("observation_date")
    dp = obs[obs.indicator_code == "USG_DIGITAL_PAYMENT"].sort_values("observation_date")
    p2p = obs[obs.indicator_code == "OPS_P2P_ATM_RATIO"].sort_values("observation_date")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Account Ownership (Access)", f"{acc.value_numeric.iloc[-1]:.0f}%",
              f"+{acc.value_numeric.iloc[-1]-acc.value_numeric.iloc[-2]:.0f}pp since {int(acc.observation_date.dt.year.iloc[-2])}")
    c2.metric("Mobile Money Ownership", f"{mm.value_numeric.iloc[-1]:.1f}%",
              f"+{mm.value_numeric.iloc[-1]-mm.value_numeric.iloc[-2]:.1f}pp since {int(mm.observation_date.dt.year.iloc[-2])}")
    c3.metric("Digital Payment Adoption (Usage)", f"{dp.value_numeric.iloc[-1]:.0f}%", "2024 Findex")
    if not p2p.empty:
        c4.metric("P2P / ATM Withdrawal Ratio", f"{p2p.value_numeric.iloc[-1]:.2f}x",
                  "P2P transfers now exceed ATM cash withdrawals")

    st.markdown("---")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Access Growth Rate by Survey Wave")
        acc2 = acc.reset_index(drop=True)
        acc2["growth_pp"] = acc2.value_numeric.diff()
        fig = px.bar(acc2.dropna(subset=["growth_pp"]), x=acc2.observation_date.dt.year.dropna(),
                     y="growth_pp", labels={"x": "Findex wave", "growth_pp": "pp change vs. prior wave"},
                     color="growth_pp", color_continuous_scale="Greens")
        fig.update_layout(showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Growth decelerated from +13.4pp (2014-17) to just +3.0pp (2021-24), "
                   "despite Telebirr (2021) and M-Pesa (2023) launches.")
    with col2:
        st.subheader("Data Quality")
        st.dataframe(obs["confidence"].value_counts().rename_axis("confidence").reset_index(name="count"),
                     use_container_width=True, hide_index=True)
        st.dataframe(df["record_type"].value_counts().rename_axis("record_type").reset_index(name="count"),
                     use_container_width=True, hide_index=True)

# --------------------------------------------------------------
# Trends
# --------------------------------------------------------------
elif page == "Trends":
    st.title("Trends Explorer")

    indicators = sorted(obs.indicator_code.dropna().unique())
    default_idx = indicators.index("ACC_OWNERSHIP") if "ACC_OWNERSHIP" in indicators else 0
    selected = st.multiselect("Select indicator(s)", indicators, default=[indicators[default_idx], "ACC_MM_ACCOUNT"])

    min_year, max_year = int(obs.observation_date.dt.year.min()), int(obs.observation_date.dt.year.max())
    yr_range = st.slider("Date range", min_year, max_year, (min_year, max_year))

    show_events = st.checkbox("Overlay events", value=True)

    sub = obs[obs.indicator_code.isin(selected)]
    sub = sub[(sub.observation_date.dt.year >= yr_range[0]) & (sub.observation_date.dt.year <= yr_range[1])]

    fig = go.Figure()
    for code in selected:
        s = sub[sub.indicator_code == code].sort_values("observation_date")
        fig.add_trace(go.Scatter(x=s.observation_date, y=s.value_numeric, mode="lines+markers", name=code))
    if show_events:
        ev_in_range = events[(events.observation_date.dt.year >= yr_range[0]) & (events.observation_date.dt.year <= yr_range[1])]
        for _, e in ev_in_range.iterrows():
            fig.add_vline(x=e.observation_date.timestamp() * 1000, line_dash="dot", line_color="grey",
                          annotation_text=e.indicator, annotation_textangle=-90, annotation_font_size=8)
    fig.update_layout(height=550, yaxis_title="Value", xaxis_title="Date")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Channel Comparison: Telebirr vs. M-Pesa (registered users)")
    tel = obs[obs.indicator_code == "OPS_TELEBIRR_USERS"].sort_values("observation_date")
    mpesa = obs[obs.indicator_code == "OPS_MPESA_USERS"].sort_values("observation_date")
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=tel.observation_date, y=tel.value_numeric, name="Telebirr", mode="lines+markers"))
    fig2.add_trace(go.Scatter(x=mpesa.observation_date, y=mpesa.value_numeric, name="M-Pesa Ethiopia", mode="lines+markers"))
    fig2.update_layout(yaxis_title="Registered users", height=400)
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Download data")
    st.download_button("Download filtered observations (CSV)", sub.to_csv(index=False), "ethiopia_fi_trends.csv")

# --------------------------------------------------------------
# Forecasts
# --------------------------------------------------------------
elif page == "Forecasts":
    st.title("Forecasts: Access & Usage, 2025-2027")

    indicator_pick = st.selectbox("Indicator", ["Access (Account Ownership)", "Usage (Digital Payment Adoption)"])
    code = "ACC_OWNERSHIP" if indicator_pick.startswith("Access") else "USG_DIGITAL_PAYMENT"
    scenario_pick = st.multiselect("Scenario(s)", ["pessimistic", "base", "optimistic"],
                                    default=["pessimistic", "base", "optimistic"])

    hist = obs[obs.indicator_code == code].sort_values("observation_date")
    sub_fc = fc[(fc.indicator_code == code) & (fc.scenario.isin(scenario_pick))]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.observation_date.dt.year, y=hist.value_numeric,
                              mode="lines+markers", name="Historical", line=dict(color="#2E5E4E", width=3)))
    colors = {"pessimistic": "#C9526B", "base": "#3E6D9C", "optimistic": "#2E5E4E"}
    last_year, last_val = int(hist.observation_date.dt.year.iloc[-1]), float(hist.value_numeric.iloc[-1])
    for scen in scenario_pick:
        s = sub_fc[sub_fc.scenario == scen].sort_values("year")
        fig.add_trace(go.Scatter(x=[last_year] + list(s.year), y=[last_val] + list(s.point_forecast),
                                  mode="lines+markers", name=scen.title(), line=dict(dash="dash", color=colors[scen])))
        fig.add_trace(go.Scatter(x=list(s.year) + list(s.year[::-1]),
                                  y=list(s.ci_high) + list(s.ci_low[::-1]),
                                  fill="toself", fillcolor=colors[scen], opacity=0.08,
                                  line=dict(width=0), showlegend=False, hoverinfo="skip"))
    t = targets[targets.indicator_code == code]
    if not t.empty:
        fig.add_hline(y=float(t.value_numeric.iloc[0]), line_dash="dot", line_color="#C9A227",
                      annotation_text=f"NFIS-II target ({t.observation_date.iloc[0][:4]})")
    fig.update_layout(height=550, yaxis_title="% of adults", xaxis_title="Year")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Forecast table")
    st.dataframe(sub_fc[["year", "scenario", "point_forecast", "ci_low", "ci_high"]]
                 .sort_values(["year", "scenario"]), use_container_width=True, hide_index=True)
    st.download_button("Download forecast (CSV)", fc.to_csv(index=False), "ethiopia_fi_forecast.csv")

    st.subheader("Event x Indicator Association Matrix")
    st.dataframe(assoc.style.background_gradient(cmap="RdYlGn", axis=None), use_container_width=True)

# --------------------------------------------------------------
# Inclusion Projections
# --------------------------------------------------------------
elif page == "Inclusion Projections":
    st.title("Inclusion Projections & Policy Questions")

    scenario = st.radio("Scenario", ["pessimistic", "base", "optimistic"], index=1, horizontal=True)

    acc_fc = fc[(fc.indicator_code == "ACC_OWNERSHIP") & (fc.scenario == scenario)].sort_values("year")
    usg_fc = fc[(fc.indicator_code == "USG_DIGITAL_PAYMENT") & (fc.scenario == scenario)].sort_values("year")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Progress Toward NFIS-II Access Target (70% by 2028)")
        acc_2027 = float(acc_fc[acc_fc.year == 2027].point_forecast.iloc[0])
        st.progress(min(acc_2027 / 70, 1.0), text=f"{acc_2027:.0f}% of 70% target reached by 2027 ({scenario} scenario)")
    with col2:
        st.subheader("Progress Toward NFIS-II Usage Target (60% by 2028)")
        usg_2027 = float(usg_fc[usg_fc.year == 2027].point_forecast.iloc[0])
        st.progress(min(usg_2027 / 60, 1.0), text=f"{usg_2027:.0f}% of 60% target reached by 2027 ({scenario} scenario)")

    st.markdown("---")
    st.subheader("Consortium's Key Questions — Answered")
    st.markdown(f"""
**1. What drives financial inclusion in Ethiopia?**
Mobile-money-enabled market entry (Telebirr, M-Pesa) and interoperability
infrastructure (EthSwitch) are the largest single-event drivers identified, but
the EDA shows registration growth is decoupling from measured Access/Usage
growth — enabler variables (4G coverage, agent density, digital ID) appear to
be binding constraints on converting registrations into active inclusion.

**2. How do events affect inclusion outcomes?**
See the Event x Indicator Association Matrix (Forecasts page) for the full
estimated magnitude of each cataloged event on each indicator.

**3. How will inclusion look in 2026-2027?**
Under the **{scenario}** scenario: Access reaches **{acc_2027:.0f}%** and Usage
reaches **{usg_2027:.0f}%** by 2027 — both below the NFIS-II 2028 targets under
base assumptions, implying either an acceleration beyond current trend or a
target revision is likely needed.
""")

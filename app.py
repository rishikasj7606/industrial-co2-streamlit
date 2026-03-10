import os
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from blockchain import Blockchain

st.set_page_config(page_title="Industrial CO₂ Monitoring", layout="wide")

DATA_FILE = "industrial_carbon_monitoring.csv"

@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found in repo root.")

    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"]).copy()

    # Ensure required columns exist
    required_cols = [
        "timestamp", "industry", "device_state", "load_kw",
        "energy_kwh", "carbon_intensity", "co2_kg"
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Peak alert fallback if missing
    if "peak_alert" not in df.columns:
        df["peak_alert"] = (
            df["device_state"].astype(str).str.upper().eq("PEAK")
            & (df["co2_kg"] > 50)
        )

    return df

try:
    df = load_data(DATA_FILE)
except Exception as e:
    st.error(f"Failed to load dataset: {e}")
    st.stop()

if "bc" not in st.session_state:
    st.session_state.bc = Blockchain()

st.title("Industrial CO₂ Monitoring & Audit Dashboard")
st.caption("State-aware industrial carbon monitoring with blockchain-backed audit logging and low-emission scheduling.")

# ---------------- Sidebar ----------------
st.sidebar.header("Filters")

industry = st.sidebar.selectbox(
    "Select Industry",
    sorted(df["industry"].dropna().unique())
)

industry_df = df[df["industry"] == industry].copy()

device_options = sorted(industry_df["device_state"].dropna().unique())
device = st.sidebar.selectbox("Select Device State", device_options)

min_date = df["timestamp"].min().date()
max_date = df["timestamp"].max().date()

date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

mask = (
    (df["industry"] == industry) & 
    (df["device_state"] == device) & 
    (df["timestamp"].dt.date >= start_date) & 
    (df["timestamp"].dt.date <= end_date)
)
f = df.loc[mask].sort_values("timestamp").copy()

# ---------------- Header stats ----------------
top1, top2, top3 = st.columns([2, 1, 1])
with top1:
    st.markdown(
        f"""
        **Selected Scope**  
        Industry: `{industry}`  
        Device State: `{device}`  
        Date Range: `{start_date}` to `{end_date}`
        """
    )
with top2:
    st.metric("Rows Selected", len(f))
with top3:
    st.metric("Blockchain Blocks", len(st.session_state.bc.chain))

# ---------------- Tabs ----------------
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Overview", "Trends", "Comparison", "Audit", "Scheduling"]
)

# ---------------- Tab 1: Overview ----------------
with tab1:
    st.subheader("Overview")

    if len(f) == 0:
        st.warning("No data available for the selected filters.")
    else:
        total_co2 = float(f["co2_kg"].sum())
        total_energy = float(f["energy_kwh"].sum())
        avg_ci = float(f["carbon_intensity"].mean())
        peak_cnt = int(f["peak_alert"].sum())
        max_co2 = float(f["co2_kg"].max())
        avg_load = float(f["load_kw"].mean())

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Total CO₂ (kg)", f"{total_co2:,.2f}")
        c2.metric("Total Energy (kWh)", f"{total_energy:,.2f}")
        c3.metric("Avg Carbon Intensity", f"{avg_ci:,.4f}")
        c4.metric("Peak Alerts", f"{peak_cnt}")
        c5.metric("Max CO₂ / Interval", f"{max_co2:,.2f}")
        c6.metric("Avg Load (kW)", f"{avg_load:,.2f}")

        st.markdown("### Formula Used")
        st.latex(r"Energy\ (kWh)=Load\ (kW)\times \Delta t")
        st.latex(r"CO_2\ (kg)=Energy\ (kWh)\times Carbon\ Intensity\ (kg/kWh)")

        st.markdown("### Summary Statistics")
        st.dataframe(f.describe(include="all"), use_container_width=True)

        st.markdown("### Sample Records")
        st.dataframe(f.head(50), use_container_width=True)

        st.download_button(
            "Download Filtered Data (CSV)",
            data=f.to_csv(index=False).encode("utf-8"),
            file_name=f"{industry}_{device}_{start_date}_{end_date}.csv",
            mime="text/csv"
        )

# ---------------- Tab 5: Scheduling ----------------
with tab5:
    st.subheader("Low-Emission Scheduling Recommendation")

    if len(f) == 0:
        st.info("No data available for scheduling.")
    else:
        st.markdown(
            "This module recommends **continuous low-emission operating blocks** "
            "based on historical CO₂ values."
        )

        block_hours = st.slider("Block Duration (hours)", 1, 6, 2)
        k_blocks = st.slider("Number of Recommended Blocks", 1, 20, 5)

        tmp = f.sort_values("timestamp").copy()
        tmp["block_avg_co2"] = tmp["co2_kg"].rolling(window=block_hours).mean()

        candidates = tmp.dropna().sort_values("block_avg_co2").head(k_blocks)

        recommended = []
        for idx in candidates.index:
            start_idx = idx - (block_hours - 1)
            if start_idx < 0:
                continue
            start_ts = tmp.loc[start_idx, "timestamp"]
            end_ts = tmp.loc[idx, "timestamp"]
            avg_block_co2 = tmp.loc[idx, "block_avg_co2"]

            recommended.append({
                "start_time": start_ts,
                "end_time": end_ts,
                "avg_co2_per_hour": float(avg_block_co2)
            })

        rec_df = pd.DataFrame(recommended)

        if len(rec_df) == 0:
            st.warning("No valid scheduling blocks found.")
        else:
            st.markdown("#### Recommended Low-Emission Blocks")
            st.dataframe(rec_df, use_container_width=True)

            overall_avg = float(f["co2_kg"].mean())
            block_avg = float(rec_df["avg_co2_per_hour"].mean())
            est_reduction = max(0.0, ((overall_avg - block_avg) / overall_avg) * 100)

            c1, c2 = st.columns(2)
            c1.metric("Overall Avg CO₂ / Interval", f"{overall_avg:,.2f}")
            c2.metric("Estimated Reduction", f"{est_reduction:.2f}%")

            # ---------------- Blockchain Recording for Scheduling ----------------
            if st.button("Record Schedule Recommendation to Blockchain"):
                schedule_record = {
                    "type": "schedule_recommendation",
                    "industry": industry,
                    "device_state": device,
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                    "recommendations": rec_df.to_dict(orient="records")
                }

                st.session_state.bc.add_block(schedule_record)
                st.success("Schedule recommendation recorded to blockchain.")

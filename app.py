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

# ---------------- Tab 2: Trends ----------------
with tab2:
    st.subheader("Time-series Trends")

    if len(f) == 0:
        st.info("No data in the selected range.")
    else:
        # CO2 over time
        st.markdown("#### CO₂ over Time")
        fig1, ax1 = plt.subplots(figsize=(12, 4))
        ax1.plot(f["timestamp"], f["co2_kg"], linewidth=1.5)
        ax1.set_xlabel("Time")
        ax1.set_ylabel("CO₂ (kg)")
        ax1.grid(alpha=0.3)
        st.pyplot(fig1)

        # Load over time
        st.markdown("#### Load over Time")
        fig2, ax2 = plt.subplots(figsize=(12, 4))
        ax2.plot(f["timestamp"], f["load_kw"], linewidth=1.5)
        ax2.set_xlabel("Time")
        ax2.set_ylabel("Load (kW)")
        ax2.grid(alpha=0.3)
        st.pyplot(fig2)

        # CO2 distribution
        st.markdown("#### CO₂ Distribution")
        fig3, ax3 = plt.subplots(figsize=(8, 4))
        ax3.hist(f["co2_kg"].dropna(), bins=30)
        ax3.set_xlabel("CO₂ (kg)")
        ax3.set_ylabel("Count")
        ax3.grid(alpha=0.3)
        st.pyplot(fig3)

        # Daily aggregation
        st.markdown("#### Daily Total CO₂")
        daily = f.groupby(f["timestamp"].dt.date, as_index=False)["co2_kg"].sum()
        fig4, ax4 = plt.subplots(figsize=(12, 4))
        ax4.plot(daily["timestamp"], daily["co2_kg"], marker="o")
        ax4.set_xlabel("Date")
        ax4.set_ylabel("Daily CO₂ (kg)")
        ax4.grid(alpha=0.3)
        st.pyplot(fig4)

# ---------------- Tab 3: Comparison ----------------
with tab3:
    st.subheader("Comparative Analytics")

    industry_totals = (
        df.groupby("industry", as_index=False)["co2_kg"]
        .sum()
        .sort_values("co2_kg", ascending=False)
    )

    st.markdown("#### Total CO₂ by Industry")
    fig5, ax5 = plt.subplots(figsize=(10, 4))
    ax5.bar(industry_totals["industry"], industry_totals["co2_kg"])
    ax5.set_xlabel("Industry")
    ax5.set_ylabel("Total CO₂ (kg)")
    plt.xticks(rotation=25)
    ax5.grid(axis="y", alpha=0.3)
    st.pyplot(fig5)

    state_totals = (
        df.groupby("device_state", as_index=False)["co2_kg"]
        .sum()
        .sort_values("co2_kg", ascending=False)
    )

    st.markdown("#### Total CO₂ by Device State")
    fig6, ax6 = plt.subplots(figsize=(10, 4))
    ax6.bar(state_totals["device_state"], state_totals["co2_kg"])
    ax6.set_xlabel("Device State")
    ax6.set_ylabel("Total CO₂ (kg)")
    plt.xticks(rotation=25)
    ax6.grid(axis="y", alpha=0.3)
    st.pyplot(fig6)

    st.markdown("#### Industry × Device State CO₂ Matrix")
    pivot = df.pivot_table(
        index="industry",
        columns="device_state",
        values="co2_kg",
        aggfunc="sum",
        fill_value=0
    )
    st.dataframe(pivot, use_container_width=True)

# ---------------- Tab 4: Audit ----------------
with tab4:
    st.subheader("Blockchain Audit")

    if len(f) == 0:
        st.info("No data to record for selected filters.")
    else:
        col1, col2 = st.columns(2)

        with col1:
            if st.button("Record Selected Data to Blockchain"):
                sample = f.sort_values("timestamp").head(200)
                for _, row in sample.iterrows():
                    record = {
                        "timestamp": str(row["timestamp"]),
                        "industry": row["industry"],
                        "device_state": row["device_state"],
                        "energy_kwh": float(row["energy_kwh"]),
                        "co2_kg": float(row["co2_kg"]),
                        "peak_alert": bool(row["peak_alert"]),
                    }
                    st.session_state.bc.add_block(record)
                st.success("Recorded up to 200 rows into blockchain audit log.")

        with col2:
            is_valid = st.session_state.bc.is_chain_valid()
            st.metric("Chain Validity", "Valid" if is_valid else "Invalid")

        st.markdown("#### Latest Block")
        st.json(st.session_state.bc.chain[-1].to_dict())

        st.markdown("#### Recent Blocks")
        recent_blocks = [blk.to_dict() for blk in st.session_state.bc.chain[-5:]]
        st.dataframe(pd.DataFrame(recent_blocks), use_container_width=True)

        st.markdown("#### Emission Hotspots (Top 10 Highest CO₂ Intervals)")
        hotspots = f.sort_values("co2_kg", ascending=False).head(10)[
            ["timestamp", "industry", "device_state", "load_kw", "co2_kg", "peak_alert"]
        ]
        st.dataframe(hotspots, use_container_width=True)

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

            if st.button("Record Schedule Recommendation to Blockchain"):
    schedule_record = {
        "type": "schedule_recommendation",
        "industry": industry,
        "device_state": device,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "recommendations": best.to_dict(orient="records")
    }

    st.session_state.bc.add_block(schedule_record)
    st.success("Schedule recommendation recorded to blockchain.")

else:
    st.info("Click the button to store the recommendation in the blockchain.")
    start_date, end_date = min_date, max_date

mask = (
    (df["industry"] == industry) &
    (df["device_state"] == device) &
    (df["timestamp"].dt.date >= start_date) &
    (df["timestamp"].dt.date <= end_date)
)
f = df[mask].copy()

# -------- Tabs --------
tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Trends", "Comparison", "Blockchain & Scheduling"])

# -------- Overview (KPIs + table) --------
with tab1:
    st.subheader(f"{industry} — {device}")

    total_co2 = float(f["co2_kg"].sum()) if len(f) else 0.0
    total_energy = float(f["energy_kwh"].sum()) if len(f) else 0.0
    avg_ci = float(f["carbon_intensity"].mean()) if len(f) else 0.0
    peak_cnt = int(f["peak_alert"].sum()) if "peak_alert" in f.columns and len(f) else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total CO₂ (kg)", f"{total_co2:,.2f}")
    c2.metric("Total Energy (kWh)", f"{total_energy:,.2f}")
    c3.metric("Avg Carbon Intensity (kg/kWh)", f"{avg_ci:,.4f}")
    c4.metric("Peak Alerts", f"{peak_cnt}")

    st.write("#### Summary Statistics")
    st.dataframe(f.describe(include="all"))

    st.write("#### Sample Records")
    st.dataframe(f.head(50))

# -------- Trends (time-series plots) --------
with tab2:
    st.subheader("Time-series Trends")

    if len(f) == 0:
        st.info("No data in the selected range.")
    else:
        # CO2 vs time
        st.write("##### CO₂ over Time")
        fig1, ax1 = plt.subplots(figsize=(12, 4))
        ax1.plot(f["timestamp"], f["co2_kg"])
        ax1.set_xlabel("Time")
        ax1.set_ylabel("CO₂ (kg)")
        st.pyplot(fig1)

        # Load vs time
        st.write("##### Load (kW) over Time")
        fig2, ax2 = plt.subplots(figsize=(12, 4))
        ax2.plot(f["timestamp"], f["load_kw"])
        ax2.set_xlabel("Time")
        ax2.set_ylabel("Load (kW)")
        st.pyplot(fig2)

        # CO2 distribution
        st.write("##### CO₂ Distribution")
        fig3, ax3 = plt.subplots(figsize=(8, 4))
        ax3.hist(f["co2_kg"].dropna(), bins=40)
        ax3.set_xlabel("CO₂ (kg)")
        ax3.set_ylabel("Count")
        st.pyplot(fig3)

# -------- Comparison (industry/device totals) --------
with tab3:
    st.subheader("Comparative Analytics")

    # Industry totals
    industry_totals = df.groupby("industry", as_index=False)["co2_kg"].sum().sort_values("co2_kg", ascending=False)
    st.write("##### Total CO₂ by Industry")
    fig4, ax4 = plt.subplots(figsize=(10, 4))
    ax4.bar(industry_totals["industry"], industry_totals["co2_kg"])
    ax4.set_xlabel("Industry")
    ax4.set_ylabel("Total CO₂ (kg)")
    plt.xticks(rotation=25)
    st.pyplot(fig4)

    # Top devices overall
    device_totals = df.groupby("device_state", as_index=False)["co2_kg"].sum().sort_values("co2_kg", ascending=False).head(10)
    st.write("##### Top 10 Devices by CO₂")
    fig5, ax5 = plt.subplots(figsize=(10, 4))
    ax5.bar(device_totals["device_state"], device_totals["co2_kg"])
    ax5.set_xlabel("Device")
    ax5.set_ylabel("Total CO₂ (kg)")
    plt.xticks(rotation=30, ha="right")
    st.pyplot(fig5)

# -------- Blockchain & Scheduling --------
with tab4:
    st.subheader("Blockchain Audit + Low-Emission Scheduling")

    if len(f) == 0:
        st.info("No data to record for selected filters.")
    else:
        if st.button("Record Selected Data to Blockchain"):
            # store only a limited number to avoid huge chain
            sample = f.sort_values("timestamp").head(200)

            for _, row in sample.iterrows():
                record = {
                    "timestamp": str(row["timestamp"]),
                    "industry": row["industry"],
                    "device_state": row["device_state"],
                    "energy_kwh": float(row["energy_kwh"]),
                    "co2_kg": float(row["co2_kg"]),
                }
                st.session_state.bc.add_block(record)

            st.success("Recorded (up to 200 rows) into blockchain audit log.")

        st.write("##### Latest Block")
        st.json(st.session_state.bc.chain[-1].__dict__)

        # Scheduling: suggest low-emission slots
        st.write("##### Recommended Low-Emission Operating Slots")
        k = st.slider("Number of recommended time slots", 5, 50, 10)
        best = f.sort_values("co2_kg", ascending=True).head(k)[["timestamp", "co2_kg", "load_kw", "carbon_intensity"]]
        st.dataframe(best)

        if st.button("Record Schedule Recommendation to Blockchain"):
            schedule_record = {
                "type": "schedule_recommendation",
                "industry": industry,
                "device_state": device,
                "start_date": str(start_date),
                "end_date": str(end_date),
                "recommendations": best.to_dict(orient="records")
            }
            st.session_state.bc.add_block(schedule_record)
            st.success("Schedule recommendation recorded to blockchain.")

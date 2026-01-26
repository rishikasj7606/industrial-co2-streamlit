import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# If you already have blockchain.py
from blockchain import Blockchain

st.set_page_config(page_title="Industrial CO₂ Monitoring", layout="wide")

@st.cache_data
def load_data():
    df = pd.read_csv("industrial_carbon_monitoring.csv")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df

df = load_data()

# Keep blockchain in session so it doesn't reset every rerun
if "bc" not in st.session_state:
    st.session_state.bc = Blockchain()

st.title("Industrial CO₂ Monitoring & Audit Dashboard")

# -------- Sidebar filters --------
st.sidebar.header("Filters")
industry = st.sidebar.selectbox("Select Industry", sorted(df["industry"].unique()))

device_options = sorted(df[df["industry"] == industry]["device_state"].unique())
device = st.sidebar.selectbox("Select Device", device_options)

min_date = df["timestamp"].min().date()
max_date = df["timestamp"].max().date()
date_range = st.sidebar.date_input("Select Date Range", value=(min_date, max_date))

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

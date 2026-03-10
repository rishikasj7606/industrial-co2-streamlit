import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st

from blockchain import Blockchain


# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="Industrial Carbon Monitoring",
    page_icon="🌍",
    layout="wide",
)

# -----------------------------
# CUSTOM STYLING
# -----------------------------
st.markdown(
    """
    <style>
        .stApp {
            background: linear-gradient(180deg, #0b1220 0%, #111827 100%);
            color: white;
        }
        .main-title {
            padding: 1rem 1.2rem;
            border-radius: 18px;
            background: linear-gradient(135deg, #0f766e, #2563eb);
            color: white;
            margin-bottom: 1rem;
        }
        .card {
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.08);
            padding: 16px;
            border-radius: 16px;
            margin-bottom: 10px;
        }
        .small-note {
            color: #cbd5e1;
            font-size: 14px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# BLOCKCHAIN
# -----------------------------
if "blockchain" not in st.session_state:
    st.session_state.blockchain = Blockchain("blockchain_ledger.json")

blockchain = st.session_state.blockchain


# -----------------------------
# HELPERS
# -----------------------------
def load_dataset(uploaded_file):
    if uploaded_file is not None:
        return pd.read_csv(uploaded_file), "Uploaded file"

    possible_files = [
        "industrial_carbon_monitoring.csv",
        "industrial_carbon_monitoring (1).csv",
        "data.csv",
        "dataset.csv",
    ]

    for f in possible_files:
        if os.path.exists(f):
            return pd.read_csv(f), f

    for f in os.listdir("."):
        if f.endswith(".csv"):
            return pd.read_csv(f), f

    return None, None


def preprocess(df):
    df.columns = [c.strip().lower() for c in df.columns]

    required = [
        "timestamp",
        "load_kw",
        "device_state",
        "state_value",
        "carbon_intensity",
        "industry",
        "energy_kwh",
        "co2_kg",
        "peak_alert",
    ]

    missing = [c for c in required if c not in df.columns]
    if missing:
        return None, missing

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    numeric_cols = ["load_kw", "state_value", "carbon_intensity", "energy_kwh", "co2_kg"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["industry"] = df["industry"].astype(str)
    df["device_state"] = df["device_state"].astype(str)
    df["peak_alert"] = df["peak_alert"].astype(str)

    df = df.dropna(subset=["timestamp", "co2_kg"])
    df["date"] = df["timestamp"].dt.date
    df["hour"] = df["timestamp"].dt.hour
    df["month"] = df["timestamp"].dt.to_period("M").astype(str)

    return df, None


def kpi_card(title, value):
    st.markdown(
        f"""
        <div class="card">
            <h4 style="margin-bottom:0.4rem;">{title}</h4>
            <h2 style="margin-top:0;">{value}</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_recommendations(df):
    hourly_avg = df.groupby("hour")["co2_kg"].mean().sort_values()
    best_hour = int(hourly_avg.index[0])
    worst_hour = int(hourly_avg.index[-1])

    state_avg = df.groupby("device_state")["co2_kg"].mean().sort_values(ascending=False)
    high_state = state_avg.index[0]

    industry_avg = df.groupby("industry")["co2_kg"].mean().sort_values(ascending=False)
    high_industry = industry_avg.index[0]

    recs = [
        f"Schedule heavy operations near **{best_hour}:00** because average CO₂ is lowest in that hour.",
        f"Avoid peak scheduling around **{worst_hour}:00** because emissions are highest then.",
        f"Focus optimization on **{high_state}** state because it has the highest average CO₂ output.",
        f"Give priority monitoring to **{high_industry}** industry because it contributes the largest average emissions.",
        "Reduce unnecessary high-load operation, improve maintenance, and shift energy-intensive activity to low-emission hours.",
    ]

    return best_hour, worst_hour, high_state, high_industry, recs


def add_decision_to_blockchain(action_type, details):
    payload = {
        "action_type": action_type,
        "details": details,
    }
    blockchain.add_block(payload)


# -----------------------------
# LOAD DATA
# -----------------------------
st.markdown(
    """
    <div class="main-title">
        <h1>🌍 Industrial Carbon Monitoring & Smart Scheduling</h1>
        <p>Monitor emissions, analyze operational patterns, generate reduction insights, and securely store decisions using blockchain.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.header("Data Input")
uploaded_file = st.sidebar.file_uploader("Upload CSV file", type=["csv"])

raw_df, source_name = load_dataset(uploaded_file)

if raw_df is None:
    st.error("No CSV file found. Keep your dataset in the repo or upload it from the sidebar.")
    st.stop()

df, missing_cols = preprocess(raw_df)

if missing_cols:
    st.error(f"Missing required columns: {missing_cols}")
    st.write("Columns found:", list(raw_df.columns))
    st.stop()

st.sidebar.success(f"Loaded from: {source_name}")

# -----------------------------
# SIDEBAR FILTERS
# -----------------------------
st.sidebar.header("Filters")

industry_list = ["All"] + sorted(df["industry"].dropna().unique().tolist())
state_list = ["All"] + sorted(df["device_state"].dropna().unique().tolist())

selected_industry = st.sidebar.selectbox("Select Industry", industry_list)
selected_state = st.sidebar.selectbox("Select Device State", state_list)

filtered_df = df.copy()

if selected_industry != "All":
    filtered_df = filtered_df[filtered_df["industry"] == selected_industry]

if selected_state != "All":
    filtered_df = filtered_df[filtered_df["device_state"] == selected_state]

if filtered_df.empty:
    st.warning("No data available for selected filters.")
    st.stop()

# -----------------------------
# KPIs
# -----------------------------
total_co2 = filtered_df["co2_kg"].sum()
avg_co2 = filtered_df["co2_kg"].mean()
total_energy = filtered_df["energy_kwh"].sum()
avg_intensity = filtered_df["carbon_intensity"].mean()
peak_count = (filtered_df["peak_alert"].str.lower() == "yes").sum()
avg_load = filtered_df["load_kw"].mean()

c1, c2, c3 = st.columns(3)
with c1:
    kpi_card("Total CO₂ (kg)", f"{total_co2:,.2f}")
with c2:
    kpi_card("Average CO₂ (kg)", f"{avg_co2:,.2f}")
with c3:
    kpi_card("Total Energy (kWh)", f"{total_energy:,.2f}")

c4, c5, c6 = st.columns(3)
with c4:
    kpi_card("Avg Carbon Intensity", f"{avg_intensity:,.4f}")
with c5:
    kpi_card("Peak Alerts", int(peak_count))
with c6:
    kpi_card("Average Load (kW)", f"{avg_load:,.2f}")

# -----------------------------
# TABS
# -----------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Monitoring", "🧠 Scheduling", "⛓ Blockchain", "🗂 Data Preview"]
)

# -----------------------------
# TAB 1 - MONITORING
# -----------------------------
with tab1:
    st.subheader("Emission Monitoring Dashboard")

    daily_emission = filtered_df.groupby("date")["co2_kg"].sum().reset_index()
    hourly_emission = filtered_df.groupby("hour")["co2_kg"].mean().reset_index()
    industry_emission = filtered_df.groupby("industry")["co2_kg"].sum().sort_values(ascending=False)
    state_emission = filtered_df.groupby("device_state")["co2_kg"].sum().sort_values(ascending=False)
    intensity_trend = filtered_df.groupby("date")["carbon_intensity"].mean().reset_index()
    load_vs_co2 = filtered_df[["load_kw", "co2_kg"]].dropna()

    st.markdown('<div class="card"><h4>Daily CO₂ Trend</h4></div>', unsafe_allow_html=True)
    fig1, ax1 = plt.subplots(figsize=(12, 4))
    ax1.plot(daily_emission["date"].astype(str), daily_emission["co2_kg"], marker="o")
    ax1.set_xlabel("Date")
    ax1.set_ylabel("CO₂ (kg)")
    ax1.set_title("Daily CO₂ Emission")
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig1)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="card"><h4>Industry-wise CO₂ Emission</h4></div>', unsafe_allow_html=True)
        fig2, ax2 = plt.subplots(figsize=(8, 4))
        ax2.bar(industry_emission.index.astype(str), industry_emission.values)
        ax2.set_xlabel("Industry")
        ax2.set_ylabel("CO₂ (kg)")
        ax2.set_title("CO₂ by Industry")
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig2)

    with col2:
        st.markdown('<div class="card"><h4>Device State-wise CO₂ Emission</h4></div>', unsafe_allow_html=True)
        fig3, ax3 = plt.subplots(figsize=(8, 4))
        ax3.bar(state_emission.index.astype(str), state_emission.values)
        ax3.set_xlabel("Device State")
        ax3.set_ylabel("CO₂ (kg)")
        ax3.set_title("CO₂ by Device State")
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig3)

    col3, col4 = st.columns(2)

    with col3:
        st.markdown('<div class="card"><h4>Hourly Emission Pattern</h4></div>', unsafe_allow_html=True)
        fig4, ax4 = plt.subplots(figsize=(8, 4))
        ax4.plot(hourly_emission["hour"], hourly_emission["co2_kg"], marker="o")
        ax4.set_xlabel("Hour")
        ax4.set_ylabel("Average CO₂ (kg)")
        ax4.set_title("Hourly CO₂ Pattern")
        plt.tight_layout()
        st.pyplot(fig4)

    with col4:
        st.markdown('<div class="card"><h4>Carbon Intensity Trend</h4></div>', unsafe_allow_html=True)
        fig5, ax5 = plt.subplots(figsize=(8, 4))
        ax5.plot(intensity_trend["date"].astype(str), intensity_trend["carbon_intensity"], marker="o")
        ax5.set_xlabel("Date")
        ax5.set_ylabel("Carbon Intensity")
        ax5.set_title("Average Carbon Intensity by Date")
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig5)

    st.markdown('<div class="card"><h4>Load vs CO₂ Relationship</h4></div>', unsafe_allow_html=True)
    fig6, ax6 = plt.subplots(figsize=(10, 4))
    ax6.scatter(load_vs_co2["load_kw"], load_vs_co2["co2_kg"], alpha=0.7)
    ax6.set_xlabel("Load (kW)")
    ax6.set_ylabel("CO₂ (kg)")
    ax6.set_title("Load vs CO₂")
    plt.tight_layout()
    st.pyplot(fig6)

    st.markdown('<div class="card"><h4>Peak Alert Records</h4></div>', unsafe_allow_html=True)
    peak_df = filtered_df[filtered_df["peak_alert"].str.lower() == "yes"]

    if not peak_df.empty:
        st.dataframe(
            peak_df[["timestamp", "industry", "device_state", "load_kw", "energy_kwh", "co2_kg", "peak_alert"]],
            use_container_width=True,
        )
    else:
        st.info("No peak alerts found in current filter.")

# -----------------------------
# TAB 2 - SCHEDULING
# -----------------------------
with tab2:
    st.subheader("Smart Scheduling and Reduction Suggestions")

    best_hour, worst_hour, high_state, high_industry, recs = get_recommendations(filtered_df)

    left, right = st.columns([1, 1])

    with left:
        st.markdown('<div class="card"><h4>Recommended Scheduling Window</h4></div>', unsafe_allow_html=True)
        st.success(f"Best hour for low-emission operation: **{best_hour}:00**")
        st.warning(f"Hour to avoid for heavy operation: **{worst_hour}:00**")

        st.write(f"Most emission-heavy device state: **{high_state}**")
        st.write(f"Most emission-heavy industry: **{high_industry}**")

    with right:
        st.markdown('<div class="card"><h4>Reduction Recommendations</h4></div>', unsafe_allow_html=True)
        for i, r in enumerate(recs, start=1):
            st.write(f"{i}. {r}")

    st.markdown('<div class="card"><h4>Save Scheduling Decision to Blockchain</h4></div>', unsafe_allow_html=True)

    decision_note = st.text_area(
        "Add scheduling note",
        value=f"Heavy operations should be shifted to {best_hour}:00 to reduce CO₂. Avoid {worst_hour}:00 due to higher average emissions.",
        height=120,
    )

    if st.button("Save Scheduling Recommendation"):
        details = {
            "recommended_hour": best_hour,
            "avoid_hour": worst_hour,
            "high_emission_state": high_state,
            "high_emission_industry": high_industry,
            "note": decision_note,
        }
        add_decision_to_blockchain("Scheduling Recommendation", details)
        st.success("Scheduling recommendation saved into blockchain.")

# -----------------------------
# TAB 3 - BLOCKCHAIN
# -----------------------------
with tab3:
    st.subheader("Blockchain Ledger")

    status = blockchain.is_valid()
    if status:
        st.success("Blockchain is valid and untampered.")
    else:
        st.error("Blockchain integrity failed.")

    chain = blockchain.get_chain()
    chain_df = pd.DataFrame(chain)
    st.dataframe(chain_df, use_container_width=True)

    st.markdown('<div class="card"><h4>Add Manual Monitoring Record</h4></div>', unsafe_allow_html=True)

    manual_action = st.text_input("Action Title", value="Monitoring Update")
    manual_note = st.text_area("Action Details", value="Manual emission review completed.")
    if st.button("Add Manual Block"):
        add_decision_to_blockchain(
            manual_action,
            {"note": manual_note}
        )
        st.success("Manual block added successfully.")

# -----------------------------
# TAB 4 - DATA PREVIEW
# -----------------------------
with tab4:
    st.subheader("Dataset Preview")
    st.dataframe(filtered_df, use_container_width=True)

    st.markdown("### Dataset Summary")
    st.write(filtered_df.describe(include="all"))

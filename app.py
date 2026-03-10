import os
from time import time

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from blockchain import Blockchain


# ---------------------------
# PAGE CONFIG
# ---------------------------
st.set_page_config(
    page_title="Industrial Carbon Monitoring Dashboard",
    page_icon="🌍",
    layout="wide",
)

# ---------------------------
# CUSTOM CSS
# ---------------------------
st.markdown(
    """
    <style>
    .main {
        background-color: #f8fbff;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    .metric-card {
        background: white;
        padding: 14px;
        border-radius: 14px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        text-align: center;
    }
    .title-box {
        background: linear-gradient(135deg, #0f766e, #2563eb);
        padding: 18px;
        border-radius: 18px;
        color: white;
        margin-bottom: 18px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------
# BLOCKCHAIN INIT
# ---------------------------
blockchain = Blockchain("blockchain_data.json")


# ---------------------------
# HELPERS
# ---------------------------
def find_default_csv():
    possible_files = [
        "industrial_carbon_monitoring (1).csv",
        "industrial_carbon_monitoring.csv",
        "dataset.csv",
        "data.csv",
    ]

    for file_name in possible_files:
        if os.path.exists(file_name):
            return file_name

    for file_name in os.listdir("."):
        if file_name.lower().endswith(".csv"):
            return file_name

    return None


def normalize_columns(df):
    df.columns = [str(col).strip().lower().replace(" ", "_") for col in df.columns]
    return df


def guess_column(df, possible_names):
    for col in df.columns:
        if col in possible_names:
            return col
    return None


def load_data(uploaded_file):
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        return df, "Uploaded file"

    default_csv = find_default_csv()
    if default_csv:
        df = pd.read_csv(default_csv)
        return df, f"Local repo file: {default_csv}"

    return None, None


def preprocess_data(df):
    df = normalize_columns(df)

    timestamp_col = guess_column(
        df,
        ["timestamp", "date", "datetime", "time", "recorded_at"],
    )
    emission_col = guess_column(
        df,
        ["carbon_emission", "co2", "co2_emission", "emission", "emissions"],
    )
    industry_col = guess_column(
        df,
        ["industry", "sector", "industry_name"],
    )
    device_col = guess_column(
        df,
        ["device", "machine", "equipment", "device_name"],
    )
    energy_col = guess_column(
        df,
        ["energy", "energy_consumption", "power", "electricity", "kwh"],
    )

    missing_required = []
    if timestamp_col is None:
        missing_required.append("timestamp/date column")
    if emission_col is None:
        missing_required.append("carbon_emission/co2/emission column")

    if missing_required:
        return None, {
            "error": True,
            "message": "Required columns not found: " + ", ".join(missing_required)
        }

    df = df.copy()
    df[timestamp_col] = pd.to_datetime(df[timestamp_col], errors="coerce")
    df[emission_col] = pd.to_numeric(df[emission_col], errors="coerce")

    if energy_col is not None:
        df[energy_col] = pd.to_numeric(df[energy_col], errors="coerce")

    if industry_col is None:
        df["industry"] = "Unknown Industry"
        industry_col = "industry"
    else:
        df[industry_col] = df[industry_col].astype(str)

    if device_col is None:
        df["device"] = "Unknown Device"
        device_col = "device"
    else:
        df[device_col] = df[device_col].astype(str)

    df = df.dropna(subset=[timestamp_col, emission_col]).copy()

    df["hour"] = df[timestamp_col].dt.hour
    df["day"] = df[timestamp_col].dt.date
    df["month"] = df[timestamp_col].dt.to_period("M").astype(str)

    if energy_col is not None:
        df["carbon_intensity"] = np.where(
            df[energy_col] > 0,
            df[emission_col] / df[energy_col],
            np.nan
        )
    else:
        df["carbon_intensity"] = np.nan

    meta = {
        "error": False,
        "timestamp_col": timestamp_col,
        "emission_col": emission_col,
        "industry_col": industry_col,
        "device_col": device_col,
        "energy_col": energy_col,
    }

    return df, meta


def reduction_recommendations(df, meta):
    emission_col = meta["emission_col"]
    device_col = meta["device_col"]

    avg_emission = df[emission_col].mean()
    peak_hour = df.groupby("hour")[emission_col].mean().idxmax()
    best_hour = df.groupby("hour")[emission_col].mean().idxmin()

    top_device = (
        df.groupby(device_col)[emission_col]
        .mean()
        .sort_values(ascending=False)
        .index[0]
    )

    tips = [
        f"Shift heavy operations away from hour {peak_hour}:00 where average emissions are highest.",
        f"Prefer scheduling non-urgent operations around hour {best_hour}:00 where average emissions are lowest.",
        f"Inspect and optimize the device '{top_device}' because it shows the highest average emissions.",
        "Use preventive maintenance and energy-efficient settings during high-load periods.",
        "Monitor carbon intensity regularly to reduce both emissions and operational cost."
    ]
    return tips, best_hour


def add_schedule_to_blockchain(best_hour, reason):
    blockchain.add_block(
        {
            "action": "Schedule Recommendation Saved",
            "recommended_hour": int(best_hour),
            "reason": reason,
            "saved_at": time(),
        }
    )


# ---------------------------
# TITLE
# ---------------------------
st.markdown(
    """
    <div class="title-box">
        <h1>🌍 Industrial Carbon Monitoring & Smart Scheduling</h1>
        <p>Track emissions, analyze device/industry trends, and save scheduling decisions on blockchain.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------
# SIDEBAR
# ---------------------------
st.sidebar.header("Data Input")
uploaded_file = st.sidebar.file_uploader("Upload CSV file", type=["csv"])

df_raw, data_source = load_data(uploaded_file)

if df_raw is None:
    st.warning("No dataset found. Upload a CSV file or keep a CSV in the same repo folder as app.py.")
    st.stop()

st.sidebar.success(f"Loaded from: {data_source}")

df, meta = preprocess_data(df_raw)

if meta["error"]:
    st.error(meta["message"])
    st.write("Columns found in your file:", list(df_raw.columns))
    st.stop()

timestamp_col = meta["timestamp_col"]
emission_col = meta["emission_col"]
industry_col = meta["industry_col"]
device_col = meta["device_col"]
energy_col = meta["energy_col"]

# ---------------------------
# FILTERS
# ---------------------------
st.sidebar.header("Filters")

industries = ["All"] + sorted(df[industry_col].dropna().unique().tolist())
devices = ["All"] + sorted(df[device_col].dropna().unique().tolist())

selected_industry = st.sidebar.selectbox("Select Industry", industries)
selected_device = st.sidebar.selectbox("Select Device", devices)

filtered_df = df.copy()

if selected_industry != "All":
    filtered_df = filtered_df[filtered_df[industry_col] == selected_industry]

if selected_device != "All":
    filtered_df = filtered_df[filtered_df[device_col] == selected_device]

if filtered_df.empty:
    st.warning("No records found for the selected filters.")
    st.stop()

# ---------------------------
# KPIs
# ---------------------------
total_emission = filtered_df[emission_col].sum()
avg_emission = filtered_df[emission_col].mean()
max_emission = filtered_df[emission_col].max()
peak_hour = filtered_df.groupby("hour")[emission_col].mean().idxmax()

if energy_col is not None:
    total_energy = filtered_df[energy_col].sum()
    avg_intensity = filtered_df["carbon_intensity"].mean()
else:
    total_energy = np.nan
    avg_intensity = np.nan

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric("Total CO₂ Emission", f"{total_emission:,.2f}")
with c2:
    st.metric("Average Emission", f"{avg_emission:,.2f}")
with c3:
    st.metric("Peak Emission", f"{max_emission:,.2f}")
with c4:
    st.metric("Peak Hour", f"{peak_hour}:00")

if energy_col is not None:
    c5, c6 = st.columns(2)
    with c5:
        st.metric("Total Energy", f"{total_energy:,.2f}")
    with c6:
        st.metric("Avg Carbon Intensity", f"{avg_intensity:,.4f}" if pd.notna(avg_intensity) else "N/A")

# ---------------------------
# DATA PREVIEW
# ---------------------------
with st.expander("Preview Dataset"):
    st.dataframe(filtered_df.head(20), use_container_width=True)

# ---------------------------
# CHARTS
# ---------------------------
st.subheader("Emission Trend Over Time")
daily_trend = filtered_df.groupby("day")[emission_col].sum().reset_index()

fig1, ax1 = plt.subplots(figsize=(10, 4))
ax1.plot(daily_trend["day"].astype(str), daily_trend[emission_col], marker="o")
ax1.set_xlabel("Day")
ax1.set_ylabel("CO₂ Emission")
ax1.set_title("Daily CO₂ Emission Trend")
plt.xticks(rotation=45)
plt.tight_layout()
st.pyplot(fig1)

col1, col2 = st.columns(2)

with col1:
    st.subheader("CO₂ Emission by Industry")
    industry_summary = (
        filtered_df.groupby(industry_col)[emission_col]
        .sum()
        .sort_values(ascending=False)
    )

    fig2, ax2 = plt.subplots(figsize=(8, 4))
    ax2.bar(industry_summary.index.astype(str), industry_summary.values)
    ax2.set_xlabel("Industry")
    ax2.set_ylabel("Total CO₂ Emission")
    ax2.set_title("Industry-wise Emissions")
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig2)

with col2:
    st.subheader("CO₂ Emission by Device")
    device_summary = (
        filtered_df.groupby(device_col)[emission_col]
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )

    fig3, ax3 = plt.subplots(figsize=(8, 4))
    ax3.bar(device_summary.index.astype(str), device_summary.values)
    ax3.set_xlabel("Device")
    ax3.set_ylabel("Total CO₂ Emission")
    ax3.set_title("Top Devices by Emissions")
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig3)

col3, col4 = st.columns(2)

with col3:
    st.subheader("Hourly Emission Pattern")
    hourly_pattern = filtered_df.groupby("hour")[emission_col].mean().reset_index()

    fig4, ax4 = plt.subplots(figsize=(8, 4))
    ax4.plot(hourly_pattern["hour"], hourly_pattern[emission_col], marker="o")
    ax4.set_xlabel("Hour of Day")
    ax4.set_ylabel("Average CO₂ Emission")
    ax4.set_title("Hour-wise Emission Pattern")
    plt.tight_layout()
    st.pyplot(fig4)

with col4:
    st.subheader("Emission Distribution")
    fig5, ax5 = plt.subplots(figsize=(8, 4))
    ax5.hist(filtered_df[emission_col].dropna(), bins=20)
    ax5.set_xlabel("CO₂ Emission")
    ax5.set_ylabel("Frequency")
    ax5.set_title("Distribution of Emissions")
    plt.tight_layout()
    st.pyplot(fig5)

if energy_col is not None:
    st.subheader("Energy vs CO₂ Emission")
    compare_df = filtered_df.dropna(subset=[energy_col, emission_col])

    if not compare_df.empty:
        fig6, ax6 = plt.subplots(figsize=(10, 4))
        ax6.scatter(compare_df[energy_col], compare_df[emission_col])
        ax6.set_xlabel("Energy")
        ax6.set_ylabel("CO₂ Emission")
        ax6.set_title("Energy vs CO₂ Emission")
        plt.tight_layout()
        st.pyplot(fig6)

# ---------------------------
# SMART SCHEDULING
# ---------------------------
st.subheader("Smart Scheduling Recommendation")

tips, best_hour = reduction_recommendations(filtered_df, meta)

hourly_avg = filtered_df.groupby("hour")[emission_col].mean().sort_values()
best_hours = hourly_avg.head(3).index.tolist()

st.write(f"**Recommended low-emission operating hour:** {best_hour}:00")
st.write(f"**Top 3 best hours:** {', '.join([str(h) + ':00' for h in best_hours])}")

for i, tip in enumerate(tips, start=1):
    st.write(f"{i}. {tip}")

reason_text = f"Recommended using lower-emission hour {best_hour}:00 based on average hourly emission analysis."

if st.button("Save Recommendation to Blockchain"):
    add_schedule_to_blockchain(best_hour, reason_text)
    st.success("Scheduling recommendation saved to blockchain.")

# ---------------------------
# ALERTS
# ---------------------------
st.subheader("Peak Emission Alerts")

threshold = st.slider(
    "Set CO₂ alert threshold",
    min_value=float(filtered_df[emission_col].min()),
    max_value=float(filtered_df[emission_col].max()),
    value=float(filtered_df[emission_col].mean()),
)

alert_df = filtered_df[filtered_df[emission_col] > threshold]

st.write(f"Records above threshold: **{len(alert_df)}**")

if not alert_df.empty:
    st.dataframe(
        alert_df[[timestamp_col, industry_col, device_col, emission_col]].head(20),
        use_container_width=True,
    )

# ---------------------------
# BLOCKCHAIN VIEW
# ---------------------------
st.subheader("Blockchain Ledger")

valid_status = "Valid ✅" if blockchain.is_chain_valid() else "Invalid ❌"
st.write(f"Chain Status: **{valid_status}**")

chain_df = pd.DataFrame(blockchain.get_chain())
st.dataframe(chain_df, use_container_width=True)

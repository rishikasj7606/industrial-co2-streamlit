import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from blockchain import Blockchain

# Load the blockchain
blockchain = Blockchain()

# Sidebar for file upload
st.sidebar.title("Carbon Emission Monitoring")
st.sidebar.markdown("Upload your industrial carbon emission dataset below:")

# File uploader
uploaded_file = st.sidebar.file_uploader("Choose a CSV file", type="csv")

# If a file is uploaded, read it
if uploaded_file:
    df = pd.read_csv(uploaded_file)
else:
    st.error("Please upload a dataset to proceed.")
    st.stop()

# Clean the dataset (you can modify this based on your dataset)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['carbon_emission'] = pd.to_numeric(df['carbon_emission'], errors='coerce')
df['industry'] = df['industry'].astype(str)
df['device'] = df['device'].astype(str)

# Display the data overview
st.header("Dataset Overview")
st.write(df.head())

# Plot emission trends over time
st.header("Emission Trends Over Time")
fig = px.line(df, x='timestamp', y='carbon_emission', title='CO₂ Emission Over Time')
st.plotly_chart(fig)

# Emission summary statistics
st.header("Emission Statistics")
st.write(f"Total CO₂ Emission: {df['carbon_emission'].sum():,.2f} tons")
st.write(f"Average CO₂ Emission per Hour: {df['carbon_emission'].mean():,.2f} tons")

# Carbon Emission by Industry
st.header("CO₂ Emission by Industry")
industry_emissions = df.groupby('industry')['carbon_emission'].sum().reset_index()
fig_industry = px.bar(industry_emissions, x='industry', y='carbon_emission', title="Carbon Emission by Industry")
st.plotly_chart(fig_industry)

# Scheduling Recommendation: Best Times for Operation
st.header("Scheduling Recommendation")
peak_times = df.groupby(df['timestamp'].dt.hour)['carbon_emission'].mean().reset_index()
fig_times = px.line(peak_times, x='timestamp', y='carbon_emission', title="CO₂ Emission by Hour")
st.plotly_chart(fig_times)

best_time = peak_times.loc[peak_times['carbon_emission'].idxmin(), 'timestamp']
st.write(f"The best time to reduce emissions is at {best_time}:00 hours.")

# Add scheduling decision to blockchain
if st.button('Save Scheduling Decision'):
    blockchain.add_block({
        "action": "Scheduling Recommendation",
        "best_time": best_time,
        "timestamp": time(),
    })
    st.success("Scheduling decision saved to blockchain!")

# View blockchain
st.header("Blockchain Ledger")
st.write(blockchain.get_chain())

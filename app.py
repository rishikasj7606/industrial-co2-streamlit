import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from blockchain import Blockchain

# -------------------------------
# Load Processed Data
# -------------------------------
df = pd.read_csv("industrial_carbon_monitoring.csv")
df['timestamp'] = pd.to_datetime(df['timestamp'])

# -------------------------------
# Initialize Blockchain
# -------------------------------
bc = Blockchain()

# -------------------------------
# Sidebar Filters
# -------------------------------
st.sidebar.title("Industrial CO2 Monitoring")
industry_list = df['industry'].unique()
selected_industry = st.sidebar.selectbox("Select Industry", industry_list)

device_list = df[df['industry']==selected_industry]['device_state'].unique()
selected_device = st.sidebar.selectbox("Select Device State", device_list)

# -------------------------------
# Filter Data
# -------------------------------
filtered_df = df[(df['industry']==selected_industry) & 
                 (df['device_state']==selected_device)]

st.write(f"### {selected_industry} - {selected_device} Emissions Overview")
st.write(filtered_df.describe())

if st.button("Record to Blockchain"):
    for i, row in filtered_df.head(50).iterrows():  # only first 50 rows
        data = {
            "timestamp": str(row['timestamp']),
            "industry": row['industry'],
            "device_state": row['device_state'],
            "co2_kg": row['co2_kg'],
            "energy_kwh": row['energy_kwh']
        }
        bc.add_block(data)
    st.success("Data recorded to blockchain!")


# Show Latest Block
st.write("#### Latest Blockchain Block")
st.json(bc.chain[-1].__dict__)


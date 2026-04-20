#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os
os.getcwd()


# In[2]:


os.getcwd()


# In[3]:


# ==========================================================
# streamlit_app.py
# Front-end dashboard for your existing Flask forecast API
# Run:
#   1) python app.py
#   2) streamlit run streamlit_app.py
# ==========================================================

import streamlit as st
import requests
import pandas as pd

# ----------------------------------------------------------
# PAGE CONFIG
# ----------------------------------------------------------
st.set_page_config(
    page_title="Warehouse VET / VTO Forecast",
    layout="wide"
)

st.title("Warehouse Workforce Forecast Dashboard")
st.caption("Machine Learning Demand Forecasting + VET / VTO Recommendations")

# ----------------------------------------------------------
# SIDEBAR INPUTS
# ----------------------------------------------------------
st.sidebar.header("Scenario Inputs")

weeks = st.sidebar.slider("Forecast Horizon (Weeks)", 1, 12, 12)

temp = st.sidebar.number_input("Temperature", value=45.0)
fuel = st.sidebar.number_input("Fuel Price", value=3.2)
cpi = st.sidebar.number_input("CPI", value=225.0)
unemployment = st.sidebar.number_input("Unemployment", value=6.5)

scenario_name = st.sidebar.text_input(
    "Scenario Name",
    value="Standard Forecast"
)

request_id = st.sidebar.text_input(
    "Request ID",
    value="REQ001"
)

run_button = st.sidebar.button("Run Forecast")

# ----------------------------------------------------------
# MAIN ACTION
# ----------------------------------------------------------
if run_button:

    # ------------------------------------------------------
    # BUILD PAYLOAD TO SEND TO FLASK API
    # ------------------------------------------------------
    payload = {
        "request_id": request_id,
        "scenario_name": scenario_name,
        "weeks": weeks,

        "inputs": {
            "temperature": [temp] * weeks,
            "fuel_price": [fuel] * weeks,
            "cpi": [cpi] * weeks,
            "unemployment": [unemployment] * weeks,
            "isholiday": [0] * weeks
        }
    }

    # ------------------------------------------------------
    # CALL YOUR FLASK API
    # ------------------------------------------------------
    try:
        response = requests.post(
            "http://backend:5000/forecast",
            json=payload,
            timeout=30
        )

        data = response.json()

    except Exception as e:
        st.error("Could not connect to Flask API.")
        st.stop()

    # ------------------------------------------------------
    # SUCCESS HEADER
    # ------------------------------------------------------
    st.success("Forecast Completed")

    # ------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------
    summary = data["summary"]

    st.subheader("Executive Summary")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("VET Weeks", summary["vet_weeks"])
    c2.metric("VTO Weeks", summary["vto_weeks"])
    c3.metric("Peak Week", summary["peak_demand_week"])
    c4.metric("Total Cost", f"${summary['total_cost']:,.0f}")

    # ------------------------------------------------------
    # FORECAST TABLE
    # ------------------------------------------------------
    st.subheader("12 Week Forecast Output")

    forecast_df = pd.DataFrame(data["forecast"])

    st.dataframe(
        forecast_df,
        use_container_width=True
    )

    # ------------------------------------------------------
    # CHART
    # ------------------------------------------------------
    st.subheader("Predicted Demand Trend")

    chart_df = forecast_df[["week", "predicted_demand"]]
    chart_df = chart_df.set_index("week")

    st.line_chart(chart_df)

    # ------------------------------------------------------
    # RECOMMENDATIONS
    # ------------------------------------------------------
    st.subheader("Operational Recommendations")

    recommendations = data.get("recommendations", [])

    if len(recommendations) == 0:
        st.info("No recommendations returned.")

    for rec in recommendations:

        txt = rec.lower()

        if "increase staffing" in txt:
            st.warning("⚠️ " + rec)

        elif "vto" in txt:
            st.success("💰 " + rec)

        elif "highest demand" in txt or "peak" in txt:
            st.error("🔥 " + rec)

        elif "cost" in txt or "savings" in txt:
            st.info("📈 " + rec)

        else:
            st.write("• " + rec)

    # ------------------------------------------------------
    # RAW JSON (OPTIONAL)
    # ------------------------------------------------------
    with st.expander("View Raw JSON Response"):
        st.json(data)

else:
    st.info("Use the left sidebar inputs, then click Run Forecast.")


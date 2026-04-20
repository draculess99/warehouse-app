#!/usr/bin/env python
# coding: utf-8

# # Run Streamllit App
# 
# ```bash
# streamlit run streamlit_app.py
# ```
# 

# In[1]:


import os
os.getcwd()


# In[2]:


os.getcwd()


# In[1]:


# ==========================================================
# streamlit_app.py
# Warehouse Workforce Forecast Dashboard
# FULL VERSION with SIMPLE + ADVANCED WEEKLY TABLE MODE
# ==========================================================

import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# ----------------------------------------------------------
# PAGE CONFIG
# ----------------------------------------------------------
st.set_page_config(
    page_title="Warehouse Workforce Forecast Dashboard 2012",
    layout="wide"
)

st.title("Warehouse Workforce Forecast Dashboard 2012")
st.caption("Machine Learning Demand Forecasting + VET / VTO Recommendations")

# ----------------------------------------------------------
# SIDEBAR
# ----------------------------------------------------------
st.sidebar.header("Scenario Inputs")

# Weeks
weeks = st.sidebar.slider("Forecast Horizon (Weeks)", 1, 43, 12)

# Input Mode
mode = st.sidebar.radio(
    "Input Mode",
    ["Simple Scenario", "Advanced Weekly Table"]
)

workers_per_unit = st.sidebar.number_input("Worker Per Unit", value=5000)
overtime_labor_cost_per_worker = st.sidebar.number_input("Ovetime labor Cost/Hr Per Worker", value=30)
hourly_labor_cost_per_worker = st.sidebar.number_input("Hourly labor Cost Per Worker", value=20)

# ----------------------------------------------------------
# SIMPLE MODE
# ----------------------------------------------------------
if mode == "Simple Scenario":

    temperature = st.sidebar.number_input("Temperature", value=45.0)
    fuel_price = st.sidebar.number_input("Fuel Price", value=3.2)
    cpi = st.sidebar.number_input("CPI", value=225.0)
    unemployment = st.sidebar.number_input("Unemployment", value=6.5)
    holiday = st.sidebar.selectbox("Holiday Week?", [0, 1])



    scenario_name = st.sidebar.text_input(
        "Scenario Name",
        value="Standard Forecast"
    )

    request_id = st.sidebar.text_input(
        "Request ID",
        value="REQ001"
    )

    st.sidebar.subheader("Operational Stress Controls for Multi-Week Stress Simulation")

    velocity_pct = st.sidebar.slider(
        "Demand Velocity %",
        -20,
        20,
        0
    )

    shipping_delay_pct = st.sidebar.slider(
        "Shipping Delay %",
        0,
        30,
        0
    )

    congestion_pct = st.sidebar.slider(
        "Warehouse Congestion %",
        0,
        30,
        0
    )

    logistics_stress_pct = st.sidebar.slider(
        "Logistics Stress %",
        0,
        30,
        0
    )

    payload = {
        "mode": "simple",

        "request_id": request_id,
        "scenario_name": scenario_name,
        "weeks": weeks,
        "inputs": {
            "temperature": [temperature] * weeks,
            "fuel_price": [fuel_price] * weeks,
            "cpi": [cpi] * weeks,
            "unemployment": [unemployment] * weeks,
            "isholiday": [holiday] * weeks
        },
        "settings": {
            "workers_per_unit": workers_per_unit,
            "overtime_labor_cost_per_worker": overtime_labor_cost_per_worker,
            "hourly_labor_cost_per_worker": hourly_labor_cost_per_worker,
            "velocity_pct": velocity_pct,
            "shipping_delay_pct": shipping_delay_pct,
            "congestion_pct": congestion_pct,
            "logistics_stress_pct": logistics_stress_pct
        }
    }

# ----------------------------------------------------------
# ADVANCED MODE
# ----------------------------------------------------------
else:

    st.subheader("Advanced Weekly Scenario Table")

    default_df = pd.DataFrame({
        "week": range(1, weeks + 1),

        "temperature": [45.0] * weeks,
        "fuel_price": [3.2] * weeks,
        "cpi": [225.0] * weeks,
        "unemployment": [6.5] * weeks,
        "isholiday": [0] * weeks,

        "velocity_pct": [0] * weeks,
        "shipping_delay_pct": [0] * weeks,
        "congestion_pct": [0] * weeks,
        "logistics_stress_pct": [0] * weeks
    })

    edited_df = st.data_editor(
        default_df,
        use_container_width=True,
        num_rows="fixed"
    )

    scenario_name = st.sidebar.text_input(
        "Scenario Name",
        value="Advanced Scenario"
    )

    request_id = st.sidebar.text_input(
        "Request ID",
        value="REQ002"
    )

    payload = {
        "mode": "advanced",

        "request_id": request_id,
        "scenario_name": scenario_name,
        "weeks": weeks,
        "inputs": {
            "temperature": edited_df["temperature"].tolist(),
            "fuel_price": edited_df["fuel_price"].tolist(),
            "cpi": edited_df["cpi"].tolist(),
            "unemployment": edited_df["unemployment"].tolist(),
            "isholiday": edited_df["isholiday"].tolist()
        },
        "settings": {
            "workers_per_unit": workers_per_unit,
            "overtime_labor_cost_per_worker": overtime_labor_cost_per_worker,
            "hourly_labor_cost_per_worker": hourly_labor_cost_per_worker,
            "velocity_pct": edited_df["velocity_pct"].tolist(),
            "shipping_delay_pct": edited_df["shipping_delay_pct"].tolist(),
            "congestion_pct": edited_df["congestion_pct"].tolist(),
            "logistics_stress_pct": edited_df["logistics_stress_pct"].tolist()
        }
    }
    #st.write(payload["settings"])

# ----------------------------------------------------------
# RUN BUTTON
# ----------------------------------------------------------
if st.sidebar.button("Run Forecast"):

    try:
        # IMPORTANT:
        # Local:
        #api_url = "http://localhost:5000/forecast"
        #
        # Docker:
        api_url = "https://warehouse-backend-n7on.onrender.com/forecast"

        response = requests.post(api_url, json=payload)

        if response.status_code == 200:

            data = response.json()

            st.success("Forecast Completed")

            # --------------------------------------------------
            # Executive Summary
            # --------------------------------------------------
            st.subheader("Executive Summary")

            col1, col2, col3, col4 = st.columns(4)

            col1.metric("VET Weeks", data["summary"]["vet_weeks"])
            col2.metric("VTO Weeks", data["summary"]["vto_weeks"])
            col3.metric("Peak Week", data["summary"]["normal_weeks"])
            col4.metric(
                "Total Cost",
                f'${data["summary"]["total_cost"]:,.0f}'
            )

            # --------------------------------------------------
            # Output Table
            # --------------------------------------------------
            st.subheader("Forecast Output")

            df_out = pd.DataFrame(data["forecast"])
            result_df = pd.DataFrame(data["forecast"])

            common_layout = dict(
                height=260,
                margin=dict(l=20, r=20, t=45, b=20),
                title_x=0.0
            )

            #Demand Forecast Chart
            fig1 = px.line(
                result_df,
                x="week",
                y="predicted_demand",
                markers=True,
                title=f"{weeks} Week Demand Forecast"
            )

            #Cost Chart
            fig2 = px.bar(
                result_df,
                x="week",
                y="estimated_cost",
                color="decision",
                title="Weekly Labor Cost"
            )

            fig1.update_layout(**common_layout)
            fig2.update_layout(**common_layout)

            #Cost Cumulative Cost Chart
            fig3 = px.line(
                result_df,
                x="week",
                y="cumulative_future_cost",
                markers=True,
                title="Cumulative Future Cost"
            )

            fig3.update_layout(
                height=260,
                margin=dict(l=10, r=10, t=35, b=10)
            )

            # ==================================
            # LAYOUT
            # ==================================
            col1, col2 = st.columns(2)

            with col1:
                st.plotly_chart(
                    fig1,
                    use_container_width=True
                )

            with col2:
                st.plotly_chart(
                    fig2,
                    use_container_width=True
                )

            colA, colB, colC = st.columns([1,2,1])

            with colB:
                st.plotly_chart(fig3)

            # st.dataframe(df_out, use_container_width=True)

            with st.expander("Detailed Forecast Table"):
                # st.dataframe(result_df)

                styled_df = result_df.style.format({

                    "week": "{:.0f}",
                    "predicted_demand": "{:,.0f}",
                    "estimated_cost": "${:,.0f}",
                    "cumulative_future_cost": "${:,.0f}",
                    "extra_workers_needed": "{:.0f}",
                    "workers_to_reduce": "{:.0f}"

                }).set_properties(

                    subset=[
                        "predicted_demand",
                        "estimated_cost",
                        "cumulative_future_cost",
                        "extra_workers_needed",
                        "workers_to_reduce"
                    ],

                    **{
                        "text-align": "right"
                    }

                ).set_properties(

                    subset=["week", "decision"],

                    **{
                            "text-align": "center"
                    }

                ).apply(

                    lambda row: [

                        (
                            "background-color:#145a32;"
                            "color:white;"
                            "font-weight:bold;"
                            "text-align:center;"
                            "border-radius:4px;"

                            if (col == "decision" and row["decision"] == "VET")

                            else

                            "background-color:#7d5a00;"
                            "color:white;"
                            "font-weight:bold;"
                            "text-align:center;"
                            "border-radius:4px;"

                            if (col == "decision" and row["decision"] == "VTO")

                            else

                            "background-color:#444444;"
                            "color:white;"
                            "font-weight:bold;"
                            "text-align:center;"
                            "border-radius:4px;"

                            if (col == "decision" and row["decision"] == "NORMAL")

                            else ""

                        )

                        for col in row.index

                    ],

                    axis=1

                ).set_table_styles([

                    {
                        "selector": "th",
                        "props": [
                            ("background-color", "#111111"),
                            ("color", "white"),
                            ("font-weight", "bold"),
                            ("text-align", "center")
                        ]
                    },

                    {
                        "selector": "td",
                        "props": [
                            ("border", "1px solid #333333"),
                            ("padding", "6px")
                        ]
                    }

                ])

                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    height=420
                )

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
            st.error("Backend returned an error.")


    except Exception as e:
        st.error(f"Could not connect to Flask API: {str(e)}")


# In[ ]:





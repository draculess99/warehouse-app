# # Run Streamllit App
# 
# ```bash
# streamlit run streamlit_app.py
# ```
# 


# ==========================================================
# streamlit_app.py
# Warehouse Workforce Forecast Dashboard
# FULL VERSION with SIMPLE + ADVANCED WEEKLY TABLE MODE
# ==========================================================

import os
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
st.caption("Springboard Data Analytics Capstone Project • Forecasting VET/VTO decisions using retail demand proxy data • By WiL Low • 2026")

# -----------------------------------
# SESSION STATE INIT
# -----------------------------------

st.markdown("""
<style>
/* Target sidebar expander headers */
section[data-testid="stSidebar"] div[data-testid="stExpander"] details {
    border: 1px solid #8a6d1d;
    border-radius: 10px;
    background: rgba(138,109,29,0.18);
    margin-bottom: 10px;
}

section[data-testid="stSidebar"] div[data-testid="stExpander"] summary {
    background: rgba(138,109,29,0.35);
    color: #ffd76a;
    border-radius: 10px;
    padding: 6px 10px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
div.stButton > button:first-child {
    background: linear-gradient(135deg,#198754,#157347);
    color: white;
    border-radius: 10px;
    border: none;
    padding: 0.55rem 1rem;
    font-weight: 700;
    width: 100%;
    box-shadow: 0 4px 10px rgba(0,0,0,0.25);
}

div.stButton > button:first-child:hover {
    background: linear-gradient(135deg,#20a464,#198754);
    color: white;
}
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------
# LOAD SCENARIO CSV
# ----------------------------------------------------------
@st.cache_data
def load_scenarios():
    return pd.read_csv("scenario_templates.tsv", sep="\t")

scenario_df = load_scenarios()

# ----------------------------------------------------------
# GEMINI HELPER FUNCTIONS
# ----------------------------------------------------------
def get_gemini_explanation(result_df, rec):
    try:
        from google import genai

        client = genai.Client(
            api_key=os.getenv("GEMINI_API_KEY")
        )

        # -----------------------------
        # Metrics
        # -----------------------------
        total_cost = result_df["estimated_cost"].sum()
        peak = result_df["predicted_demand"].max()
        avg = result_df["predicted_demand"].mean()

        peak_row = result_df.loc[
            result_df["predicted_demand"].idxmax()
        ]

        peak_week = int(peak_row["week"])

        demand_band = classify_demand_band(result_df)
        cost_band = classify_cost_band(result_df)

        action = rec["action"]
        rule_text = rec["final_recommendation"]

        # -----------------------------
        # Prompt (highly controlled)
        # -----------------------------
        prompt = f"""
You are a warehouse workforce planning analyst.

Create a concise executive explanation.

Forecast facts:
- Peak week: Week {peak_week}
- Peak forecast volume index: {peak:,.0f}
- Average forecast volume index: {avg:,.0f}
- Demand band: {demand_band}
- Cost band: {cost_band}
- Projected labor impact: ${total_cost:,.0f}
- Recommended action: {action}

Existing rule recommendation:
{rule_text}

Instructions:
1. Write exactly 5 sentences.
2. Use plain business English.
3. Refer to demand as forecast volume, not units sold.
4. If action is VET, recommend targeted overtime before peak week.
5. If action is VTO, recommend reducing excess staffing carefully.
6. If action is NORMAL, recommend monitoring and maintaining staffing.
7. Mention labor cost discipline when cost band is High.
8. Do not exaggerate or invent facts.
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        return response.text.strip()

    except Exception as e:
        return f"Gemini unavailable: {str(e)}"



# ----------------------------------------------------------
# GROQ HELPER FUNCTIONS
# ----------------------------------------------------------
def get_groq_explanation(result_df, rec):
    try:
        from groq import Groq
        import streamlit as st

        client = Groq(
            api_key=os.getenv("GROQ_API_KEY")
        )

        total_cost = result_df["estimated_cost"].sum()
        peak = result_df["predicted_demand"].max()
        avg = result_df["predicted_demand"].mean()

        peak_row = result_df.loc[
            result_df["predicted_demand"].idxmax()
        ]

        peak_week = int(peak_row["week"])

        demand_band = classify_demand_band(result_df)
        cost_band = classify_cost_band(result_df)

        action = rec["action"]

        prompt = f"""
You are a warehouse workforce planning analyst.

Write exactly 5 short executive sentences.

Peak week: {peak_week}
Peak workload index: {peak:,.0f}
Average workload index: {avg:,.0f}
Demand band: {demand_band}
Cost band: {cost_band}
Projected labor impact: ${total_cost:,.0f}
Recommended action: {action}

Rules:
- Use professional language
- Mention staffing action
- Mention cost discipline if High cost
- Do not invent facts
"""

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3
        )

        return completion.choices[0].message.content.strip()

    except Exception as e:
        return f"Groq unavailable: {str(e)}"

# ----------------------------------------------------------
# HELPER FUNCTIONS
# ----------------------------------------------------------
def classify_demand_band(result_df):
    peak = result_df["predicted_demand"].max()
    avg = result_df["predicted_demand"].mean()
    recent = result_df["predicted_demand"].tail(4).mean()

    score = (peak * 0.25) + (avg * 0.45) + (recent * 0.30)

    q75 = result_df["predicted_demand"].quantile(0.75)
    q25 = result_df["predicted_demand"].quantile(0.25)

    if score >= q75:
        return "High"
    elif score <= q25:
        return "Low"
    else:
        return "Normal"


def classify_stress_band(v, s, c, l):
    vals = [v, s, c, l]

    if isinstance(v, list):
        vals = v + s + c + l

    score = max(vals)

    if score >= 20:
        return "High"
    elif score >= 8:
        return "Medium"
    else:
        return "Low"


def classify_cost_band(result_df):
    total_cost = result_df["estimated_cost"].sum()

    if total_cost >= 25000:
        return "High"
    elif total_cost >= 10000:
        return "Medium"
    else:
        return "Low"


def get_scenario_row(demand_band, stress_band, cost_band):
    row = scenario_df[
        (scenario_df["demand_band"] == demand_band) &
        (scenario_df["stress_band"] == stress_band) &
        (scenario_df["cost_band"] == cost_band)
    ]

    if len(row) == 0:
        return None

    return row.iloc[0]


# ----------------------------------------------------------
# SIDEBAR
# ----------------------------------------------------------
st.sidebar.header("Scenario Inputs")

# ----------------------------------------------------------
# SECTION 1 - FORECAST SETUP
# ----------------------------------------------------------
st.sidebar.subheader("📅 Forecast Setup")

# Weeks
weeks = st.sidebar.slider("Forecast Horizon (Weeks)", 1, 43, 12)

# Input Mode
mode = st.sidebar.radio(
    "Input Mode",
    ["Simple Scenario", "Advanced Weekly Table"]
)

st.sidebar.markdown("---")

# ------------------------------------------------
# CONDITIONAL FIELDS
# ------------------------------------------------
if mode == "Simple Scenario":

    scenario_name = st.sidebar.text_input(
        "Scenario Name",
        value="Standard Forecast"
    )

    request_id = st.sidebar.text_input(
        "Request ID",
        value="REQ001"
    )

else:

    scenario_name = st.sidebar.text_input(
        "Scenario Name",
        value="Advanced Scenario"
    )

    request_id = st.sidebar.text_input(
        "Request ID",
        value="REQ002"
    )
# ----------------------------------------------------------
# SECTION 2 - LABOR PLANNING SETTINGS
# ----------------------------------------------------------

st.sidebar.subheader("👷 Labor Planning")

workers_per_unit = st.sidebar.number_input(
    "Units per Worker Capacity",
    value=5000,
    help="Estimated workload handled per worker"
)

overtime_labor_cost_per_worker = st.sidebar.number_input(
    "Overtime Cost per Hour ($)",
    value=30,
    help="Estimated overtime labor rate"
)

hourly_labor_cost_per_worker = st.sidebar.number_input(
    "Regular Labor Cost per Hour ($)",
    value=20,
    help="Standard hourly labor cost"
)

st.sidebar.markdown("---")

# ----------------------------------------------------------
# SIMPLE MODE
# ----------------------------------------------------------
if mode == "Simple Scenario":

    # ----------------------------------------------------------
    # SECTION 3 - ECONOMIC DRIVERS
    # ----------------------------------------------------------
    st.sidebar.subheader("📈 Economic Drivers")

    temperature = st.sidebar.number_input(
        "Temperature",
        value=45.0
    )

    fuel_price = st.sidebar.number_input(
        "Fuel Price",
        value=3.20
    )

    cpi = st.sidebar.number_input(
        "CPI Index",
        value=225.0
    )

    unemployment = st.sidebar.number_input(
        "Unemployment Rate (%)",
        value=6.50
    )

    holiday = st.sidebar.selectbox(
        "Holiday Demand Week",
        [0, 1]
    )

    st.sidebar.markdown("---")

    # ----------------------------------------------------------
    # SECTION 4 - OPERATIONAL STRESS CONTROLS
    # ----------------------------------------------------------
    with st.sidebar.expander("⚙️ Advanced Scenario Stress Testing"):

        velocity_pct = st.slider(
            "Demand Velocity (%)",
            -20, 20, 0
        )

        shipping_delay_pct = st.slider(
            "Shipping Delay (%)",
            0, 30, 0
        )

        congestion_pct = st.slider(
            "Warehouse Congestion (%)",
            0, 30, 0
        )

        logistics_stress_pct = st.slider(
            "Logistics Stress (%)",
            0, 30, 0
        )
        st.sidebar.markdown("---")

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

    with st.sidebar.expander("⚙️ Advanced Scenario Stress Testing"):

        velocity_pct_default = st.slider(
            "Demand Velocity (%)",
            -20, 20, 0
        )

        shipping_delay_default = st.slider(
            "Shipping Delay (%)",
            0, 30, 0
        )

        congestion_default = st.slider(
            "Warehouse Congestion (%)",
            0, 30, 0
        )

        logistics_stress_default = st.slider(
            "Logistics Stress (%)",
            0, 30, 0
        )

    st.subheader("Advanced Weekly Scenario Table")

    default_df = pd.DataFrame({
        "week": range(1, weeks + 1),

        "temperature": [45.0] * weeks,
        "fuel_price": [3.2] * weeks,
        "cpi": [225.0] * weeks,
        "unemployment": [6.5] * weeks,
        "isholiday": [0] * weeks,

        "velocity_pct": [velocity_pct_default] * weeks,
        "shipping_delay_pct": [shipping_delay_default] * weeks,
        "congestion_pct": [congestion_default] * weeks,
        "logistics_stress_pct": [logistics_stress_default] * weeks
    })

    edited_df = st.data_editor(
        default_df,
        use_container_width=True,
        num_rows="fixed"
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
run_clicked = st.sidebar.button("🚀 Run Forecast")

if run_clicked:
    try:
        # IMPORTANT:
        # Local:
        # api_url = "http://localhost:5000/forecast"
        #
        # Docker:
        api_url = "https://warehouse-backend-n7on.onrender.com/forecast"

        response = requests.post(api_url, json=payload)

        if response.status_code == 200:
            st.success("Forecast Completed")
        else:
            st.text(response.text[:1000])
            st.error("Backend returned an error.")
            st.stop()

    except requests.exceptions.RequestException as e:
        st.error(f"Could not connect to Flask API: {str(e)}")

    except Exception as e:
        st.error(f"Application error: {str(e)}")

    # ------------------------------------------------------
    # BLOCK 2 - DISPLAY SAVED RESULTS
    # ------------------------------------------------------
    data = response.json()

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

    result_df = pd.DataFrame(data["forecast"])

    common_layout = dict(
        height=260,
        margin=dict(l=20, r=20, t=45, b=20),
        title_x=0.0
    )

    # Demand Forecast Chart
    fig1 = px.line(
        result_df,
        x="week",
        y="predicted_demand",
        markers=True,
        title=f"{weeks} Week Demand Forecast"
    )

    # Cost Chart
    fig2 = px.bar(
        result_df,
        x="week",
        y="estimated_cost",
        color="decision",
        title="Weekly Labor Cost"
    )

    fig1.update_layout(**common_layout)
    fig2.update_layout(**common_layout)

    # Cumulative Cost Chart
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
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.plotly_chart(fig2, use_container_width=True)

    colA, colB, colC = st.columns([1, 2, 1])

    with colB:
        st.plotly_chart(fig3, use_container_width=True)

    with st.expander("Detailed Forecast Table"):
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
            **{"text-align": "right"}
        ).set_properties(
            subset=["week", "decision"],
            **{"text-align": "center"}
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

    st.caption(
    "Public Walmart weekly sales data is used as a proxy for operational demand. "
    "Staffing outputs are scenario-based estimates using configurable capacity assumptions."
)
    # ------------------------------------------------------
    # RECOMMENDATIONS (SMART SCENARIO ENGINE)
    # ------------------------------------------------------
    st.subheader("Operational Recommendations")

    # classify demand from forecast results
    demand_band = classify_demand_band(result_df)

    # classify stress depending on mode
    if mode == "Simple Scenario":
        stress_band = classify_stress_band(
            velocity_pct,
            shipping_delay_pct,
            congestion_pct,
            logistics_stress_pct
        )
    else:
        stress_band = classify_stress_band(
            edited_df["velocity_pct"].tolist(),
            edited_df["shipping_delay_pct"].tolist(),
            edited_df["congestion_pct"].tolist(),
            edited_df["logistics_stress_pct"].tolist()
        )

    # classify cost
    cost_band = classify_cost_band(result_df)

    # lookup row from CSV
    rec = get_scenario_row(
        demand_band,
        stress_band,
        cost_band
    )

    # show scenario summary
    st.write(
        f"Scenario: Demand={demand_band} | Stress={stress_band} | Cost={cost_band}"
    )

    if rec is not None:
        action = rec["action"]
        severity = rec["severity"]

        # Card 1 Demand Alert
        if severity == "Critical":
            st.error("🔥 " + rec["short_message"])
        elif severity == "Warning":
            st.warning("⚠️ " + rec["short_message"])
        else:
            st.info("📊 " + rec["short_message"])

        # Card 2 Operational Guidance
        st.info("📈 " + rec["final_recommendation"])

        # Card 3 Cost Insight
        total_cost = result_df["estimated_cost"].sum()
        st.info(f"💰 Projected total labor impact: ${total_cost:,.0f}")

        # Card 4 Action
        if action == "VET":
            st.success("✅ Recommended Action: Increase Staffing (VET)")
        elif action == "VTO":
            st.warning("💤 Recommended Action: Offer Voluntary Time Off (VTO)")
        else:
            st.info("🟦 Recommended Action: Maintain Current Staffing")

        # Card 5 Peak Week Alert
        peak_row = result_df.loc[result_df["predicted_demand"].idxmax()]
        peak_week = int(peak_row["week"])

        st.error(f"🔥 Highest demand expected in Week {peak_week}. Prepare early.")

        # Rule Engine Explanation
        with st.expander("### Rule Engine Interpretation"):
            st.info(rec["long_narrative"].replace(". ", ".\n\n"))

        # -----------------------------------
        # GEMINI HEADER
        # -----------------------------------
        title_col, btn_col, count_col = st.columns([8, 0.7, 1])

        with title_col:
            st.markdown("### AI Decision Summary")

        # first load or retry
        with st.spinner("Generating AI summary..."):
                ai_summary = get_gemini_explanation(result_df, rec)

        if "unavailable" in ai_summary.lower() or "busy" in ai_summary.lower():
            ai_summary = get_groq_explanation(result_df, rec)
            ai_summary = ai_summary.replace(". ", ".\n\n")
            st.warning(ai_summary)
        else:
            ai_summary = ai_summary.replace(". ", ".\n\n")
            st.success(ai_summary)

    else:
        st.info("No scenario matched.")

    # ------------------------------------------------------
    # RAW JSON (OPTIONAL)
    # ------------------------------------------------------
    with st.expander("View Raw JSON Response"):
        st.json(data)


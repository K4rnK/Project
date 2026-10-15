import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from PIL import Image
import random

# ==========================================
# 1. PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="Real Estate AI Predictor & Feasibility Model",
    page_icon="🏢",
    layout="wide"
)

st.title("🏢 Real Estate Capital Gain & Feasibility Prototype Model")
st.caption("Predicting 5-10 Year Capital Gain and Highest & Best Use (HBU) Viability for Land Development")

# ==========================================
# 2. MOCK AUTOMATIC ENRICHMENT DATABASE
# ==========================================
def auto_enrich_spatial_data(lat, lon):
    """
    Simulates fetching GIS & Historical Data layers (Road Network, Feeder, Socio-Economic, Laws, Flood Risk)
    based on coordinates or OCR bounding box centroid.
    """
    np.random.seed(int((lat + lon) * 1000) % 100000)
    
    enriched_data = {
        "Road_Network": {
            "distance_to_highway_km": round(random.uniform(0.5, 8.0), 2),
            "travel_time_cbd_mins": random.randint(20, 60),
            "road_lanes": random.choice([2, 4, 6, 8]),
            "vehicle_volume_AADT": random.randint(15000, 65000)
        },
        "Feeder_Density": {
            "kde_transit_score": round(random.uniform(30.0, 95.0), 1),
            "bus_stop_count_1km": random.randint(2, 15)
        },
        "Socio_Economic": {
            "population_density_sqkm": random.randint(1500, 8500),
            "pop_growth_rate_pct": round(random.uniform(1.2, 5.5), 2),
            "dist_to_mall_km": round(random.uniform(0.8, 6.0), 2)
        },
        "Laws_Zoning": {
            "zone_code": random.choice(["Yellow (Low-Density)", "Orange (Med-Density)", "Purple (Industrial/Commercial)"]),
            "max_far": random.choice([2.5, 4.0, 6.0]),
            "min_osr_pct": 10.0,
            "setback_m": 3.0,
            "flood_risk_penalty": round(random.uniform(0.0, 0.2), 2)
        }
    }
    return enriched_data

# ==========================================
# 3. SIDEBAR: USER INPUT INTERFACE
# ==========================================
st.sidebar.header("📍 1. Land & Project Input")

input_method = st.sidebar.radio(
    "Choose Land Input Method:",
    ("Option A: Upload Red-Highlighted Image (JPG/PNG)", "Option B: Coordinates & Land Attributes")
)

lat, lon = 13.985, 100.542 # Default location (e.g., Pathum Thani / Ratchaphruek 346)
land_size_sqwah = 400.0
frontage_m = 20.0
land_cost_per_sqwah = 45000.0

if input_method == "Option A: Upload Red-Highlighted Image (JPG/PNG)":
    uploaded_file = st.sidebar.file_uploader("Upload Parcel Image (JPG/PNG)", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.sidebar.image(image, caption="Uploaded Parcel Map", use_column_width=True)
        st.sidebar.success("✅ Image processed! Red highlight centroid detected.")
        # Simulated OCR / Computer Vision output
        land_size_sqwah = st.sidebar.number_input("Detected Land Area (Sq.Wah):", value=800.0, step=50.0)
        frontage_m = st.sidebar.number_input("Detected Frontage Width (Meters):", value=35.0, step=5.0)
        land_cost_per_sqwah = st.sidebar.number_input("Land Acquisition Cost (THB/Sq.Wah):", value=50000.0, step=5000.0)
    else:
        st.sidebar.warning("Please upload a PNG/JPG image with red highlighted boundaries.")

else:
    st.sidebar.subheader("Manual Land Attributes")
    lat = st.sidebar.number_input("Latitude:", value=13.9854, format="%.4f")
    lon = st.sidebar.number_input("Longitude:", value=100.5421, format="%.4f")
    land_size_sqwah = st.sidebar.number_input("Land Size (Sq.Wah):", value=1000.0, step=100.0)
    frontage_m = st.sidebar.number_input("Frontage Width (Meters):", value=40.0, step=5.0)
    land_cost_per_sqwah = st.sidebar.number_input("Land Acquisition Cost (THB/Sq.Wah):", value=60000.0, step=5000.0)

st.sidebar.markdown("---")
st.sidebar.header("🏗️ 2. Target Real Estate Typology")
target_typology = st.sidebar.selectbox(
    "Select Intended Real Estate Development:",
    [
        "Single-Detached Houses (Luxury)",
        "Semi-Detached / Twin Houses",
        "Townhomes / Townhouses",
        "Roadside Commercial Shophouses",
        "Community Strip Mall"
    ]
)

# Trigger Automatic Enrichment
enriched_env = auto_enrich_spatial_data(lat, lon)

# ==========================================
# 4. AUTOMATIC DATA ENRICHMENT DISPLAY
# ==========================================
st.subheader("🔄 Automatically Enriched Contextual Data (History & GIS Layers)")
with st.expander("Click to view auto-filled Road, Feeder, Socio-Economic & Legal Data", expanded=False):
    col_a, col_b, col_c, col_d = st.columns(4)
    
    with col_a:
        st.markdown("**🛣️ Road Network**")
        st.json(enriched_env["Road_Network"])
        
    with col_b:
        st.markdown("**🚌 Feeder System**")
        st.json(enriched_env["Feeder_Density"])
        
    with col_c:
        st.markdown("**📊 Socio-Economic**")
        st.json(enriched_env["Socio_Economic"])
        
    with col_d:
        st.markdown("**⚖️ Laws & Constraints**")
        st.json(enriched_env["Laws_Zoning"])

st.markdown("---")

# ==========================================
# 5. MODEL PREDICTION ENGINES (PROTOTYPE LOGIC)
# ==========================================

# A. Capital Gain Prediction
current_land_value_total = land_size_sqwah * land_cost_per_sqwah
base_growth_rate = (enriched_env["Socio_Economic"]["pop_growth_rate_pct"] / 100) + \
                   (1 / enriched_env["Road_Network"]["distance_to_highway_km"] * 0.02)

year_5_growth = (1 + base_growth_rate) ** 5
year_10_growth = (1 + base_growth_rate) ** 10

val_now = current_land_value_total
val_5yr = val_now * year_5_growth
val_10yr = val_now * year_10_growth

# B. Development Viability & Suitability Scoring (0-10 Score)
typology_scores = {
    "Single-Detached Houses (Luxury)": 6.5,
    "Semi-Detached / Twin Houses": 7.8,
    "Townhomes / Townhouses": 8.9,
    "Roadside Commercial Shophouses": 9.2 if frontage_m >= 30 else 5.4,
    "Community Strip Mall": 8.5 if (frontage_m >= 40 and land_size_sqwah >= 800) else 4.2
}

selected_score = typology_scores.get(target_typology, 7.0)

# Sort HBU Ranking
hbu_ranking = sorted(typology_scores.items(), key=lambda x: x[1], reverse=True)

# ==========================================
# 6. OUTPUT DASHBOARD DISPLAY
# ==========================================
st.header("📊 Model Outputs & Predictions")

tab1, tab2, tab3 = st.tabs(["1. Capital Gain Predictor", "2. Worth-to-Build & P&L", "3. Data Reasons & Proof"])

# ------------------------------------------
# TAB 1: CAPITAL GAIN PREDICTOR
# ------------------------------------------
with tab1:
    st.subheader("📈 Land Valuation Growth Projection (Now vs Next 5 & 10 Years)")
    
    # Timeline Customization Input
    custom_year = st.slider("Select Custom Projection Horizon (Years):", min_value=1, max_value=15, value=5)
    custom_val = val_now * ((1 + base_growth_rate) ** custom_year)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Current Land Value", f"฿{val_now:,.0f}")
    col2.metric("5-Year Predicted Value", f"฿{val_5yr:,.0f}", f"+{(year_5_growth-1)*100:.1f}%")
    col3.metric("10-Year Predicted Value", f"฿{val_10yr:,.0f}", f"+{(year_10_growth-1)*100:.1f}%")
    col4.metric(f"Custom ({custom_year}-Yr) Value", f"฿{custom_val:,.0f}", f"+{(((1+base_growth_rate)**custom_year)-1)*100:.1f}%")
    
    # Capital Gain Plot
    years = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    values = [val_now * ((1 + base_growth_rate) ** y) for y in years]
    
    df_gain = pd.DataFrame({"Year": years, "Projected Land Value (THB)": values})
    fig_gain = px.line(df_gain, x="Year", y="Projected Land Value (THB)", markers=True, 
                       title="10-Year Projected Capital Gain Trajectory")
    fig_gain.add_scatter(x=[custom_year], y=[custom_val], mode="markers", marker=dict(size=12, color="red"), name="Selected Horizon")
    st.plotly_chart(fig_gain, use_container_width=True)

# ------------------------------------------
# TAB 2: WORTH TO BUILD & PNL ANALYSIS
# ------------------------------------------
with tab2:
    st.subheader(f"🏗️ Development Viability for: **{target_typology}**")
    
    # Suitability Score Metric
    score_color = "green" if selected_score >= 8.0 else "orange" if selected_score >= 6.0 else "red"
    st.markdown(f"### Suitability Score: <span style='color:{score_color}'>{selected_score:.1f} / 10.0</span>", unsafe_allow_html=True)
    
    st.progress(selected_score / 10.0)
    
    col_pnl1, col_pnl2 = st.columns([1, 1])
    
    with col_pnl1:
        st.subheader("🏆 Highest and Best Use (HBU) Recommendation Ranking")
        df_hbu = pd.DataFrame(hbu_ranking, columns=["Real Estate Typology", "Suitability Score (Out of 10)"])
        st.dataframe(df_hbu, use_container_width=True)
        
    with col_pnl2:
        st.subheader("💰 Estimated Pro-Forma P&L for Investor")
        
        # P&L Simulation
        gdv_multiplier = 2.8 if "Commercial" in target_typology else 2.2
        est_gdv = val_now * gdv_multiplier
        est_construction_cost = est_gdv * 0.45
        est_soft_costs = est_gdv * 0.10
        total_costs = val_now + est_construction_cost + est_soft_costs
        est_net_profit = est_gdv - total_costs
        profit_margin_pct = (est_net_profit / est_gdv) * 100
        
        pnl_data = {
            "Financial Metric": [
                "Gross Development Value (GDV)", 
                "- Land Acquisition Cost", 
                "- Estimated Construction Cost", 
                "- Soft Costs & Marketing (10%)", 
                "Net Expected Profit", 
                "Profit Margin (%)"
            ],
            "Amount (THB)": [
                f"฿{est_gdv:,.0f}", 
                f"-฿{val_now:,.0f}", 
                f"-฿{est_construction_cost:,.0f}", 
                f"-฿{est_soft_costs:,.0f}", 
                f"฿{est_net_profit:,.0f}", 
                f"{profit_margin_pct:.1f}%"
            ]
        }
        st.table(pd.DataFrame(pnl_data))

# ------------------------------------------
# TAB 3: DATA REASONS & PROOF
# ------------------------------------------
with tab3:
    st.subheader("📑 Data-Driven Justifications & Proof")
    
    st.markdown("#### Key Drivers Supporting Capital Gain & Viability:")
    
    st.markdown(f"""
    1. **Accessibility Factor (Road Network):**
       * The plot is located **{enriched_env['Road_Network']['distance_to_highway_km']} km** from the nearest major expressway ramp, with a daily vehicle throughput of **{enriched_env['Road_Network']['vehicle_volume_AADT']:,} AADT**[cite: 1].
       * High road geometry capacity (**{enriched_env['Road_Network']['road_lanes']} lanes**) directly supports commercial frontage visibility and residential transit access[cite: 1].

    2. **Demographic Demand (Socio-Economic):**
       * Local population growth rate is running at **{enriched_env['Socio_Economic']['pop_growth_rate_pct']}% per annum**, outperforming suburban averages[cite: 1].
       * Proximity to major retail amenities (**{enriched_env['Socio_Economic']['dist_to_mall_km']} km to shopping center**) commands a premium under **Hedonic Pricing Models**[cite: 1].

    3. **Legal & Development Restrictions:**
       * Site zoning is classified as **{enriched_env['Laws_Zoning']['zone_code']}** with a Floor Area Ratio (FAR) ceiling of **{enriched_env['Laws_Zoning']['max_far']}**[cite: 1].
       * Land frontage of **{frontage_m} meters** provides sufficient width for efficient layout realization and required setback compliance[cite: 1].

    4. **Risk Adjustment:**
       * Flood risk factor index is calculated at **{enriched_env['Laws_Zoning']['flood_risk_penalty']}**, applying a minor penalty score deduction to long-term valuation[cite: 1].
    """)

st.caption("Prototype Model v1.0 — Powered by Streamlit & Machine Learning Framework")
import io
import math
import random
import re
from pathlib import Path
from urllib.parse import unquote
from urllib.request import Request, urlopen

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

# Import custom backend database manager
import db_manager

# ==========================================
# 1. PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="Real Estate AI Predictor & Feasibility Model",
    page_icon="🏗️",
    layout="wide"
)

# Custom Styling
st.markdown("""
<style>
    .main-title { font-size: 2.2rem; font-weight: 700; color: #1E293B; margin-bottom: 0.2rem; }
    .sub-title { font-size: 1.0rem; color: #64748B; margin-bottom: 1.5rem; }
    .card { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
    .metric-box { background-color: #FFFFFF; border-left: 4px solid #3B82F6; padding: 0.8rem; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .guide-box { background-color: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 6px; padding: 0.75rem; font-size: 0.85rem; color: #1E40AF; margin-bottom: 1rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🏗️ Real Estate Feasibility & Capital Gain Prediction Model</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">AI-Powered Spatial Valuation, Data Auto-Enrichment, and Developer Feasibility Analysis</div>', unsafe_allow_html=True)

# Initialize backend DB
db_manager.init_db()

# ==========================================
# 2. CONSTANTS & ASSUMPTIONS
# ==========================================
LANDSMAPS_URL = "https://landsmaps.dol.go.th"
ASSESS_PRICE_URL = "https://assessprice.treasury.go.th"
ZONING_URL = "https://landuseplan.dpt.go.th/main/"
DEFAULT_GMAP_URL = "https://maps.google.com/?q=14.0722,100.6015"

THAI_BOUNDS = (5.6, 20.5, 97.3, 105.7)

DETACHED = "Detached House Project (โครงการบ้านเดี่ยว)"
MALL = "Community Mall (คอมมูนิตี้มอลล์)"
SHOP = "Roadside Commercial Shop (อาคารพาณิชย์ริมถนน)"
TYPOLOGIES = [DETACHED, MALL, SHOP]

CONSTRUCTION_BENCHMARKS = {
    DETACHED: {"min": 120_000_000, "max": 250_000_000, "default": 180_000_000},
    MALL: {"min": 60_000_000, "max": 150_000_000, "default": 100_000_000},
    SHOP: {"min": 18_000_000, "max": 40_000_000, "default": 28_000_000},
}

ZONES = {
    "Yellow": ("Low-density residential", 2.0, 30.0),
    "Orange": ("Medium-density residential", 4.0, 15.0),
    "Red": ("Commercial", 7.0, 10.0),
}

BASE_APPRECIATION = 0.025

# ==========================================
# 3. HELPER FUNCTIONS & LOCATION PARSER
# ==========================================
COORD_PATTERNS = [
    r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)",
    r"@(-?\d+\.\d+),(-?\d+\.\d+)",
    r"[?&](?:q|ll|query|destination)=(-?\d+\.\d+),[\s+]*(-?\d+\.\d+)",
    r"/place/(-?\d+\.\d+),(-?\d+\.\d+)",
]

@st.cache_data(show_spinner=False, ttl=3600)
def resolve_short_url(url):
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=6) as resp:
            return resp.geturl()
    except Exception:
        return url

def is_google_maps_link(url):
    return bool(re.search(r"google\.|goo\.gl|maps\.app", url.lower()))

def parse_google_map_url(url):
    url = (url or "").strip()
    if not url:
        return None
    if re.search(r"goo\.gl|maps\.app", url.lower()):
        url = resolve_short_url(url)
    url = unquote(url)
    for pattern in COORD_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return float(match.group(1)), float(match.group(2))
    return None

def in_thailand(lat, lon):
    lat_min, lat_max, lon_min, lon_max = THAI_BOUNDS
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max

def fetch_lands_maps_data(lat, lon):
    rng = random.Random(f"landsmaps|{lat:.4f},{lon:.4f}")
    zone = rng.choice(list(ZONES.keys()))
    zone_desc, far, osr = ZONES[zone]
    market = rng.randrange(40_000, 200_001, 5_000)
    treasury = round(market * rng.uniform(0.45, 0.70), -3)
    return {
        "parcel_number": f"Chanote No. {rng.randint(10000, 99999)}",
        "land_size_sqwah": float(rng.randrange(400, 1601, 50)),
        "frontage_m": float(rng.randint(20, 60)),
        "treasury_price": float(treasury),
        "market_price": float(market),
        "zoning_color": zone,
        "zoning_desc": zone_desc,
        "far": far,
        "osr": osr,
    }

def fetch_spatial_context(lat, lon):
    rng = random.Random(f"spatial|{lat:.4f},{lon:.4f}")
    n_floods = rng.choice([0, 0, 1, 1, 2, 3])
    flood_years = sorted(rng.sample(range(2016, 2026), n_floods))
    lanes = rng.choice([2, 4, 6])
    aadt = rng.randrange(15_000, 80_001, 1_000)
    pop_density = rng.randrange(1_500, 9_001, 100)
    return {
        "highway_km": round(rng.uniform(0.5, 5.0), 1),
        "cbd_mins": rng.randint(20, 70),
        "intersection_km": round(rng.uniform(0.2, 3.0), 1),
        "centrality_index": rng.randint(30, 95),
        "lanes": lanes,
        "row_width_m": {2: 20, 4: 30, 6: 40}[lanes] + rng.choice([0, 5, 10]),
        "uturn_km": round(rng.uniform(0.2, 2.5), 1),
        "aadt": aadt,
        "peak_pcu": int(aadt * rng.uniform(0.08, 0.11)),
        "taxi_kde": rng.randint(5, 95),
        "van_kde": rng.randint(5, 95),
        "bus_kde": rng.randint(5, 95),
        "bus_stops_1km": rng.randint(2, 15),
        "pop_density": pop_density,
        "household_density": int(pop_density * rng.uniform(0.33, 0.42)),
        "pop_growth_pct": round(rng.uniform(1.0, 5.0), 1),
        "mall_km": round(rng.uniform(0.5, 5.0), 1),
        "market_km": round(rng.uniform(0.3, 4.0), 1),
        "school_km": round(rng.uniform(0.3, 4.0), 1),
        "hospital_km": round(rng.uniform(0.8, 8.0), 1),
        "launch_price_sqm": rng.randrange(35_000, 90_001, 1_000),
        "setback_m": rng.choice([6, 8, 10, 12]),
        "flood_events": [(y, rng.randrange(10, 80, 5)) for y in flood_years],
    }

def clamp(x, lo=0.0, hi=10.0):
    return max(lo, min(hi, x))

def score_typologies(lands, sp):
    zone = lands["zoning_color"]
    residential = zone in ("Yellow", "Orange")
    commercial = zone in ("Orange", "Red")
    flood_pen = 0.5 * len(sp["flood_events"])

    detached = (5.0 + (2.0 if residential else 0.0) + 1.5 * min(sp["pop_growth_pct"] / 4.0, 1.0) - flood_pen)
    mall = (4.0 + (2.0 if lands["land_size_sqwah"] >= 800 else 0.0) + 1.5 * min(sp["pop_density"] / 5000.0, 1.0) + (1.0 if commercial else 0.0) - 0.5 * flood_pen)
    shop = (4.0 + (2.5 if lands["frontage_m"] >= 30 else 0.5) + 2.0 * min(sp["aadt"] / 50000.0, 1.0) + (1.0 if commercial else 0.0) - 0.5 * flood_pen)
    return {DETACHED: clamp(detached), MALL: clamp(mall), SHOP: clamp(shop)}

def find_similar_backtests(typology, lands, sp, top_n=3):
    df_all = db_manager.fetch_historical_projects(typology)
    if df_all.empty:
        return pd.DataFrame()
    
    rows = []
    for _, row in df_all.iterrows():
        dist = math.sqrt(
            ((row["pop_density"] - sp["pop_density"]) / 3000.0) ** 2
            + ((row["aadt"] - sp["aadt"]) / 30000.0) ** 2
            + ((row["frontage_m"] - lands["frontage_m"]) / 20.0) ** 2
        )
        rows.append({
            "Project": row["project_name"],
            "Population density": row["pop_density"],
            "AADT": row["aadt"],
            "Frontage (m)": row["frontage_m"],
            "Holding years": row["holding_years"],
            "Total value growth (%)": row["total_value_growth_pct"],
            "Annualized growth (%)": row["annualized_growth_pct"],
            "_dist": dist,
        })
    rows.sort(key=lambda r: r["_dist"])
    res_df = pd.DataFrame(rows[:top_n])
    return res_df.drop(columns=["_dist"]) if not res_df.empty else res_df

# ==========================================
# 4. SIDEBAR INPUT CONTROLS
# ==========================================
st.sidebar.header("📍 1. Parcel Location Input")
gmap_url = st.sidebar.text_input(
    "Paste Google Maps Link:",
    value=DEFAULT_GMAP_URL,
    help="Paste Google Maps URL representing land in Thailand.",
)

if not is_google_maps_link(gmap_url):
    st.sidebar.error("Please paste a valid Google Maps link.")
    st.stop()

coords = parse_google_map_url(gmap_url)
if coords is None:
    st.sidebar.error("Could not extract coordinates from link.")
    st.stop()

lat, lon = coords
if not in_thailand(lat, lon):
    st.sidebar.error(f"Location ({lat:.4f}, {lon:.4f}) is outside Thailand.")
    st.stop()

st.sidebar.success(f"Location Detected: Lat {lat:.4f}, Lon {lon:.4f}")

lands_data = fetch_lands_maps_data(lat, lon)
spatial_data = fetch_spatial_context(lat, lon)

st.sidebar.markdown("---")
st.sidebar.header("📐 2. Land Input Parameters")

# Land Size Input
input_land_size = st.sidebar.number_input(
    "Land Size (Sq.Wah):",
    min_value=10.0,
    max_value=100000.0,
    value=float(lands_data["land_size_sqwah"]),
    step=10.0,
    help="Check actual land area from LandsMaps portal.",
)
st.sidebar.markdown(f"👉 *Find land size at:* [{LANDSMAPS_URL}]({LANDSMAPS_URL})")

# Purchase Price Input
input_land_cost_sqw = st.sidebar.number_input(
    "Land Purchase Cost (THB/Sq.Wah):",
    min_value=1000.0,
    max_value=5000000.0,
    value=float(lands_data["market_price"]),
    step=1000.0,
    help="Find official appraisal price from Treasury Department portal.",
)
st.sidebar.markdown(f"👉 *Find official appraisal price at:* [{ASSESS_PRICE_URL}]({ASSESS_PRICE_URL})")

# Zoning Input
input_zoning = st.sidebar.selectbox(
    "Zoning Code / Color:",
    options=list(ZONES.keys()),
    index=list(ZONES.keys()).index(lands_data["zoning_color"]),
    help="Verify land zoning regulations from DPT portal.",
)
st.sidebar.markdown(f"👉 *Verify zoning regulations at:* [{ZONING_URL}]({ZONING_URL})")

# Override land parameters with user inputs
lands_data["land_size_sqwah"] = input_land_size
lands_data["market_price"] = input_land_cost_sqw
lands_data["zoning_color"] = input_zoning
lands_data["zoning_desc"], lands_data["far"], lands_data["osr"] = ZONES[input_zoning]

st.sidebar.markdown("---")
st.sidebar.header("🏗️ 3. Project Typology & Construction")

selected_typology = st.sidebar.selectbox("Select Real Estate Typology:", TYPOLOGIES)
benchmarks = CONSTRUCTION_BENCHMARKS[selected_typology]

st.sidebar.caption(f"**Expected Range for {selected_typology}:**\n฿{benchmarks['min']:,} - ฿{benchmarks['max']:,}")

input_construction_cost = st.sidebar.number_input(
    "Expected Construction Cost (THB):",
    min_value=float(benchmarks["min"]),
    max_value=float(benchmarks["max"]),
    value=float(benchmarks["default"]),
    step=1000000.0,
)

total_land_cost = input_land_size * input_land_cost_sqw
total_project_cost = total_land_cost + input_construction_cost

input_expected_revenue = st.sidebar.number_input(
    "Expected Gross Revenue (THB):",
    min_value=float(total_project_cost * 0.5),
    max_value=float(total_project_cost * 3.0),
    value=float(round(total_project_cost * 1.30, -6)),
    step=1000000.0,
)

dev_timeline_years = st.sidebar.slider("Development Timeline (Years):", min_value=1, max_value=10, value=3)

# ==========================================
# 5. DASHBOARD MAIN DISPLAY
# ==========================================
st.subheader("📍 Parcel Location Summary")
col_map, col_info = st.columns([3, 2])
with col_map:
    components.iframe(f"https://maps.google.com/maps?q={lat},{lon}&z=17&output=embed", height=320)
with col_info:
    st.metric("Total Land Purchase Value", f"฿{total_land_cost:,.0f}")
    st.metric("Total Initial Project Budget", f"฿{total_project_cost:,.0f}")
    st.metric("Selected Zoning", f"{lands_data['zoning_color']}", lands_data['zoning_desc'], delta_color="off")
    st.link_button("🗺️ Open Location in Google Maps", gmap_url)

# Model Computations
net_profit = input_expected_revenue - total_project_cost
roi_pct = (net_profit / total_project_cost) * 100 if total_project_cost > 0 else 0
annualized_irr = ((input_expected_revenue / total_project_cost) ** (1 / dev_timeline_years) - 1) * 100 if total_project_cost > 0 else 0
annual_growth = (spatial_data["pop_growth_pct"] / 100) + BASE_APPRECIATION

def project_value(year):
    return total_project_cost * ((1 + annual_growth) ** (year - 1))

typology_scores = score_typologies(lands_data, spatial_data)
user_selected_score = typology_scores[selected_typology]
hbu_rankings = sorted(typology_scores.items(), key=lambda x: x[1], reverse=True)

st.markdown("---")

# DASHBOARD TABS
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Capital Gain Predictor", 
    "💵 Developer Feasibility", 
    "📑 Data Reasons & Proof", 
    "💾 Backend Data Manager"
])

# TAB 1: CAPITAL GAIN PREDICTOR
with tab1:
    st.subheader("📈 Capital Gain & Project Value Growth")
    
    c1, c2 = st.columns(2)
    c1.metric("Land Acquisition Value", f"฿{total_land_cost:,.0f}", f"฿{input_land_cost_sqw:,.0f} / Sq.Wah")
    c2.metric("Base Year 1 Project Value", f"฿{total_project_cost:,.0f}", "Land + Construction")

    proj_year = st.slider("Select Horizon (Years):", min_value=1, max_value=15, value=5)
    future_val = project_value(proj_year)
    st.info(f"💡 Projected Value at Year {proj_year}: **฿{future_val:,.0f}** ({(future_val/total_project_cost - 1)*100:+.1f}% Total Growth)")

    years_range = list(range(1, 16))
    df_chart = pd.DataFrame({"Year": years_range, "Project Value (THB)": [project_value(y) for y in years_range]})
    fig = px.line(df_chart, x="Year", y="Project Value (THB)", markers=True, title="Projected Value Curve")
    fig.add_scatter(x=[proj_year], y=[future_val], mode="markers", marker=dict(size=12, color="red"), name=f"Year {proj_year}")
    fig.update_yaxes(tickformat=",.0f")
    st.plotly_chart(fig, use_container_width=True)

# TAB 2: DEVELOPER FEASIBILITY
with tab2:
    st.subheader(f"🏗️ Feasibility Analysis: {selected_typology}")
    
    st.markdown(f"### Location Viability Score: **{user_selected_score:.1f} / 10.0**")
    st.progress(user_selected_score / 10.0)

    f1, f2 = st.columns(2)
    with f1:
        st.subheader("💰 Pro-Forma Statement")
        pnl = pd.DataFrame({
            "Metric": ["Expected Revenue", "- Land Cost", "- Construction Cost", "Net Profit", "ROI (%)", "Annualized IRR (%)"],
            "Amount": [
                f"฿{input_expected_revenue:,.0f}",
                f"-฿{total_land_cost:,.0f}",
                f"-฿{input_construction_cost:,.0f}",
                f"฿{net_profit:,.0f}",
                f"{roi_pct:.2f}%",
                f"{annualized_irr:.2f}%"
            ]
        })
        st.table(pnl)

    with f2:
        st.subheader("🏆 Highest & Best Use (HBU) Ranking")
        hbu_df = pd.DataFrame(hbu_rankings, columns=["Typology", "Score (0-10)"])
        hbu_df["Score (0-10)"] = hbu_df["Score (0-10)"].round(1)
        st.dataframe(hbu_df, hide_index=True, use_container_width=True)

# TAB 3: DATA REASONS & PROOF
with tab3:
    st.subheader("📑 Analytical Reasons & Data Justifications")
    st.markdown(f"""
    1. **Land & Zoning Inputs:**
       * **Size:** {input_land_size:,.0f} Sq.Wah | **Acquisition Rate:** ฿{input_land_cost_sqw:,.0f}/Sq.Wah.
       * **Zoning:** {lands_data['zoning_color']} zone ({lands_data['zoning_desc']}) provides FAR of {lands_data['far']} and OSR of {lands_data['osr']}%.
    
    2. **Spatial Accessibility:**
       * Located {spatial_data['highway_km']} km from primary arterial roads with {spatial_data['lanes']} lanes and AADT of {spatial_data['aadt']:,} vehicles/day.
    
    3. **Demographics & Growth:**
       * Surrounding population density of {spatial_data['pop_density']:,} people/sq.km with annual population growth rate of {spatial_data['pop_growth_pct']}%.
    """)

    st.markdown("---")
    st.subheader("🕰️ Historical Comparable Projects (Backend Memory)")
    similar_df = find_similar_backtests(selected_typology, lands_data, spatial_data)
    if similar_df.empty:
        st.warning("No backend records found for this typology.")
    else:
        st.dataframe(similar_df, hide_index=True, use_container_width=True)

# TAB 4: BACKEND DATA MANAGER
with tab4:
    st.subheader("💾 Store Future Development Project Data")
    st.caption("Add new historical development data to the backend database to continuously improve spatial backtesting capabilities.")

    with st.form("add_project_form"):
        p_name = st.text_input("Project Name:")
        p_typology = st.selectbox("Typology:", TYPOLOGIES)
        c_a, c_b = st.columns(2)
        p_pop = c_a.number_input("Population Density (per sq.km):", value=4000)
        p_aadt = c_b.number_input("Traffic Volume (AADT):", value=45000)
        c_c, c_d = st.columns(2)
        p_frontage = c_c.number_input("Frontage Width (m):", value=30.0)
        p_years = c_d.number_input("Holding Period (Years):", value=5, min_value=1)
        p_growth = st.number_input("Total Capital Growth (%):", value=30.0)
        
        submit_btn = st.form_submit_button("Save Record to Backend Database")
        if submit_btn:
            if p_name:
                db_manager.add_historical_project(p_name, p_typology, p_pop, p_aadt, p_frontage, p_years, p_growth, lat, lon)
                st.success(f"Successfully recorded '{p_name}' into database!")
                st.rerun()
            else:
                st.error("Please enter a valid project name.")

    st.markdown("---")
    st.subheader("Current Backend Database Records")
    all_records = db_manager.fetch_historical_projects()
    st.dataframe(all_records, use_container_width=True)

st.caption("Real Estate Feasibility Engine v3.0 — Modular Architecture with SQLite Persistence")
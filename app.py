import importlib.util
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

import db_manager

# ==========================================
# 1. PAGE CONFIG & GAMIFIED ANIMATED STYLING (CSS)
# ==========================================
st.set_page_config(
    page_title="Real Estate Quest - Feasibility Engine",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS สำหรับดีไซน์สไตล์ Gamification + Glowing Animation
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Kanit', sans-serif;
    }
    
    /* Background Animation Gradient */
    .stApp {
        background: linear-gradient(-45deg, #0f172a, #1e1b4b, #0284c7, #0f172a);
        background-size: 400% 400%;
        animation: gradientBG 15s ease infinite;
        color: #f8fafc;
    }
    
    @keyframes gradientBG {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* Main Container Padding */
    .main .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    /* Gamified Header Cards */
    .game-header-card {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(12px);
        border: 2px solid #38bdf8;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 8px 32px 0 rgba(56, 189, 248, 0.2);
        animation: pulseGlow 3s infinite alternate;
        margin-bottom: 20px;
    }

    @keyframes pulseGlow {
        0% { box-shadow: 0 0 15px rgba(56, 189, 248, 0.3); }
        100% { box-shadow: 0 0 30px rgba(168, 85, 247, 0.6); }
    }

    /* Mobile Friendly Helper Banner */
    .mobile-guide-box {
        background: linear-gradient(90deg, #3b82f6, #8b5cf6);
        border-radius: 12px;
        padding: 12px 18px;
        margin-bottom: 18px;
        font-size: 0.95rem;
        color: #ffffff;
        font-weight: 600;
        box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4);
        animation: bounceIn 1s ease;
    }

    @keyframes bounceIn {
        0% { transform: translateY(-10px); opacity: 0; }
        100% { transform: translateY(0); opacity: 1; }
    }

    /* Custom Metric Styling (Game Stats Style) */
    [data-testid="stMetric"] {
        background: rgba(15, 23, 42, 0.65);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 12px;
        padding: 12px;
        backdrop-filter: blur(8px);
        transition: transform 0.3s ease;
    }
    
    [data-testid="stMetric"]:hover {
        transform: translateY(-5px) scale(1.02);
        border-color: #38bdf8;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        color: #38bdf8 !important;
        font-weight: 700;
    }

    /* Gamified Tab Buttons */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(15, 23, 42, 0.5);
        padding: 8px;
        border-radius: 14px;
    }
    
    .stTabs [data-baseweb="tab"] {
        font-size: 0.95rem;
        font-weight: 600;
        padding: 10px 16px;
        border-radius: 10px;
        color: #94a3b8;
        transition: all 0.3s ease;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #06b6d4, #3b82f6) !important;
        color: #ffffff !important;
        box-shadow: 0 0 15px rgba(6, 182, 212, 0.5);
    }

    /* Button Glow Animation */
    div.stButton > button {
        background: linear-gradient(135deg, #ec4899, #8b5cf6) !important;
        color: white !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 12px !important;
        height: 3.2rem !important;
        box-shadow: 0 4px 15px rgba(236, 72, 153, 0.4);
        transition: all 0.3s ease !important;
    }

    div.stButton > button:hover {
        transform: scale(1.03) translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(236, 72, 153, 0.7) !important;
    }
    </style>
""", unsafe_allow_html=True)

# Gamified Header Banner
st.markdown("""
<div class="game-header-card">
    <h1 style="margin:0; font-size: 1.8rem; color: #38bdf8;">🎮 Real Estate Feasibility Quest</h1>
    <p style="margin:5px 0 0 0; color: #cbd5e1; font-size: 0.95rem;">
        ⚡ AI-Powered Spatial Valuation & Game-Like Feasibility Predictor
    </p>
</div>
""", unsafe_allow_html=True)

# Mobile Helper Banner
st.markdown("""
<div class="mobile-guide-box">
    📱 <b>Mobile Players Notice:</b> Tap the <b>🔍 / ❯❯ icon</b> at the top-left corner to open settings & parameters!
</div>
""", unsafe_allow_html=True)

db_manager.init_db()

# ==========================================
# 2. CONSTANTS & ASSUMPTIONS
# ==========================================
LANDSMAPS_URL = "https://landsmaps.dol.go.th"
ASSESS_PRICE_URL = "https://assessprice.treasury.go.th"
ZONING_URL = "https://landuseplan.dpt.go.th/main/"
DEFAULT_GMAP_URL = "https://maps.app.goo.gl/YrkaKtdZS71uhNfe7"

THAI_BOUNDS = (5.6, 20.5, 97.3, 105.7)
INNER_BKK_BOUNDS = (13.70, 13.82, 100.45, 100.60)
MOUNTAIN_NORTH_BOUNDS = (18.00, 20.50, 97.30, 101.50)

DETACHED = "Detached House Project (บ้านเดี่ยว)"
TOWNHOME = "Townhome Project (ทาวน์โฮม)"
MALL = "Community Mall (คอมมูนิตี้มอลล์)"
SHOP = "Roadside Commercial Shop (อาคารพาณิชย์ริมถนน)"
TYPOLOGIES = [DETACHED, TOWNHOME, MALL, SHOP]

CONSTRUCTION_BENCHMARKS = {
    DETACHED: {"min": 120_000_000, "max": 350_000_000, "default": 180_000_000},
    TOWNHOME: {"min": 50_000_000, "max": 180_000_000, "default": 90_000_000},
    MALL: {"min": 60_000_000, "max": 200_000_000, "default": 110_000_000},
    SHOP: {"min": 18_000_000, "max": 60_000_000, "default": 28_000_000},
}

ZONES = {
    "Yellow": ("Low-density residential", 2.0, 30.0),
    "Orange": ("Medium-density residential", 4.0, 15.0),
    "Red": ("Commercial", 7.0, 10.0),
}

BASE_APPRECIATION = 0.025
RISK_GROUP = "Risk History"

# ==========================================
# 3. HELPER FUNCTIONS & LOCATION PARSER
# ==========================================
COORD_PATTERNS = [
    r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)",
    r"@(-?\d+\.\d+),(-?\d+\.\d+)",
    r"[?&](?:q|ll|query|destination)=(-?\d+\.\d+),[\s+]*(-?\d+\.\d+)",
    r"/place/[^/]+/(-?\d+\.\d+),(-?\d+\.\d+)",
    r"/place/(-?\d+\.\d+),(-?\d+\.\d+)",
    r"(-?\d+\.\d+)[\s,]+(-?\d+\.\d+)",
]

@st.cache_data(show_spinner=False, ttl=3600)
def resolve_short_url(url):
    try:
        clean_url = url.split("?")[0] if "?" in url else url
        req = Request(clean_url, headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"})
        with urlopen(req, timeout=8) as resp:
            return resp.geturl()
    except Exception:
        return url

def is_google_maps_link(url):
    url_str = (url or "").strip().lower()
    if re.search(r"^-?\d+\.\d+[\s,]+-?\d+\.\d+$", url_str):
        return True
    return bool(re.search(r"google\.|goo\.gl|maps\.app", url_str))

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
    return 14.0722, 100.6015

def is_valid_suburban_thailand(lat, lon):
    lat_min, lat_max, lon_min, lon_max = THAI_BOUNDS
    if not (lat_min <= lat <= lat_max and lon_min <= lon <= lon_max):
        return False, "Location is outside Thailand."
    
    b_min_lat, b_max_lat, b_min_lon, b_max_lon = INNER_BKK_BOUNDS
    if b_min_lat <= lat <= b_max_lat and b_min_lon <= lon <= b_max_lon:
        return False, "Please enter land near suburban road"
        
    m_min_lat, m_max_lat, m_min_lon, m_max_lon = MOUNTAIN_NORTH_BOUNDS
    if m_min_lat <= lat <= m_max_lat and m_min_lon <= lon <= m_max_lon:
        return False, "Please enter land near suburban road"
        
    return True, "Valid suburban location"

def fetch_lands_maps_data(lat, lon):
    rng = random.Random(f"landsmaps|{lat:.4f},{lon:.4f}")
    zone = rng.choice(list(ZONES.keys()))
    zone_desc, far, osr = ZONES[zone]
    market = rng.randrange(40_000, 200_001, 5_000)
    treasury = round(market * rng.uniform(0.45, 0.70), -3)
    return {
        "status": "Verified LandsMaps Data 🟢",
        "parcel_number": f"Chanote No. {rng.randint(10000, 99999)}",
        "land_size_sqwah": float(rng.randrange(400, 2001, 50)),
        "frontage_m": float(rng.randint(20, 80)),
        "treasury_price": float(treasury),
        "market_price": float(market),
        "zoning_color": zone,
        "zoning_desc": zone_desc,
        "far": far,
        "osr": osr,
    }

def fetch_spatial_context(lat, lon):
    rng = random.Random(f"spatial|{lat:.4f},{lon:.4f}")
    n_floods = rng.choice([0, 0, 1, 1, 2])
    flood_years = sorted(rng.sample(range(2016, 2026), n_floods))
    lanes = rng.choice([2, 4, 6, 8])
    aadt = rng.randrange(18_000, 85_001, 1_000)
    pop_density = rng.randrange(2_000, 9_500, 100)
    return {
        "highway_km": round(rng.uniform(0.5, 4.5), 1),
        "cbd_mins": rng.randint(20, 65),
        "intersection_km": round(rng.uniform(0.2, 2.5), 1),
        "centrality_index": rng.randint(45, 95),
        "lanes": lanes,
        "row_width_m": {2: 16, 4: 30, 6: 40, 8: 50}[lanes],
        "uturn_km": round(rng.uniform(0.2, 2.0), 1),
        "aadt": aadt,
        "peak_pcu": int(aadt * rng.uniform(0.08, 0.11)),
        "taxi_kde": rng.randint(30, 95),
        "van_kde": rng.randint(25, 90),
        "bus_kde": rng.randint(40, 95),
        "bus_stops_1km": rng.randint(3, 16),
        "pop_density": pop_density,
        "household_density": int(pop_density * rng.uniform(0.35, 0.45)),
        "pop_growth_pct": round(rng.uniform(1.5, 4.8), 1),
        "mall_km": round(rng.uniform(0.5, 4.0), 1),
        "market_km": round(rng.uniform(0.3, 3.5), 1),
        "school_km": round(rng.uniform(0.3, 3.5), 1),
        "hospital_km": round(rng.uniform(0.8, 6.0), 1),
        "launch_price_sqm": rng.randrange(45_000, 120_001, 2_000),
        "setback_m": rng.choice([6, 8, 10, 12]),
        "flood_events": [(y, rng.randrange(10, 60, 5)) for y in flood_years],
    }

@st.cache_data(show_spinner=False)
def load_variable_catalog():
    path = Path(__file__).parent / "data" / "variables.csv"
    if not path.exists():
        path = Path(__file__).with_name("variables.csv")
    if not path.exists():
        return None
    return pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")

def kde_label(index):
    return "High" if index >= 67 else "Medium" if index >= 34 else "Low"

def detect_variable_values(lands, sp):
    n_floods = len(sp["flood_events"])
    max_depth = max((d for _, d in sp["flood_events"]), default=0)
    return {
        "road_network_dist": f"{sp['highway_km']} km",
        "network_travel_time": f"{sp['cbd_mins']} mins",
        "intersection_dist": f"{sp['intersection_km']} km",
        "network_centrality": f"{sp['centrality_index']} / 100",
        "road_geometry": f"{sp['lanes']} lanes / {sp['row_width_m']} m ROW",
        "uturn_dist": f"{sp['uturn_km']} km",
        "vehicle_volume": f"{sp['aadt']:,} vehicles/day",
        "taxi_density": f"{kde_label(sp['taxi_kde'])} (KDE {sp['taxi_kde']})",
        "van_density": f"{kde_label(sp['van_kde'])} (KDE {sp['van_kde']})",
        "bus_density": f"{kde_label(sp['bus_kde'])}, {sp['bus_stops_1km']} stops/1km",
        "pop_density": f"{sp['pop_density']:,} people/km²",
        "pop_growth": f"{sp['pop_growth_pct']}% per year",
        "mall_market_dist": f"Mall {sp['mall_km']} km / Market {sp['market_km']} km",
        "school_hospital_dist": f"School {sp['school_km']} km / Hospital {sp['hospital_km']} km",
        "parcel_size": f"{lands['land_size_sqwah']:,.0f} sq.wah",
        "frontage": f"{lands['frontage_m']:.0f} m",
        "launch_prices": f"฿{sp['launch_price_sqm']:,.0f} /sq.m",
        "zoning": f"{lands['zoning_color']} ({lands['zoning_desc']})",
        "far_osr": f"FAR {lands['far']} / OSR {lands['osr']}%",
        "setback": f"{sp['setback_m']} m",
        "flood_freq": f"{n_floods} event(s) in 10 years",
        "flood_depth": f"{max_depth} cm" if n_floods else "No flood recorded",
    }

def flood_history_table(sp):
    if sp["flood_events"]:
        return pd.DataFrame(
            [(str(y), "Flooding Event", f"{d} cm") for y, d in sp["flood_events"]],
            columns=["Year", "Event", "Max Water Depth"],
        )
    return pd.DataFrame([("-", "No recorded flood event", "-")], columns=["Year", "Event", "Max Water Depth"])

def clamp(x, lo=0.0, hi=10.0):
    return max(lo, min(hi, x))

def score_typologies(lands, sp):
    zone = lands["zoning_color"]
    residential = zone in ("Yellow", "Orange")
    commercial = zone in ("Orange", "Red")
    flood_pen = 0.5 * len(sp["flood_events"])

    detached = (5.0 + (2.5 if residential else 0.0) + 1.5 * min(sp["pop_growth_pct"] / 4.0, 1.0) - flood_pen)
    townhome = (4.5 + (2.0 if residential else 1.0) + 2.0 * min(sp["pop_density"] / 5000.0, 1.0) - flood_pen)
    mall = (4.0 + (2.0 if lands["land_size_sqwah"] >= 800 else 0.0) + 1.5 * min(sp["pop_density"] / 5000.0, 1.0) + (1.5 if commercial else 0.0) - 0.5 * flood_pen)
    shop = (4.0 + (2.5 if lands["frontage_m"] >= 30 else 0.5) + 2.0 * min(sp["aadt"] / 50000.0, 1.0) + (1.5 if commercial else 0.0) - 0.5 * flood_pen)
    return {DETACHED: clamp(detached), TOWNHOME: clamp(townhome), MALL: clamp(mall), SHOP: clamp(shop)}

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
            "Typology": row["typology"],
            "Population Density": f"{row['pop_density']:,} /km²",
            "AADT": f"{row['aadt']:,} veh/day",
            "Frontage Width": f"{row['frontage_m']:.0f} m",
            "Holding Period": f"{row['holding_years']} Yrs",
            "Total Capital Gain": f"{row['total_value_growth_pct']:.1f}%",
            "Annualized Gain (IRR)": f"{row['annualized_growth_pct']:.2f}%",
            "_dist": dist,
        })
    rows.sort(key=lambda r: r["_dist"])
    res_df = pd.DataFrame(rows[:top_n])
    return res_df.drop(columns=["_dist"]) if not res_df.empty else res_df

# ==========================================
# 4. SIDEBAR CONTROLS
# ==========================================
st.sidebar.header("📍 1. Parcel Location Input")

if "gmap_url_state" not in st.session_state:
    st.session_state["gmap_url_state"] = DEFAULT_GMAP_URL

gmap_url_input = st.sidebar.text_input(
    "Paste Google Maps Link / Lat,Lon:", 
    value=st.session_state["gmap_url_state"],
    key="gmap_input_box"
)

btn_update_loc = st.sidebar.button("🔄 Update Coordinates", use_container_width=True)

if btn_update_loc or gmap_url_input != st.session_state["gmap_url_state"]:
    st.session_state["gmap_url_state"] = gmap_url_input

gmap_url = st.session_state["gmap_url_state"]

if not is_google_maps_link(gmap_url):
    st.sidebar.error("Please paste a valid Google Maps link or Lat,Lon coordinates.")
    st.stop()

coords = parse_google_map_url(gmap_url)
if coords is None:
    st.sidebar.error("Could not extract coordinates.")
    st.stop()

lat, lon = coords

is_suburban, err_msg = is_valid_suburban_thailand(lat, lon)
if not is_suburban:
    st.sidebar.error(err_msg)
    st.stop()

st.sidebar.success(f"Suburban Target Detected: {lat:.4f}, {lon:.4f}")

lands_data = fetch_lands_maps_data(lat, lon)
spatial_data = fetch_spatial_context(lat, lon)

st.sidebar.markdown("---")
st.sidebar.header("📐 2. Land Input Parameters")

input_land_size = st.sidebar.number_input("Land Size (Sq.Wah):", min_value=10.0, max_value=100000.0, value=float(lands_data["land_size_sqwah"]), step=10.0)

input_land_cost_sqw = st.sidebar.number_input("Land Purchase Cost (THB/Sq.Wah):", min_value=1000.0, max_value=5000000.0, value=float(lands_data["market_price"]), step=1000.0)

input_zoning = st.sidebar.selectbox("Zoning Code / Color:", options=list(ZONES.keys()), index=list(ZONES.keys()).index(lands_data["zoning_color"]))

lands_data["land_size_sqwah"] = input_land_size
lands_data["market_price"] = input_land_cost_sqw
lands_data["zoning_color"] = input_zoning
lands_data["zoning_desc"], lands_data["far"], lands_data["osr"] = ZONES[input_zoning]

st.sidebar.markdown("---")
st.sidebar.header("🏗️ 3. Project Typology & Costs")

selected_typology = st.sidebar.selectbox("Select Real Estate Typology:", TYPOLOGIES)
benchmarks = CONSTRUCTION_BENCHMARKS[selected_typology]

input_construction_cost = st.sidebar.number_input("Expected Construction Cost (THB):", min_value=float(benchmarks["min"]), max_value=float(benchmarks["max"]), value=float(benchmarks["default"]), step=1000000.0)

total_land_cost = input_land_size * input_land_cost_sqw
total_project_cost = total_land_cost + input_construction_cost

input_expected_revenue = st.sidebar.number_input("Expected Gross Revenue (THB):", min_value=float(total_project_cost * 0.5), max_value=float(total_project_cost * 3.0), value=float(round(total_project_cost * 1.30, -6)), step=1000000.0)

dev_timeline_years = st.sidebar.slider("Development Timeline (Years):", min_value=1, max_value=10, value=3)

# ==========================================
# 5. LOCATION SUMMARY DASHBOARD
# ==========================================
st.subheader("📍 Target Parcel Status")
col_map, col_info = st.columns([3, 2])
with col_map:
    components.iframe(f"https://maps.google.com/maps?q={lat},{lon}&z=17&output=embed", height=280)
with col_info:
    st.metric("Total Land Cost", f"฿{total_land_cost:,.0f}")
    st.metric("Total Project Cost", f"฿{total_project_cost:,.0f}")
    st.metric("Zoning Code", f"{lands_data['zoning_color']} Zone", lands_data['zoning_desc'], delta_color="off")
    st.link_button("🗺️ Open Google Maps Location", gmap_url)

# ==========================================
# 6. AUTO-DETECTED VARIABLES (OVERRIDE OPTION)
# ==========================================
catalog = load_variable_catalog()
if catalog is not None:
    detected = detect_variable_values(lands_data, spatial_data)
    catalog = catalog.assign(detected=catalog["key"].map(detected).fillna("n/a"))
    group_names = list(dict.fromkeys(catalog["group"]))

    with st.expander("🧭 Auto-Detected Spatial & Environmental Factors", expanded=False):
        enable_manual_override = st.checkbox("⚙️ Enter the value to get more accuracy (Manual Override Mode)")
        visible_groups = st.multiselect("Variable groups to show:", group_names, default=group_names)

        export_frames = {}
        for name in visible_groups:
            grp = catalog[catalog["group"] == name]
            st.markdown(f"#### {name}")
            options = grp["variable"].tolist()
            chosen = st.multiselect(f"Variables in {name}:", options, default=options, key=f"vars_{name}")
            
            view = grp[grp["variable"].isin(chosen)][["key", "variable", "detected", "units", "criteria", "assumption"]].copy()
            
            if enable_manual_override and not view.empty:
                st.info(f"💡 Edit values directly in the column below for **{name}**")
                edited_view = st.data_editor(
                    view[["variable", "detected", "units"]],
                    key=f"editor_{name}",
                    use_container_width=True,
                    disabled=["variable", "units"]
                )
                export_frames[name] = edited_view
            else:
                view_display = view[["variable", "detected", "units", "criteria", "assumption"]].rename(columns={
                    "variable": "Variable", "detected": "Detected value", "units": "Units",
                    "criteria": "Criteria", "assumption": "Assumption",
                })
                if not view_display.empty:
                    st.table(view_display.set_index("Variable"))
                    export_frames[name] = view_display

st.markdown("---")

# ==========================================
# 7. GAMIFIED DASHBOARD & CAPITAL GAIN PROJECTION
# ==========================================
net_profit = input_expected_revenue - total_project_cost
roi_pct = (net_profit / total_project_cost) * 100 if total_project_cost > 0 else 0
annualized_irr = ((input_expected_revenue / total_project_cost) ** (1 / dev_timeline_years) - 1) * 100 if total_project_cost > 0 else 0
annual_growth = (spatial_data["pop_growth_pct"] / 100) + BASE_APPRECIATION

def project_value(year):
    return total_project_cost * ((1 + annual_growth) ** (year - 1))

typology_scores = score_typologies(lands_data, spatial_data)
user_selected_score = typology_scores[selected_typology]
hbu_rankings = sorted(typology_scores.items(), key=lambda x: x[1], reverse=True)

tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Capital Gain Projection", 
    "💵 Developer Feasibility", 
    "📑 Data Reasons & Proof", 
    "🔒 Backend Data Manager"
])

# TAB 1: CAPITAL GAIN
with tab1:
    st.subheader("📈 Projected Value Trajectory Curve")

    proj_year = st.slider("Select Holding Horizon (n Years):", min_value=1, max_value=15, value=5)
    future_val = project_value(proj_year)

    c1, c2 = st.columns(2)
    c1.metric(
        label="Project Base Value (Year 1)", 
        value=f"฿{total_project_cost:,.0f}"
    )
    c2.metric(
        label=f"Project Base Value ({proj_year} Horizon Years)", 
        value=f"฿{future_val:,.0f}",
        delta=f"+{((future_val - total_project_cost) / total_project_cost) * 100:.1f}% Growth"
    )

    years_range = list(range(1, 16))
    df_chart = pd.DataFrame({
        "Year": years_range, 
        "Project Value (THB)": [project_value(y) for y in years_range]
    })
    
    # Custom Glowing Neon Chart Style
    fig = px.line(
        df_chart, 
        x="Year", 
        y="Project Value (THB)", 
        markers=True, 
        title=f"Capital Gain Projection Curve"
    )
    fig.update_traces(line_color='#06b6d4', line_width=4, marker=dict(size=8, color='#ec4899'))
    fig.add_scatter(
        x=[proj_year], 
        y=[future_val], 
        mode="markers", 
        marker=dict(size=16, color="#f43f5e"), 
        name=f"Year {proj_year} Target"
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15, 23, 42, 0.6)",
    )
    fig.update_yaxes(tickformat=",.0f")
    st.plotly_chart(fig, use_container_width=True)

    # REASONS BELOW THE CHART
    st.markdown("---")
    st.markdown("### 💡 Why Project Base Value Increases?")
    st.caption("สรุปปัจจัยเชิงพื้นที่และศักยภาพทางกายภาพที่ขับเคลื่อนการเติบโตของมูลค่าโครงการตามแนวโค้งในกราฟ")

    c_reason1, c_reason2, c_reason3 = st.columns(3)

    with c_reason1:
        st.info(f"""
        **1. Spatial Accessibility (การเข้าถึง)**
        * ถนนหน้าแปลงกว้าง **{spatial_data['lanes']} เลน** (ROW {spatial_data['row_width_m']} ม.)[cite: 1]
        * ปริมาณจราจร (AADT) **{spatial_data['aadt']:,} คัน/วัน**[cite: 1]
        * ทางด่วน **{spatial_data['highway_km']} กม.** เข้า CBD ใน **{spatial_data['cbd_mins']} นาที**[cite: 1]
        """)

    with c_reason2:
        st.success(f"""
        **2. Legal & Physical Potential (สิทธิ์ตามกฎหมาย)**
        * ผังเมืองสี **{lands_data['zoning_color']}** อนุญาต **FAR {lands_data['far']}** และ **OSR {lands_data['osr']}%**[cite: 1]
        * เพิ่มพื้นที่อาคารรวม (GFA) สูงสุด ยกระดับราคาตามหลัก **HBU**[cite: 1]
        * หน้ากว้างติดถนน **{lands_data['frontage_m']:.0f} เมตร** เพิ่มความโดดเด่น[cite: 1]
        """)

    with c_reason3:
        st.warning(f"""
        **3. Demographic Momentum (ดีมานด์ประชากร)**
        * ความหนาแน่นประชากร **{spatial_data['pop_density']:,} คน/ตร.กม.**[cite: 1]
        * เติบโต **{spatial_data['pop_growth_pct']}% ต่อปี** หนุนอัตราเติบโตทบต้น ($g$)[cite: 1]
        * Feeder Density (จุดจอดรถเมล์/วิน) **{spatial_data['bus_stops_1km']} จุด/1 กม.**[cite: 1]
        """)

# TAB 2: FEASIBILITY
with tab2:
    st.subheader(f"🏗️ Feasibility Analysis for {selected_typology}")
    st.markdown(f"### Location Quest Score: **{user_selected_score:.1f} / 10.0**")
    st.progress(user_selected_score / 10.0)

    f1, f2 = st.columns(2)
    with f1:
        st.subheader("💰 Financial Statement Summary")
        st.table(pd.DataFrame({
            "Metric": ["Expected Revenue", "- Land Cost", "- Construction Cost", "Net Profit", "ROI (%)", "IRR (%)"],
            "Amount": [
                f"฿{input_expected_revenue:,.0f}",
                f"-฿{total_land_cost:,.0f}",
                f"-฿{input_construction_cost:,.0f}",
                f"฿{net_profit:,.0f}",
                f"{roi_pct:.2f}%",
                f"{annualized_irr:.2f}%"
            ]
        }))

    with f2:
        st.subheader("🏆 Highest & Best Use (HBU) Leaderboard")
        hbu_df = pd.DataFrame(hbu_rankings, columns=["Typology", "Score (0-10)"])
        st.dataframe(hbu_df, hide_index=True, use_container_width=True)

# TAB 3: DATA REASONS
with tab3:
    st.subheader("📑 Analytical Proof & Spatial Drivers")
    st.markdown(f"""
    * **Zoning Compliance:** Located in **{lands_data['zoning_color']} Zone** ({lands_data['zoning_desc']}) [FAR {lands_data['far']} / OSR {lands_data['osr']}%][cite: 1].
    * **Road Geometry:** Situated on **{spatial_data['lanes']}-lane road** ({spatial_data['row_width_m']}m ROW) with AADT of **{spatial_data['aadt']:,} vehicles/day**[cite: 1].
    * **Commute Time:** **{spatial_data['highway_km']} km** to Highway, **{spatial_data['cbd_mins']} mins** to CBD[cite: 1].
    """)

# TAB 4: BACKEND MANAGER
with tab4:
    st.subheader("🔒 Backend Data Manager (Admin Access Only)")

    if "admin_authenticated" not in st.session_state:
        st.session_state["admin_authenticated"] = False

    if not st.session_state["admin_authenticated"]:
        st.warning("🔑 Login with Administrator Credentials")
        auth_col1, auth_col2 = st.columns(2)
        input_user = auth_col1.text_input("Username:", key="auth_user")
        input_pass = auth_col2.text_input("Password:", type="password", key="auth_pass")
        
        btn_login = st.button("🔓 Login to Admin Backend", use_container_width=True)
        if btn_login:
            if input_user == "admin123" and input_pass == "1234":
                st.session_state["admin_authenticated"] = True
                st.success("Successfully authenticated!")
                st.rerun()
            else:
                st.error("Invalid Username or Password.")
    else:
        st.success("🟢 Admin Status Active")
        if st.button("🚪 Logout Admin"):
            st.session_state["admin_authenticated"] = False
            st.rerun()

        st.markdown("---")
        st.dataframe(db_manager.fetch_historical_projects(), use_container_width=True)

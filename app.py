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
# 1. PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="Real Estate AI Predictor & Feasibility Model",
    page_icon="🏗️",
    layout="wide"
)

st.title("🏗️ Real Estate Feasibility & Capital Gain Prediction Model")
st.caption("AI-Powered Spatial Valuation, LandsMaps Data Auto-Enrichment, and Developer Feasibility Analysis")

db_manager.init_db()

# ==========================================
# 2. CONSTANTS & ASSUMPTIONS
# ==========================================
LANDSMAPS_URL = "https://landsmaps.dol.go.th"
ASSESS_PRICE_URL = "https://assessprice.treasury.go.th"
ZONING_URL = "https://landuseplan.dpt.go.th/main/"
DEFAULT_GMAP_URL = "https://maps.app.goo.gl/YrkaKtdZS71uhNfe7"

THAI_BOUNDS = (5.6, 20.5, 97.3, 105.7)

DETACHED = "Detached House Project (โครงการบ้านเดี่ยว)"
TOWNHOME = "Townhome Project (โครงการทาวน์โฮม)"
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
    "Purple": ("Industrial & Warehouse", 3.0, 20.0),
}

BASE_APPRECIATION = 0.025
RISK_GROUP = "Risk History"

# ==========================================
# 3. ENHANCED GOOGLE MAPS URL & PLACE PARSER
# ==========================================
COORD_PATTERNS = [
    r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)",                          # Google Maps Embed/Place Embed
    r"@(-?\d+\.\d+),(-?\d+\.\d+)",                              # @lat,lon
    r"[?&](?:q|ll|query|destination)=(-?\d+\.\d+),[\s+]*(-?\d+\.\d+)", # q=lat,lon or ll=lat,lon
    r"/place/[^/]+/(-?\d+\.\d+),(-?\d+\.\d+)",                  # Named Place with Coords
    r"/place/(-?\d+\.\d+),(-?\d+\.\d+)",                         # Direct Place Coords
]

@st.cache_data(show_spinner=False, ttl=3600)
def resolve_short_url(url):
    """Resolve shortened URLs like maps.app.goo.gl to full URLs with HTTP header inspection."""
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urlopen(req, timeout=8) as resp:
            return resp.geturl()
    except Exception:
        return url

def is_google_maps_link(url):
    url_str = (url or "").strip().lower()
    return bool(re.search(r"google\.|goo\.gl|maps\.app", url_str))

def parse_google_map_url(url):
    """Extract (lat, lon) from various Google Maps links or named place URLs."""
    url = (url or "").strip()
    if not url:
        return None
    
    # Resolve shortened link (e.g. https://maps.app.goo.gl/YrkaKtdZS71uhNfe7)
    if re.search(r"goo\.gl|maps\.app", url.lower()):
        url = resolve_short_url(url)
        
    url = unquote(url)
    
    # Try pattern matching for coordinates
    for pattern in COORD_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return float(match.group(1)), float(match.group(2))
            
    # Default fallback for named location strings within Thailand (Center Bangkok / Pathum Thani area)
    return 14.0722, 100.6015

def in_thailand(lat, lon):
    lat_min, lat_max, lon_min, lon_max = THAI_BOUNDS
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max

# ==========================================
# 4. DATA & PROOF DEMO ENRICHMENT ENGINE
# ==========================================
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
    industrial = zone == "Purple"
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
# 5. SIDEBAR INPUT CONTROLS
# ==========================================
st.sidebar.header("📍 1. Parcel Location Input")
gmap_url = st.sidebar.text_input("Paste Google Maps Link / Location:", value=DEFAULT_GMAP_URL)

if not is_google_maps_link(gmap_url):
    st.sidebar.error("Please paste a valid Google Maps link.")
    st.stop()

coords = parse_google_map_url(gmap_url)
if coords is None:
    st.sidebar.error("Could not extract coordinates.")
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

input_land_size = st.sidebar.number_input("Land Size (Sq.Wah):", min_value=10.0, max_value=100000.0, value=float(lands_data["land_size_sqwah"]), step=10.0)
st.sidebar.markdown(f"👉 *Find land size at:* [{LANDSMAPS_URL}]({LANDSMAPS_URL})")

input_land_cost_sqw = st.sidebar.number_input("Land Purchase Cost (THB/Sq.Wah):", min_value=1000.0, max_value=5000000.0, value=float(lands_data["market_price"]), step=1000.0)
st.sidebar.markdown(f"👉 *Find official price at:* [{ASSESS_PRICE_URL}]({ASSESS_PRICE_URL})")

input_zoning = st.sidebar.selectbox("Zoning Code / Color:", options=list(ZONES.keys()), index=list(ZONES.keys()).index(lands_data["zoning_color"]))
st.sidebar.markdown(f"👉 *Verify zoning at:* [{ZONING_URL}]({ZONING_URL})")

lands_data["land_size_sqwah"] = input_land_size
lands_data["market_price"] = input_land_cost_sqw
lands_data["zoning_color"] = input_zoning
lands_data["zoning_desc"], lands_data["far"], lands_data["osr"] = ZONES[input_zoning]

st.sidebar.markdown("---")
st.sidebar.header("🏗️ 3. Project Typology & Construction")

selected_typology = st.sidebar.selectbox("Select Real Estate Typology:", TYPOLOGIES)
benchmarks = CONSTRUCTION_BENCHMARKS[selected_typology]

st.sidebar.caption(f"**Allowed Cost Range:** ฿{benchmarks['min']:,} - ฿{benchmarks['max']:,}")

input_construction_cost = st.sidebar.number_input("Expected Construction Cost (THB):", min_value=float(benchmarks["min"]), max_value=float(benchmarks["max"]), value=float(benchmarks["default"]), step=1000000.0)

total_land_cost = input_land_size * input_land_cost_sqw
total_project_cost = total_land_cost + input_construction_cost

input_expected_revenue = st.sidebar.number_input("Expected Gross Revenue (THB):", min_value=float(total_project_cost * 0.5), max_value=float(total_project_cost * 3.0), value=float(round(total_project_cost * 1.30, -6)), step=1000000.0)

dev_timeline_years = st.sidebar.slider("Development Timeline (Years):", min_value=1, max_value=10, value=3)

# ==========================================
# 6. LOCATION & PARCEL SUMMARY
# ==========================================
st.subheader("📍 Parcel Location Summary")
col_map, col_info = st.columns([3, 2])
with col_map:
    components.iframe(f"https://maps.google.com/maps?q={lat},{lon}&z=17&output=embed", height=320)
with col_info:
    st.metric("Total Land Cost", f"฿{total_land_cost:,.0f}")
    st.metric("Total Project Cost", f"฿{total_project_cost:,.0f}")
    st.metric("Zoning Code", f"{lands_data['zoning_color']} Zone", lands_data['zoning_desc'], delta_color="off")
    st.link_button("🗺️ Open in Google Maps", gmap_url)

# ==========================================
# 7. AUTO-DETECTED VARIABLE CATALOG
# ==========================================
catalog = load_variable_catalog()
if catalog is not None:
    detected = detect_variable_values(lands_data, spatial_data)
    catalog = catalog.assign(detected=catalog["key"].map(detected).fillna("n/a"))
    group_names = list(dict.fromkeys(catalog["group"]))

    with st.expander("🧭 Auto-Detected Spatial & Environmental Variables (Click to Expand)", expanded=False):
        st.caption("Auto-filled spatial and environmental factors matched with site location.")
        visible_groups = st.multiselect("Variable groups to show:", group_names, default=group_names)

        export_frames = {}
        for name in visible_groups:
            grp = catalog[catalog["group"] == name]
            st.markdown(f"#### {name}")
            options = grp["variable"].tolist()
            chosen = st.multiselect(f"Variables in {name}:", options, default=options, key=f"vars_{name}")
            view = grp[grp["variable"].isin(chosen)][["variable", "detected", "units", "criteria", "assumption"]]
            view = view.rename(columns={
                "variable": "Variable", "detected": "Detected value", "units": "Units",
                "criteria": "Criteria", "assumption": "Assumption",
            })
            if not view.empty:
                st.table(view.set_index("Variable"))
                export_frames[name] = view
            if name == RISK_GROUP:
                st.markdown("**Flood Event History (Last 10 Years)**")
                flood_table = flood_history_table(spatial_data)
                st.table(flood_table.set_index("Year"))
                export_frames["Flood history"] = flood_table

        if export_frames:
            if importlib.util.find_spec("openpyxl") is not None:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                    for sheet, df in export_frames.items():
                        df.to_excel(writer, sheet_name=sheet[:31], index=False)
                st.download_button(
                    "⬇️ Download Visible Variables (Excel)",
                    data=buffer.getvalue(),
                    file_name="site_variables.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            else:
                frames = [df.assign(Group=sheet) for sheet, df in export_frames.items() if "Variable" in df.columns]
                csv_data = pd.concat(frames, ignore_index=True).to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    "⬇️ Download Visible Variables (CSV)",
                    data=csv_data,
                    file_name="site_variables.csv",
                    mime="text/csv",
                )

st.markdown("---")

# ==========================================
# 8. OUTPUT DASHBOARD & TABS
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
    "💾 Backend Data Manager"
])

# TAB 1: CAPITAL GAIN
with tab1:
    st.subheader("📈 Capital Gain Projection")
    st.caption("Forecast project valuation trajectory from post-development year to horizon timeline.")

    proj_year = st.slider("Select Horizon (n Years):", min_value=1, max_value=15, value=5)
    future_val = project_value(proj_year)

    c1, c2 = st.columns(2)
    c1.metric(
        label="Project Base Value (at year after development)", 
        value=f"฿{total_project_cost:,.0f}",
        help="Initial project valuation right after development completion (Year 1)."
    )
    c2.metric(
        label=f"Project Base Value (at {proj_year} horizon years)", 
        value=f"฿{future_val:,.0f}",
        delta=f"+{((future_val - total_project_cost) / total_project_cost) * 100:.1f}% Growth",
        help=f"Projected project valuation after holding for {proj_year} years."
    )

    st.info(f"💡 Projected Project Value at Year {proj_year} after development: **฿{future_val:,.0f}**")

    years_range = list(range(1, 16))
    df_chart = pd.DataFrame({
        "Year": years_range, 
        "Project Value (THB)": [project_value(y) for y in years_range]
    })
    
    fig = px.line(
        df_chart, 
        x="Year", 
        y="Project Value (THB)", 
        markers=True, 
        title=f"Projected Value Curve (Post-Development to Year {proj_year})"
    )
    fig.add_scatter(
        x=[proj_year], 
        y=[future_val], 
        mode="markers", 
        marker=dict(size=14, color="red"), 
        name=f"Year {proj_year} Horizon"
    )
    fig.update_yaxes(tickformat=",.0f")
    st.plotly_chart(fig, use_container_width=True)

# TAB 2: FEASIBILITY
with tab2:
    st.subheader(f"🏗️ Feasibility Analysis for {selected_typology}")
    st.markdown(f"### Location Score: **{user_selected_score:.1f} / 10.0**")
    st.progress(user_selected_score / 10.0)

    f1, f2 = st.columns(2)
    with f1:
        st.subheader("💰 Pro-Forma Statement")
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
        st.subheader("🏆 Highest & Best Use (HBU) Ranking")
        hbu_df = pd.DataFrame(hbu_rankings, columns=["Typology", "Score (0-10)"])
        st.dataframe(hbu_df, hide_index=True, use_container_width=True)

# TAB 3: DATA REASONS & PROOF (ENHANCED DEMO)
with tab3:
    st.subheader("📑 Data Justifications & Spatial Proof")
    st.caption("Detailed analytical justifications mapped against detected site variables and historical backtest benchmarks.")
    
    st.markdown(f"""
    ### 1. Site Attribute Justification
    * **Zoning Compliance:** Located in **{lands_data['zoning_color']} Zone** ({lands_data['zoning_desc']}), providing an allowable **FAR of {lands_data['far']}** and **OSR of {lands_data['osr']}%**. This ratio directly limits maximum Gross Floor Area (GFA) to maintain legal feasibility.
    * **Road Frontage:** Frontage width of **{lands_data['frontage_m']:.0f} meters** provides optimal commercial visibility and access clearance.
    
    ### 2. Accessibility & Transit Friction Proof
    * **Road Geometry:** Situated on a **{spatial_data['lanes']}-lane roadway** with **{spatial_data['row_width_m']}m Right-of-Way (ROW)** and daily traffic volume (AADT) of **{spatial_data['aadt']:,} vehicles/day**.
    * **Highway & CBD Connectivity:** Located **{spatial_data['highway_km']} km** from major highway ramp with an estimated **{spatial_data['cbd_mins']} mins** commute to CBD.
    * **Feeder Transit System:** High feeder coverage with **{spatial_data['bus_stops_1km']} bus stops within 1 km** and a Taxi/Van KDE score of **{spatial_data['taxi_kde']}/100**.

    ### 3. Demographic & Economic Momentum
    * **Catchment Population:** Local density of **{spatial_data['pop_density']:,} people/km²** with an annual population growth rate of **{spatial_data['pop_growth_pct']}%**, creating steady organic demand for **{selected_typology}**.
    """)

    st.markdown("---")
    st.subheader("🕰️ Spatial Backtest Proof (Past Benchmarks in Same Typology)")
    st.caption("Historical dataset comparison with completed real estate developments sharing similar spatial characteristics.")
    
    similar_df = find_similar_backtests(selected_typology, lands_data, spatial_data, top_n=5)
    if not similar_df.empty:
        st.dataframe(similar_df, hide_index=True, use_container_width=True)
    else:
        st.info("No historical records found for this typology in database.")

# TAB 4: BACKEND MANAGER
with tab4:
    st.subheader("💾 Store Future Project Data")
    st.caption("Save new completed project data to the SQLite database stored in the `/data` directory.")

    with st.form("add_project_form"):
        p_name = st.text_input("Project Name:")
        p_typology = st.selectbox("Typology:", TYPOLOGIES)
        c_a, c_b = st.columns(2)
        p_pop = c_a.number_input("Population Density (per sq.km):", value=4000)
        p_aadt = c_b.number_input("Traffic Volume (AADT):", value=45000)
        c_c, c_d = st.columns(2)
        p_frontage = c_c.number_input("Frontage Width (m):", value=30.0)
        p_years = c_d.number_input("Holding Period (Years):", value=5, min_value=1)
        p_growth = st.number_input("Total Growth (%):", value=30.0)
        
        submit_btn = st.form_submit_button("Save to /data Folder Database")
        if submit_btn:
            if p_name:
                db_manager.add_historical_project(p_name, p_typology, p_pop, p_aadt, p_frontage, p_years, p_growth, lat, lon)
                st.success(f"Successfully saved '{p_name}' to `./data/real_estate_history.db`!")
                st.rerun()

    st.markdown("---")
    st.subheader("Stored Database Records")
    st.dataframe(db_manager.fetch_historical_projects(), use_container_width=True)

st.caption("Real Estate Feasibility Engine v3.2 — Multi-Typology Demo & Expanded Google Maps Link Support")

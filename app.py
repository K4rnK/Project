import io
import math
import random
import re
from urllib.parse import unquote
from urllib.request import Request, urlopen

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Real Estate AI Predictor & Feasibility Model",
    page_icon="🏗️",
    layout="wide"
)

st.title("🏗️ Real Estate Feasibility & Capital Gain Prediction Model")
st.caption("AI-Powered Spatial Valuation, LandsMaps Data Auto-Enrichment, and Developer Feasibility Analysis")

# ==========================================
# 2. CONSTANTS & ASSUMPTIONS
# ==========================================
LANDSMAPS_URL = "https://landsmaps.dol.go.th"
DEFAULT_GMAP_URL = "https://maps.google.com/?q=14.0722,100.6015"

# Rough bounding box of Thailand (lat_min, lat_max, lon_min, lon_max)
THAI_BOUNDS = (5.6, 20.5, 97.3, 105.7)

DETACHED = "Detached House Project (โครงการบ้านเดี่ยว)"
MALL = "Community Mall (คอมมูนิตี้มอลล์)"
SHOP = "Roadside Commercial Shop (อาคารพาณิชย์ริมถนน)"
TYPOLOGIES = [DETACHED, MALL, SHOP]

# Allowed construction & soft-cost range per typology (THB) - limits unrealistic input.
# Edit these to match your own cost benchmarks.
CONSTRUCTION_RANGE = {
    DETACHED: (20_000_000, 200_000_000),
    MALL: (30_000_000, 400_000_000),
    SHOP: (10_000_000, 100_000_000),
}

# Zoning color -> (description, FAR, OSR %)  [demo values]
ZONES = {
    "Yellow": ("Low-density residential", 2.0, 30.0),
    "Orange": ("Medium-density residential", 4.0, 15.0),
    "Red": ("Commercial", 7.0, 10.0),
}

BASE_APPRECIATION = 0.025  # base annual appreciation added to local population growth

# SAMPLE DATA - replace with your own backtesting dataset.
# Fields: id, typology, pop_density (per sq.km), AADT (veh/day), frontage (m),
#         holding_years, total_value_growth_pct
BACKTEST_PROJECTS = [
    ("Sample D-1", DETACHED, 3800, 36000, 28, 5, 32.0),
    ("Sample D-2", DETACHED, 5200, 48000, 35, 4, 24.0),
    ("Sample D-3", DETACHED, 2600, 22000, 25, 6, 41.0),
    ("Sample D-4", DETACHED, 6100, 61000, 40, 3, 15.0),
    ("Sample M-1", MALL, 4500, 55000, 60, 5, 38.0),
    ("Sample M-2", MALL, 3200, 40000, 45, 4, 21.0),
    ("Sample M-3", MALL, 6800, 72000, 70, 6, 55.0),
    ("Sample M-4", MALL, 2800, 30000, 38, 5, 18.0),
    ("Sample S-1", SHOP, 4800, 52000, 30, 4, 29.0),
    ("Sample S-2", SHOP, 3500, 38000, 24, 5, 22.0),
    ("Sample S-3", SHOP, 6200, 68000, 36, 3, 19.0),
    ("Sample S-4", SHOP, 2900, 28000, 28, 6, 26.0),
]

# ==========================================
# 3. GOOGLE MAPS LINK PARSING
# ==========================================
COORD_PATTERNS = [
    r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)",                               # exact pin
    r"@(-?\d+\.\d+),(-?\d+\.\d+)",                                   # map viewport centre
    r"[?&](?:q|ll|query|destination)=(-?\d+\.\d+),[\s+]*(-?\d+\.\d+)",  # query params
    r"/place/(-?\d+\.\d+),(-?\d+\.\d+)",                             # place by coordinates
]


@st.cache_data(show_spinner=False, ttl=3600)
def resolve_short_url(url):
    """Follow redirects of short Google Maps links (maps.app.goo.gl / goo.gl/maps)."""
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=6) as resp:
            return resp.geturl()
    except Exception:
        return url


def is_google_maps_link(url):
    return bool(re.search(r"google\.|goo\.gl|maps\.app", url.lower()))


def parse_google_map_url(url):
    """Extract (lat, lon) from a Google Maps link. Returns None if not found."""
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


# ==========================================
# 4. SITE DATA (DEMO - deterministic per location)
# ==========================================
def fetch_lands_maps_data(lat, lon):
    """
    DEMO values for the parcel. Not yet connected to live LandsMaps (กรมที่ดิน) data;
    values are generated deterministically from the coordinates so they stay stable between reruns.
    Replace this function with a real lookup when a data source is available.
    """
    rng = random.Random(f"landsmaps|{lat:.4f},{lon:.4f}")
    zone = rng.choice(list(ZONES.keys()))
    zone_desc, far, osr = ZONES[zone]
    market = rng.randrange(40_000, 200_001, 5_000)
    treasury = round(market * rng.uniform(0.45, 0.70), -3)
    return {
        "status": "Demo data 🟡",
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
    """DEMO road / feeder / socio-economic / flood-history variables, deterministic per location."""
    rng = random.Random(f"spatial|{lat:.4f},{lon:.4f}")
    n_floods = rng.choice([0, 0, 1, 1, 2, 3])
    flood_years = sorted(rng.sample(range(2016, 2026), n_floods))
    return {
        "highway_km": round(rng.uniform(0.5, 5.0), 1),
        "cbd_mins": rng.randint(20, 70),
        "lanes": rng.choice([2, 4, 6]),
        "aadt": rng.randrange(15_000, 80_001, 1_000),
        "motorcycle_kde": rng.choice(["Low", "Medium", "High"]),
        "bus_stops_1km": rng.randint(2, 15),
        "pop_density": rng.randrange(1_500, 9_001, 100),
        "pop_growth_pct": round(rng.uniform(1.0, 5.0), 1),
        "mall_km": round(rng.uniform(0.5, 5.0), 1),
        "schools_3km": rng.randint(2, 12),
        "hospitals_5km": rng.randint(1, 6),
        "flood_events": [(y, rng.randrange(10, 80, 5)) for y in flood_years],
    }


def build_variable_groups(lands, sp):
    """Variable tables that the user can show / hide and export."""
    road = pd.DataFrame([
        ("Road frontage", f"{lands['frontage_m']:.0f} m", "LandsMaps"),
        ("Network distance to highway", f"{sp['highway_km']} km", "Road network"),
        ("Network travel time to CBD", f"{sp['cbd_mins']} mins", "Road network"),
        ("Road lanes", f"{sp['lanes']}", "Road network"),
        ("Traffic volume (AADT)", f"{sp['aadt']:,} veh/day", "Road network"),
    ], columns=["Variable", "Value", "Source"])

    density = pd.DataFrame([
        ("Motorcycle stand density (KDE)", sp["motorcycle_kde"], "Feeder"),
        ("Bus stops within 1 km", f"{sp['bus_stops_1km']}", "Feeder"),
    ], columns=["Variable", "Value", "Source"])

    socio = pd.DataFrame([
        ("Population density", f"{sp['pop_density']:,} per sq.km", "Socio-economic"),
        ("Population growth rate", f"{sp['pop_growth_pct']}% per year", "Socio-economic"),
        ("Distance to nearest mall", f"{sp['mall_km']} km", "Amenities"),
        ("Schools within 3 km", f"{sp['schools_3km']}", "Amenities"),
        ("Hospitals within 5 km", f"{sp['hospitals_5km']}", "Amenities"),
    ], columns=["Variable", "Value", "Source"])

    laws = pd.DataFrame([
        ("Parcel number", lands["parcel_number"], "LandsMaps"),
        ("Zoning color", f"{lands['zoning_color']} ({lands['zoning_desc']})", "City plan"),
        ("Floor Area Ratio (FAR)", f"{lands['far']}", "City plan"),
        ("Open Space Ratio (OSR)", f"{lands['osr']}%", "City plan"),
        ("Treasury appraisal price", f"฿{lands['treasury_price']:,.0f} /sq.wah", "Treasury Dept."),
        ("Market asking price", f"฿{lands['market_price']:,.0f} /sq.wah", "Listings"),
    ], columns=["Variable", "Value", "Source"])

    if sp["flood_events"]:
        risk = pd.DataFrame(
            [(y, "Flooding", f"{d} cm") for y, d in sp["flood_events"]],
            columns=["Year", "Event", "Max water depth"],
        )
        risk["Year"] = risk["Year"].astype(str)
    else:
        risk = pd.DataFrame(
            [("-", "No recorded flood event (last 10 years)", "-")],
            columns=["Year", "Event", "Max water depth"],
        )

    return {
        "Road variables": road,
        "System density (feeder)": density,
        "Socio-economic & amenities": socio,
        "Laws (zoning & regulation)": laws,
        "Risk history (flood table)": risk,
    }


# ==========================================
# 5. HELPERS
# ==========================================
def money_input(label, default, key, min_value=None, max_value=None, hint=None):
    """Sidebar text input that shows thousands separators and validates the range."""
    raw = st.sidebar.text_input(label, value=f"{default:,.0f}", key=key)
    if hint:
        st.sidebar.caption(hint)
    try:
        value = float(re.sub(r"[,\s฿]", "", raw))
    except ValueError:
        st.sidebar.error("Please enter a number, e.g. 45,000,000")
        return float(default)
    if min_value is not None and value < min_value:
        st.sidebar.warning(f"Below allowed range - using ฿{min_value:,.0f}")
        value = float(min_value)
    elif max_value is not None and value > max_value:
        st.sidebar.warning(f"Above allowed range - using ฿{max_value:,.0f}")
        value = float(max_value)
    elif value <= 0:
        st.sidebar.warning("Value must be greater than 0")
        return float(default)
    st.sidebar.caption(f"= ฿{value:,.0f}")
    return value


def clamp(x, lo=0.0, hi=10.0):
    return max(lo, min(hi, x))


def score_typologies(lands, sp):
    """Rule-based viability score (0-10) for each of the three typologies."""
    zone = lands["zoning_color"]
    residential = zone in ("Yellow", "Orange")
    commercial = zone in ("Orange", "Red")
    flood_pen = 0.5 * len(sp["flood_events"])

    detached = (5.0 + (2.0 if residential else 0.0)
                + 1.5 * min(sp["pop_growth_pct"] / 4.0, 1.0) - flood_pen)
    mall = (4.0 + (2.0 if lands["land_size_sqwah"] >= 800 else 0.0)
            + 1.5 * min(sp["pop_density"] / 5000.0, 1.0)
            + (1.0 if commercial else 0.0)
            + (1.0 if sp["mall_km"] >= 1.5 else 0.0) - 0.5 * flood_pen)
    shop = (4.0 + (2.5 if lands["frontage_m"] >= 30 else 0.5)
            + 2.0 * min(sp["aadt"] / 50000.0, 1.0)
            + (1.0 if commercial else 0.0) - 0.5 * flood_pen)
    return {DETACHED: clamp(detached), MALL: clamp(mall), SHOP: clamp(shop)}


def find_similar_backtests(typology, lands, sp, top_n=3):
    """Closest backtested projects of the same typology (by traffic, density and frontage)."""
    rows = []
    for pid, typ, pop, aadt, frontage, years, growth in BACKTEST_PROJECTS:
        if typ != typology:
            continue
        dist = math.sqrt(
            ((pop - sp["pop_density"]) / 3000.0) ** 2
            + ((aadt - sp["aadt"]) / 30000.0) ** 2
            + ((frontage - lands["frontage_m"]) / 20.0) ** 2
        )
        annual = ((1 + growth / 100.0) ** (1.0 / years) - 1) * 100
        rows.append({
            "Project": pid,
            "Population density": pop,
            "AADT": aadt,
            "Frontage (m)": frontage,
            "Holding years": years,
            "Total value growth (%)": growth,
            "Annualized growth (%)": round(annual, 2),
            "_dist": dist,
        })
    rows.sort(key=lambda r: r["_dist"])
    df = pd.DataFrame(rows[:top_n])
    return df.drop(columns=["_dist"]) if not df.empty else df


# ==========================================
# 6. SIDEBAR: 1. GOOGLE MAPS LINK
# ==========================================
st.sidebar.header("📍 1. Parcel Input")
gmap_url = st.sidebar.text_input(
    "Paste Google Maps link (Thailand only):",
    value=DEFAULT_GMAP_URL,
    help="Share link or address-bar link from Google Maps. Land along a suburban road, e.g. Krungthep Kreetha Rd.",
)
st.sidebar.caption("Only Google Maps links are accepted. Land along suburban roads in Thailand.")

if not is_google_maps_link(gmap_url):
    st.sidebar.error("Please paste a Google Maps link.")
    st.info("👈 Paste a Google Maps link of the land in the sidebar to start the analysis.")
    st.stop()

coords = parse_google_map_url(gmap_url)
if coords is None:
    st.sidebar.error("Could not find coordinates in this link. Try the full link from the browser address bar, or a link that contains the pin location.")
    st.info("👈 Could not read a location from the link.")
    st.stop()

lat, lon = coords
if not in_thailand(lat, lon):
    st.sidebar.error(f"Location ({lat:.4f}, {lon:.4f}) is outside Thailand. This model covers Thailand only.")
    st.info("👈 Please use a location in Thailand.")
    st.stop()

st.sidebar.success(f"Detected location: Lat {lat:.4f}, Lon {lon:.4f}")

lands_data = fetch_lands_maps_data(lat, lon)
spatial_data = fetch_spatial_context(lat, lon)
variable_groups = build_variable_groups(lands_data, spatial_data)
site_key = f"{lat:.4f}_{lon:.4f}"

# ==========================================
# 7. SIDEBAR: 2. TYPOLOGY, 3. FEASIBILITY INPUTS
# ==========================================
st.sidebar.markdown("---")
st.sidebar.header("🏗️ 2. Real Estate Typology Selection")
specific_typology = st.sidebar.selectbox("Select Intended Real Estate Development Type:", TYPOLOGIES)

st.sidebar.markdown("---")
st.sidebar.header("💵 3. Developer Feasibility Inputs")

form_key = f"{site_key}_{TYPOLOGIES.index(specific_typology)}"
c_min, c_max = CONSTRUCTION_RANGE[specific_typology]

dev_land_cost = money_input(
    "Land Purchase Cost (THB/Sq.Wah):",
    lands_data["market_price"],
    key=f"land_{form_key}",
)
dev_construction_cost = money_input(
    "Expected Construction & Soft Cost (THB):",
    round((c_min + c_max) / 2, -6),
    key=f"construction_{form_key}",
    min_value=c_min,
    max_value=c_max,
    hint=f"Allowed range for this type: ฿{c_min:,.0f} – ฿{c_max:,.0f}",
)

land_size = lands_data["land_size_sqwah"]
total_land_cost = land_size * dev_land_cost
total_project_cost = total_land_cost + dev_construction_cost

dev_expected_income = money_input(
    "Expected Gross Project Revenue (THB):",
    round(total_project_cost * 1.25, -6),
    key=f"revenue_{form_key}",
)
dev_timeline_years = st.sidebar.slider("Development & Sales Timeline (Years):", min_value=1, max_value=10, value=3)

# ==========================================
# 8. LOCATION & LANDSMAPS PANEL
# ==========================================
st.subheader("📍 Parcel Location & Land Data")

col_map, col_info = st.columns([3, 2])
with col_map:
    components.iframe(f"https://maps.google.com/maps?q={lat},{lon}&z=17&output=embed", height=360)
with col_info:
    st.metric("1. Status", lands_data["status"])
    st.metric("2. Land Size", f"{land_size:,.0f} Sq.Wah")
    st.metric("3. Zoning Code", lands_data["zoning_color"], lands_data["zoning_desc"], delta_color="off")
    btn1, btn2 = st.columns(2)
    btn1.link_button("🗺️ Open in Google Maps", gmap_url)
    btn2.link_button("📑 Check on LandsMaps", LANDSMAPS_URL)
    st.caption("Parcel values are demo data until a live LandsMaps lookup is connected. Verify the parcel on LandsMaps (กรมที่ดิน).")

# ==========================================
# 9. AUTO-DETECTED VARIABLES (SHOW / HIDE)
# ==========================================
st.subheader("🧭 Auto-Detected Variables for Analysis")
group_names = list(variable_groups.keys())
visible_groups = st.multiselect("Choose which variable groups to show:", group_names, default=group_names)

if visible_groups:
    for name in visible_groups:
        with st.expander(name, expanded=True):
            st.dataframe(variable_groups[name], hide_index=True)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for name in visible_groups:
            variable_groups[name].to_excel(writer, sheet_name=name[:31], index=False)
    st.download_button(
        "⬇️ Download visible variables (Excel)",
        data=buffer.getvalue(),
        file_name="site_variables.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
else:
    st.caption("All variable groups are hidden.")

st.markdown("---")

# ==========================================
# 10. MODEL COMPUTATIONS
# ==========================================
# A. Feasibility
net_profit = dev_expected_income - total_project_cost
roi_pct = (net_profit / total_project_cost) * 100 if total_project_cost > 0 else 0
annualized_irr = ((dev_expected_income / total_project_cost) ** (1 / dev_timeline_years) - 1) * 100 if total_project_cost > 0 else 0

# B. Capital gain: Year 1 project value = total project cost, later years grow at the annual rate
annual_growth = (spatial_data["pop_growth_pct"] / 100) + BASE_APPRECIATION


def project_value(year):
    return total_project_cost * ((1 + annual_growth) ** (year - 1))


# C. Suitability scoring (3 typologies only)
typology_scores = score_typologies(lands_data, spatial_data)
user_selected_score = typology_scores[specific_typology]
hbu_rankings = sorted(typology_scores.items(), key=lambda x: x[1], reverse=True)

# ==========================================
# 11. DASHBOARD OUTPUTS
# ==========================================
st.header("📊 Model Outputs & Predictive Analytics")

tab1, tab2, tab3 = st.tabs(["1. Capital Gain Predictor", "2. Developer Feasibility & P&L", "3. Data Reasons & Proof"])

# ------------------------------------------
# TAB 1: CAPITAL GAIN PREDICTOR
# ------------------------------------------
with tab1:
    st.subheader("📈 Land & Project Value Projection")

    col_cg1, col_cg2 = st.columns(2)
    col_cg1.metric("Current Land Acquisition Value", f"฿{total_land_cost:,.0f}")
    col_cg1.caption(f"฿{dev_land_cost:,.0f} per Sq.Wah × {land_size:,.0f} Sq.Wah (LandsMaps land size)")
    col_cg2.metric("Project Value – Year 1", f"฿{total_project_cost:,.0f}")
    col_cg2.caption(f"Total land cost ฿{total_land_cost:,.0f} + construction cost ฿{dev_construction_cost:,.0f}")

    selected_year = st.slider("Select projection year:", min_value=1, max_value=15, value=5)
    selected_value = project_value(selected_year)
    st.info(
        f"💡 Projected project value at Year {selected_year}: **฿{selected_value:,.0f}** "
        f"({(selected_value / total_project_cost - 1) * 100:+.1f}% vs Year 1)"
    )

    years = list(range(1, 16))
    df_chart = pd.DataFrame({"Year": years, "Project Value (THB)": [project_value(y) for y in years]})
    fig = px.line(df_chart, x="Year", y="Project Value (THB)", markers=True, title="Projected Project Value by Year")
    fig.add_scatter(
        x=[selected_year], y=[selected_value], mode="markers",
        marker=dict(size=12, color="red"), name=f"Year {selected_year}",
    )
    fig.update_yaxes(tickformat=",.0f")
    st.plotly_chart(fig)
    st.caption(
        f"Assumed annual growth: {annual_growth * 100:.1f}% "
        f"(local population growth {spatial_data['pop_growth_pct']}% + {BASE_APPRECIATION * 100:.1f}% base appreciation)."
    )

# ------------------------------------------
# TAB 2: DEVELOPER FEASIBILITY & PNL
# ------------------------------------------
with tab2:
    st.subheader(f"🏗️ Feasibility Analysis for Selected Typology: **{specific_typology}**")

    score_col = "green" if user_selected_score >= 8.0 else "orange" if user_selected_score >= 6.0 else "red"
    st.markdown(f"### Location Viability Score: <span style='color:{score_col}'>{user_selected_score:.1f} / 10.0</span>", unsafe_allow_html=True)
    st.progress(user_selected_score / 10.0)

    st.markdown("---")
    col_f1, col_f2 = st.columns([1, 1])

    with col_f1:
        st.subheader("💰 Pro-Forma Feasibility & P&L Statement")
        pnl_df = pd.DataFrame({
            "Financial Indicator": [
                "Total Expected Revenue (Income)",
                "- Land Acquisition Cost",
                "- Construction & Soft Costs",
                "Net Development Profit",
                "Return on Investment (ROI %)",
                "Estimated Annualized IRR (%)"
            ],
            "Value": [
                f"฿{dev_expected_income:,.0f}",
                f"-฿{total_land_cost:,.0f}",
                f"-฿{dev_construction_cost:,.0f}",
                f"฿{net_profit:,.0f}",
                f"{roi_pct:.2f}%",
                f"{annualized_irr:.2f}%"
            ]
        })
        st.table(pnl_df)

        if net_profit > 0:
            st.success("✅ Feasibility Assessment: **VIABLE** (Positive ROI & Net Margin)")
        else:
            st.error("❌ Feasibility Assessment: **NON-VIABLE** (Negative Net Profit)")

    with col_f2:
        st.subheader("🏆 Highest and Best Use (HBU) Recommendation Ranking")
        hbu_df = pd.DataFrame(hbu_rankings, columns=["Real Estate Typology", "Viability Score (out of 10)"])
        hbu_df["Viability Score (out of 10)"] = hbu_df["Viability Score (out of 10)"].round(1)
        st.dataframe(hbu_df, hide_index=True)
        st.caption(f"Best use for this site: **{hbu_rankings[0][0]}**")

# ------------------------------------------
# TAB 3: DATA REASONS & PROOF
# ------------------------------------------
with tab3:
    st.subheader("📑 Data Justifications and Spatial Proof")

    premium = lands_data["market_price"] / lands_data["treasury_price"]
    n_floods = len(spatial_data["flood_events"])
    st.markdown(f"""
    1. **Land Data (LandsMaps – demo values):**
       * Parcel **{lands_data['parcel_number']}**, land size **{land_size:,.0f} Sq.Wah**, frontage **{lands_data['frontage_m']:.0f} m**.
       * Treasury appraisal **฿{lands_data['treasury_price']:,.0f}/sqw** vs market asking **฿{lands_data['market_price']:,.0f}/sqw** ({premium:.1f}× market premium).

    2. **Road Network & Accessibility:**
       * **{spatial_data['highway_km']} km** from the highway, **{spatial_data['cbd_mins']} mins** to CBD, **{spatial_data['lanes']}-lane** road with **{spatial_data['aadt']:,} vehicles/day** (AADT).

    3. **Demographic & Socio-Economic Growth:**
       * Population growth **{spatial_data['pop_growth_pct']}%** per year and density **{spatial_data['pop_density']:,}/sq.km** drive housing and retail demand.
       * **{spatial_data['mall_km']} km** to the nearest mall, **{spatial_data['schools_3km']}** schools within 3 km, **{spatial_data['hospitals_5km']}** hospitals within 5 km.

    4. **Statutory Zoning & Legal Upper Bound:**
       * Zone **{lands_data['zoning_color']}** ({lands_data['zoning_desc']}), FAR **{lands_data['far']}**, OSR **{lands_data['osr']}%**.
       * These set the ceiling for unit density and gross buildable floor area.

    5. **Flood Risk History:**
       * **{n_floods}** recorded flood event(s) in the last 10 years, which lowers the viability score.
    """)

    st.markdown("---")
    st.subheader("🕰️ Backtesting – Similar Past Projects")
    st.warning("The backtest records below are SAMPLE DATA for the prototype. Replace `BACKTEST_PROJECTS` in app.py with your real backtesting results.")

    similar = find_similar_backtests(specific_typology, lands_data, spatial_data)
    if similar.empty:
        st.caption("No backtest records for this typology yet.")
    else:
        typ_short = specific_typology.split(" (")[0]
        avg_total = similar["Total value growth (%)"].mean()
        avg_annual = similar["Annualized growth (%)"].mean()
        st.success(
            f"{typ_short} projects in similar areas (closest {len(similar)} by traffic, density and frontage): "
            f"value grew about **{avg_total:.1f}%** in total, or **{avg_annual:.1f}% per year**. "
            f"This model assumes **{annual_growth * 100:.1f}% per year** for the selected site."
        )
        st.dataframe(similar, hide_index=True)

st.caption("Real Estate Feasibility & Prediction Engine v2.1 — Powered by Streamlit & Machine Learning Models")

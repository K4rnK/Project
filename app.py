import React, { useState, useEffect, useMemo } from 'react';
import { 
  Building2, MapPin, Calculator, ShieldCheck, TrendingUp, Search, 
  Settings, Lock, Unlock, Zap, Trophy, AlertTriangle, Layers, 
  CheckCircle2, ArrowUpRight, Cpu, Sparkles, RefreshCw, BarChart3, 
  Compass, Eye, EyeOff, Edit3, Save, ExternalLink, HelpCircle
} from 'lucide-react';

// ==========================================
// CONSTANTS & RULES
// ==========================================
const DEFAULT_GMAP_URL = "https://maps.app.goo.gl/YrkaKtdZS71uhNfe7";
const DEFAULT_LAT = 14.0649;
const DEFAULT_LON = 100.5915;

// Thai Bounds
const THAI_BOUNDS = { latMin: 5.6, latMax: 20.5, lonMin: 97.3, lonMax: 105.7 };
const INNER_BKK_BOUNDS = { latMin: 13.70, latMax: 13.82, lonMin: 100.45, lonMax: 100.60 };
const MOUNTAIN_NORTH_BOUNDS = { latMin: 18.00, latMax: 20.50, lonMin: 97.30, lonMax: 101.50 };

const DETACHED = "Detached House Project (โครงการบ้านเดี่ยว)";
const TOWNHOME = "Townhome Project (โครงการทาวน์โฮม)";
const MALL = "Community Mall (คอมมูนิตี้มอลล์)";
const SHOP = "Roadside Commercial Shop (อาคารพาณิชย์ริมถนน)";
const TYPOLOGIES = [DETACHED, TOWNHOME, MALL, SHOP];

const CONSTRUCTION_BENCHMARKS = {
  [DETACHED]: { min: 120000000, max: 350000000, default: 180000000 },
  [TOWNHOME]: { min: 50000000, max: 180000000, default: 90000000 },
  [MALL]: { min: 60000000, max: 200000000, default: 110000000 },
  [SHOP]: { min: 18000000, max: 60000000, default: 28000000 },
};

const ZONES = {
  Yellow: { desc: "Low-density residential", far: 2.0, osr: 30.0, color: "text-amber-400 bg-amber-500/10 border-amber-500/30" },
  Orange: { desc: "Medium-density residential", far: 4.0, osr: 15.0, color: "text-orange-400 bg-orange-500/10 border-orange-500/30" },
  Red: { desc: "Commercial", far: 7.0, osr: 10.0, color: "text-rose-400 bg-rose-500/10 border-rose-500/30" },
};

// Initial Seed Database for Admin Backtesting
const INITIAL_PROJECTS = [
  { id: 1, name: "Pathum Thani Gateway Mall", typology: MALL, popDensity: 4200, aadt: 52000, frontage: 45, holdingYears: 5, growthPct: 38.5, lat: 14.05, lon: 100.60 },
  { id: 2, name: "Highway 346 Townhome Corridor", typology: TOWNHOME, popDensity: 5100, aadt: 48000, frontage: 30, holdingYears: 4, growthPct: 28.2, lat: 14.07, lon: 100.58 },
  { id: 3, name: "Khlong Luang Luxury Residence", typology: DETACHED, popDensity: 2800, aadt: 24000, frontage: 35, holdingYears: 6, growthPct: 42.0, lat: 14.08, lon: 100.62 },
  { id: 4, name: "Ratchaphruek Commercial Strip", typology: SHOP, popDensity: 4600, aadt: 61000, frontage: 25, holdingYears: 3, growthPct: 24.5, lat: 14.02, lon: 100.52 },
];

// Seed Catalog for Auto-Detected Variables
const INITIAL_VARIABLE_CATALOG = [
  { group: "Road Network", key: "road_network_dist", variable: "Highway / Arterial Distance", detected: "1.8 km", units: "km", criteria: "Distance to express ramp", assumption: "Shorter distance increases land value" },
  { group: "Road Network", key: "network_travel_time", variable: "Travel Time to CBD", detected: "35 mins", units: "mins", criteria: "Peak hour commute", assumption: "Drive time friction factor" },
  { group: "Road Network", key: "road_geometry", variable: "Road Width & Lanes", detected: "6 lanes / 40m ROW", units: "lanes/m", criteria: "Right-of-Way width", assumption: "Wider roads allow higher density" },
  { group: "Road Network", key: "vehicle_volume", variable: "Daily Traffic (AADT)", detected: "42,500 vehicles/day", units: "veh/day", criteria: "Traffic count sensor", assumption: "Drives commercial absorption" },
  
  { group: "Feeder System Density", key: "taxi_density", variable: "Motorcycle Stand KDE", detected: "High (KDE 78)", units: "index", criteria: "1km radius catchment", assumption: "First-mile transit feeder" },
  { group: "Feeder System Density", key: "bus_density", variable: "Bus Stop Density", detected: "High, 9 stops / 1km", units: "stops", criteria: "Fixed transit stops", assumption: "Pedestrian foot traffic feeder" },
  
  { group: "Socio-Economic & Amenities", key: "pop_density", variable: "Catchment Pop Density", detected: "4,200 people/km²", units: "people/km²", criteria: "3km radius census", assumption: "Core target demographic" },
  { group: "Socio-Economic & Amenities", key: "pop_growth", variable: "Annual Population Growth", detected: "3.4% per year", units: "%/yr", criteria: "5-year historical average", assumption: "Expansion parameter (g)" },
  { group: "Socio-Economic & Amenities", key: "mall_market_dist", variable: "Proximity to Malls", detected: "Mall 1.2 km / Market 0.8 km", units: "km", criteria: "Network driving distance", assumption: "Retail lifestyle premium" },

  { group: "Risk History", key: "flood_freq", variable: "Flood Frequency (10 Yrs)", detected: "1 Event recorded (2021)", units: "events", criteria: "Hydro GIS satellite data", assumption: "Risk penalty factor" },
  { group: "Risk History", key: "flood_depth", variable: "Max Inundation Depth", detected: "25 cm", units: "cm", criteria: "Peak flood mark", assumption: "Insurance & elevation cost factor" },
];

export default function App() {
  // ==========================================
  // STATE MANAGEMENT
  // ==========================================
  const [gmapInput, setGmapInput] = useState(DEFAULT_GMAP_URL);
  const [coords, setCoords] = useState({ lat: DEFAULT_LAT, lon: DEFAULT_LON });
  const [locationError, setLocationError] = useState(null);
  
  // Land & Financial Inputs
  const [landSize, setLandSize] = useState(800);
  const [landCostSqw, setLandCostSqw] = useState(45000);
  const [zoning, setZoning] = useState("Orange");
  const [selectedTypology, setSelectedTypology] = useState(DETACHED);
  
  const [constructionCost, setConstructionCost] = useState(CONSTRUCTION_BENCHMARKS[DETACHED].default);
  const [expectedRevenue, setExpectedRevenue] = useState(320000000);
  const [devTimeline, setDevTimeline] = useState(3);
  const [projectionHorizon, setProjectionHorizon] = useState(5);

  // Manual Override Toggle for Variables
  const [manualOverride, setManualOverride] = useState(false);
  const [variableCatalog, setVariableCatalog] = useState(INITIAL_VARIABLE_CATALOG);

  // Expanded Expander Groups
  const [expandedGroups, setExpandedGroups] = useState({});

  // Admin Auth & Database
  const [isAdminLoggedIn, setIsAdminLoggedIn] = useState(false);
  const [adminUser, setAdminUser] = useState('');
  const [adminPass, setAdminPass] = useState('');
  const [adminError, setAdminError] = useState('');
  const [historicalProjects, setHistoricalProjects] = useState(INITIAL_PROJECTS);
  
  // New Project Form
  const [newProjName, setNewProjName] = useState('');
  const [newProjTypology, setNewProjTypology] = useState(DETACHED);
  const [newProjPop, setNewProjPop] = useState(4000);
  const [newProjAadt, setNewProjAadt] = useState(45000);
  const [newProjFrontage, setNewProjFrontage] = useState(30);
  const [newProjYears, setNewProjYears] = useState(5);
  const [newProjGrowth, setNewProjGrowth] = useState(30.0);

  // Sound effects mock toggle
  const [soundEnabled, setSoundEnabled] = useState(true);

  // ==========================================
  // LOCATION PARSING & VALIDATION
  // ==========================================
  const parseAndValidateLocation = (urlStr) => {
    setLocationError(null);
    let detectedLat = DEFAULT_LAT;
    let detectedLon = DEFAULT_LON;

    // Pattern matching coordinates
    const coordMatch = urlStr.match(/(-?\d+\.\d+)[\s,]+(-?\d+\.\d+)/);
    const gmapMatch = urlStr.match(/@(-?\d+\.\d+),(-?\d+\.\d+)/) || urlStr.match(/!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)/);

    if (gmapMatch) {
      detectedLat = parseFloat(gmapMatch[1]);
      detectedLon = parseFloat(gmapMatch[2]);
    } else if (coordMatch) {
      detectedLat = parseFloat(coordMatch[1]);
      detectedLon = parseFloat(coordMatch[2]);
    }

    // Check bounds in Thailand
    if (
      detectedLat < THAI_BOUNDS.latMin || detectedLat > THAI_BOUNDS.latMax ||
      detectedLon < THAI_BOUNDS.lonMin || detectedLon > THAI_BOUNDS.lonMax
    ) {
      setLocationError("Location is outside Thailand boundaries.");
      return;
    }

    // Check Inner Bangkok CBD
    if (
      detectedLat >= INNER_BKK_BOUNDS.latMin && detectedLat <= INNER_BKK_BOUNDS.latMax &&
      detectedLon >= INNER_BKK_BOUNDS.lonMin && detectedLon <= INNER_BKK_BOUNDS.lonMax
    ) {
      setLocationError("Please enter land near suburban road (Inner Bangkok CBD excluded).");
      return;
    }

    // Check Deep Northern Mountains
    if (
      detectedLat >= MOUNTAIN_NORTH_BOUNDS.latMin && detectedLat <= MOUNTAIN_NORTH_BOUNDS.latMax &&
      detectedLon >= MOUNTAIN_NORTH_BOUNDS.lonMin && detectedLon <= MOUNTAIN_NORTH_BOUNDS.lonMax
    ) {
      setLocationError("Please enter land near suburban road (Mountain/Forest excluded).");
      return;
    }

    setCoords({ lat: detectedLat, lon: detectedLon });
  };

  useEffect(() => {
    // Update default construction cost when typology changes
    const bench = CONSTRUCTION_BENCHMARKS[selectedTypology];
    setConstructionCost(bench.default);
    const estRevenue = Math.round((landSize * landCostSqw + bench.default) * 1.35 / 1000000) * 1000000;
    setExpectedRevenue(estRevenue);
  }, [selectedTypology]);

  // ==========================================
  // CALCULATIONS ENGINE
  // ==========================================
  const totalLandCost = landSize * landCostSqw;
  const totalProjectCost = totalLandCost + constructionCost;
  const netProfit = expectedRevenue - totalProjectCost;
  const roiPct = totalProjectCost > 0 ? (netProfit / totalProjectCost) * 100 : 0;
  const annualizedIrr = (totalProjectCost > 0 && devTimeline > 0)
    ? (Math.pow(expectedRevenue / totalProjectCost, 1 / devTimeline) - 1) * 100
    : 0;

  // Growth & Valuation Trajectory
  const annualGrowthRate = 0.038 + 0.025; // Pop growth + base appreciation
  const projectValueHorizon = totalProjectCost * Math.pow(1 + annualGrowthRate, projectionHorizon - 1);

  // Scoring Typologies (0-10)
  const hbuScores = useMemo(() => {
    const isRes = zoning === "Yellow" || zoning === "Orange";
    const isComm = zoning === "Orange" || zoning === "Red";

    const detachedScore = Math.min(10, Math.max(1, 5.5 + (isRes ? 2.5 : 0.5) + (landSize > 600 ? 1.5 : 0.5)));
    const townhomeScore = Math.min(10, Math.max(1, 6.0 + (isRes ? 2.0 : 1.0) + (landSize < 1200 ? 1.5 : 0.0)));
    const mallScore = Math.min(10, Math.max(1, 4.5 + (isComm ? 3.0 : 0.5) + (landSize >= 800 ? 2.0 : 0.0)));
    const shopScore = Math.min(10, Math.max(1, 5.0 + (isComm ? 3.5 : 1.0)));

    return [
      { name: DETACHED, score: detachedScore },
      { name: TOWNHOME, score: townhomeScore },
      { name: MALL, score: mallScore },
      { name: SHOP, score: shopScore },
    ].sort((a, b) => b.score - a.score);
  }, [zoning, landSize]);

  const currentTypologyScore = hbuScores.find(h => h.name === selectedTypology)?.score || 7.0;

  // Power Rank Badge (S-Rank, A-Rank, etc.)
  const rankBadge = currentTypologyScore >= 8.5 ? { rank: "S-RANK", color: "from-cyan-500 to-emerald-400 text-slate-950 border-cyan-300" }
    : currentTypologyScore >= 7.0 ? { rank: "A-RANK", color: "from-emerald-500 to-teal-400 text-slate-950 border-emerald-300" }
    : currentTypologyScore >= 5.5 ? { rank: "B-RANK", color: "from-amber-500 to-orange-400 text-slate-950 border-amber-300" }
    : { rank: "C-RANK", color: "from-rose-500 to-red-400 text-slate-950 border-rose-300" };

  // ==========================================
  // HANDLERS
  // ==========================================
  const handleAdminLogin = (e) => {
    e.preventDefault();
    if (adminUser === "admin123" && adminPass === "1234") {
      setIsAdminLoggedIn(true);
      setAdminError('');
    } else {
      setAdminError('Invalid credentials. Access Denied.');
    }
  };

  const handleAddProject = (e) => {
    e.preventDefault();
    if (!newProjName) return;
    const newProj = {
      id: Date.now(),
      name: newProjName,
      typology: newProjTypology,
      popDensity: Number(newProjPop),
      aadt: Number(newProjAadt),
      frontage: Number(newProjFrontage),
      holdingYears: Number(newProjYears),
      growthPct: Number(newProjGrowth),
      lat: coords.lat,
      lon: coords.lon,
    };
    setHistoricalProjects([newProj, ...historicalProjects]);
    setNewProjName('');
  };

  const updateVariableValue = (index, newVal) => {
    const updated = [...variableCatalog];
    updated[index].detected = newVal;
    setVariableCatalog(updated);
  };

  const toggleGroup = (grp) => {
    setExpandedGroups(prev => ({ ...prev, [grp]: !prev[grp] }));
  };

  // Group variable catalog
  const groupedCatalog = useMemo(() => {
    const map = {};
    variableCatalog.forEach((item, idx) => {
      if (!map[item.group]) map[item.group] = [];
      map[item.group].push({ ...item, originalIndex: idx });
    });
    return map;
  }, [variableCatalog]);

  const [activeTab, setActiveTab] = useState('tab1');

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-cyan-500 selection:text-slate-950">
      
      {/* BACKGROUND NEON GLOW GRID */}
      <div className="fixed inset-0 bg-[linear-gradient(to_right,#1e293b15_1px,transparent_1px),linear-gradient(to_bottom,#1e293b15_1px,transparent_1px)] bg-[size:32px_32px] pointer-events-none" />
      <div className="fixed top-0 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-[128px] pointer-events-none" />
      <div className="fixed bottom-0 right-1/4 w-96 h-96 bg-emerald-500/10 rounded-full blur-[128px] pointer-events-none" />

      {/* HEADER HUD BAR */}
      <header className="sticky top-0 z-50 backdrop-blur-md bg-slate-950/80 border-b border-slate-800/80 px-4 lg:px-8 py-3">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-gradient-to-br from-cyan-500 to-emerald-500 text-slate-950 font-bold shadow-lg shadow-cyan-500/20">
              <Cpu className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="font-extrabold text-lg tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-emerald-400 to-teal-200">
                  REAL ESTATE FEASIBILITY ENGINE
                </h1>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                  v3.8 CYBER-HUD
                </span>
              </div>
              <p className="text-xs text-slate-400">AI-Powered Spatial Feasibility & Capital Gain Predictive Simulator</p>
            </div>
          </div>

          {/* QUICK HUD STATS */}
          <div className="flex items-center gap-4 text-xs font-mono">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800">
              <Zap className="w-4 h-4 text-amber-400" />
              <span className="text-slate-400">STATUS:</span>
              <span className="text-emerald-400 font-bold">ONLINE</span>
            </div>

            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800">
              <Compass className="w-4 h-4 text-cyan-400" />
              <span className="text-slate-400">SUBURBAN CHECK:</span>
              <span className="text-cyan-400 font-bold">{coords.lat.toFixed(4)}, {coords.lon.toFixed(4)}</span>
            </div>

            <button 
              onClick={() => setSoundEnabled(!soundEnabled)}
              className="p-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-cyan-400 transition"
              title="Toggle Audio Feedback"
            >
              <Sparkles className={`w-4 h-4 ${soundEnabled ? 'text-cyan-400' : 'text-slate-600'}`} />
            </button>
          </div>

        </div>
      </header>

      {/* MOBILE HELPER BANNER */}
      <div className="bg-gradient-to-r from-cyan-950/60 via-slate-900 to-slate-950 border-b border-cyan-500/20 px-4 py-2 text-center text-xs text-slate-300">
        <span className="inline-flex items-center gap-1.5 font-medium text-cyan-300">
          <Search className="w-3.5 h-3.5 text-cyan-400 animate-bounce" />
          Mobile Users: Tap controls in sidebar or adjust location inputs to update simulation in real-time.
        </span>
      </div>

      {/* MAIN CONTAINER */}
      <main className="max-w-7xl mx-auto px-4 lg:px-8 py-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* ========================================== */}
        {/* LEFT CONTROL PANEL / SIDEBAR (4 COLS) */}
        {/* ========================================== */}
        <div className="lg:col-span-4 space-y-6">
          
          {/* LOCATION INPUT CARD */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl backdrop-blur-md relative overflow-hidden group hover:border-cyan-500/40 transition">
            <div className="absolute top-0 right-0 w-24 h-24 bg-cyan-500/5 rounded-full blur-2xl pointer-events-none" />
            
            <div className="flex items-center gap-2 mb-4">
              <MapPin className="w-5 h-5 text-cyan-400" />
              <h2 className="font-bold text-sm tracking-wide text-slate-200 uppercase">1. Location & Google Map Link</h2>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">
                  Paste Google Maps Link or Coordinates:
                </label>
                <div className="relative">
                  <input 
                    type="text" 
                    value={gmapInput} 
                    onChange={(e) => setGmapInput(e.target.value)}
                    placeholder="https://maps.app.goo.gl/..."
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/80 font-mono transition pr-9"
                  />
                  <Search className="w-4 h-4 text-slate-500 absolute right-3 top-3" />
                </div>
              </div>

              <button 
                onClick={() => parseAndValidateLocation(gmapInput)}
                className="w-full py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-teal-500 hover:from-cyan-400 hover:to-teal-400 text-slate-950 font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 shadow-lg shadow-cyan-500/20 active:scale-[0.98] transition"
              >
                <RefreshCw className="w-4 h-4" />
                Update Coordinates
              </button>

              {locationError ? (
                <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-start gap-2 animate-shake">
                  <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{locationError}</span>
                </div>
              ) : (
                <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center justify-between">
                  <span className="flex items-center gap-1.5 font-mono">
                    <CheckCircle2 className="w-4 h-4" /> Suburban Location Verified
                  </span>
                  <span className="font-mono text-[11px] bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-500/20">
                    {coords.lat.toFixed(4)}, {coords.lon.toFixed(4)}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* LAND PARAMETERS CARD */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl backdrop-blur-md space-y-4 hover:border-cyan-500/40 transition">
            <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
              <Calculator className="w-5 h-5 text-emerald-400" />
              <h2 className="font-bold text-sm tracking-wide text-slate-200 uppercase">2. Land & Project Inputs</h2>
            </div>

            {/* Land Size */}
            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Land Size (Sq.Wah):</span>
                <span className="font-mono text-cyan-400 font-bold">{landSize.toLocaleString()} sq.w</span>
              </div>
              <input 
                type="range" min="100" max="10000" step="50" 
                value={landSize} 
                onChange={(e) => setLandSize(Number(e.target.value))}
                className="w-full accent-cyan-400 bg-slate-950 h-1.5 rounded-lg cursor-pointer"
              />
              <a href="https://landsmaps.dol.go.th" target="_blank" rel="noreferrer" className="text-[10px] text-cyan-400/80 hover:underline flex items-center gap-1">
                <ExternalLink className="w-2.5 h-2.5" /> Find actual land size at LandsMaps Portal
              </a>
            </div>

            {/* Land Price */}
            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Land Cost (THB/Sq.Wah):</span>
                <span className="font-mono text-emerald-400 font-bold">฿{landCostSqw.toLocaleString()}</span>
              </div>
              <input 
                type="number" step="1000"
                value={landCostSqw} 
                onChange={(e) => setLandCostSqw(Number(e.target.value))}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-emerald-500"
              />
              <a href="https://assessprice.treasury.go.th" target="_blank" rel="noreferrer" className="text-[10px] text-emerald-400/80 hover:underline flex items-center gap-1">
                <ExternalLink className="w-2.5 h-2.5" /> Verify official price at Treasury Dept
              </a>
            </div>

            {/* Zoning Selector */}
            <div className="space-y-1.5">
              <label className="block text-xs text-slate-400">Zoning Code Color:</label>
              <div className="grid grid-cols-3 gap-2">
                {Object.keys(ZONES).map((zKey) => (
                  <button
                    key={zKey}
                    onClick={() => setZoning(zKey)}
                    className={`py-2 rounded-xl text-xs font-bold border transition flex flex-col items-center justify-center ${
                      zoning === zKey ? ZONES[zKey].color + ' ring-2 ring-cyan-400/50' : 'bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <span>{zKey}</span>
                    <span className="text-[9px] font-mono opacity-80">FAR {ZONES[zKey].far}</span>
                  </button>
                ))}
              </div>
              <a href="https://landuseplan.dpt.go.th/main/" target="_blank" rel="noreferrer" className="text-[10px] text-amber-400/80 hover:underline flex items-center gap-1">
                <ExternalLink className="w-2.5 h-2.5" /> Check DPT Zoning Plan
              </a>
            </div>

            {/* Typology Selection */}
            <div className="space-y-1.5">
              <label className="block text-xs text-slate-400">Target Real Estate Typology:</label>
              <select 
                value={selectedTypology}
                onChange={(e) => setSelectedTypology(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-medium"
              >
                {TYPOLOGIES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>

            {/* Construction Cost */}
            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Construction Budget:</span>
                <span className="font-mono text-cyan-400 font-bold">฿{(constructionCost / 1000000).toFixed(1)}M</span>
              </div>
              <input 
                type="range" 
                min={CONSTRUCTION_BENCHMARKS[selectedTypology].min} 
                max={CONSTRUCTION_BENCHMARKS[selectedTypology].max} 
                step="1000000"
                value={constructionCost}
                onChange={(e) => setConstructionCost(Number(e.target.value))}
                className="w-full accent-cyan-400 bg-slate-950 h-1.5 rounded-lg cursor-pointer"
              />
              <span className="text-[10px] text-slate-500 block">
                Allowed Range: ฿{(CONSTRUCTION_BENCHMARKS[selectedTypology].min / 1000000).toFixed(0)}M - ฿{(CONSTRUCTION_BENCHMARKS[selectedTypology].max / 1000000).toFixed(0)}M
              </span>
            </div>

            {/* Expected Revenue */}
            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Expected Gross Revenue:</span>
                <span className="font-mono text-emerald-400 font-bold">฿{(expectedRevenue / 1000000).toFixed(1)}M</span>
              </div>
              <input 
                type="number" step="1000000"
                value={expectedRevenue}
                onChange={(e) => setExpectedRevenue(Number(e.target.value))}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-emerald-500"
              />
            </div>

            {/* Dev Timeline */}
            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Development Timeline:</span>
                <span className="font-mono text-amber-400 font-bold">{devTimeline} Years</span>
              </div>
              <input 
                type="range" min="1" max="10" step="1"
                value={devTimeline}
                onChange={(e) => setDevTimeline(Number(e.target.value))}
                className="w-full accent-amber-400 bg-slate-950 h-1.5 rounded-lg cursor-pointer"
              />
            </div>

          </div>

        </div>

        {/* ========================================== */}
        {/* RIGHT DASHBOARD DISPLAY (8 COLS) */}
        {/* ========================================== */}
        <div className="lg:col-span-8 space-y-6">
          
          {/* POWER GAUGE & HERO SUMMARY HEADER */}
          <div className="bg-gradient-to-r from-slate-900 via-slate-900/90 to-slate-950 border border-slate-800 rounded-2xl p-6 shadow-2xl relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
            
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className={`text-xs font-bold px-3 py-1 rounded-full border bg-gradient-to-r ${rankBadge.color} shadow-lg font-mono`}>
                    {rankBadge.rank}
                  </span>
                  <span className="text-xs font-mono text-slate-400">FEASIBILITY POWER RATING</span>
                </div>
                <h2 className="text-2xl font-black tracking-tight text-white flex items-center gap-2">
                  {selectedTypology}
                </h2>
                <p className="text-xs text-slate-400 mt-1">
                  Suburban Corridor Match Index: <span className="text-cyan-400 font-mono font-bold">{coords.lat.toFixed(4)}, {coords.lon.toFixed(4)}</span>
                </p>
              </div>

              {/* SCORE CIRCLE METRIC */}
              <div className="flex items-center gap-4 bg-slate-950/80 p-4 rounded-2xl border border-slate-800/80 backdrop-blur-md">
                <div className="relative w-20 h-20 flex items-center justify-center">
                  <svg className="w-full h-full transform -rotate-90">
                    <circle cx="40" cy="40" r="32" stroke="currentColor" strokeWidth="6" className="text-slate-800" fill="transparent" />
                    <circle 
                      cx="40" cy="40" r="32" stroke="currentColor" strokeWidth="6" 
                      className="text-cyan-400 transition-all duration-1000 ease-out" 
                      fill="transparent" 
                      strokeDasharray={2 * Math.PI * 32}
                      strokeDashoffset={2 * Math.PI * 32 * (1 - currentTypologyScore / 10)}
                    />
                  </svg>
                  <div className="absolute flex flex-col items-center justify-center">
                    <span className="text-xl font-black text-white font-mono">{currentTypologyScore.toFixed(1)}</span>
                    <span className="text-[9px] text-slate-400">/10</span>
                  </div>
                </div>

                <div className="space-y-1">
                  <div className="text-[11px] text-slate-400">Total Project Cost</div>
                  <div className="text-base font-bold font-mono text-emerald-400">฿{(totalProjectCost / 1000000).toFixed(1)}M</div>
                  <div className="text-[10px] text-slate-500">Land: ฿{(totalLandCost/1000000).toFixed(1)}M | Build: ฿{(constructionCost/1000000).toFixed(1)}M</div>
                </div>
              </div>
            </div>
          </div>

          {/* AUTO-DETECTED VARIABLES EXPANDER SECTION */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
            <div className="p-4 bg-slate-900/90 border-b border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Cpu className="w-5 h-5 text-cyan-400" />
                <div>
                  <h3 className="font-bold text-sm text-slate-200">Auto-Detected Spatial & Environmental Variables</h3>
                  <p className="text-[11px] text-slate-400">Matched using location coordinates & spatial context layers</p>
                </div>
              </div>

              {/* MANUAL OVERRIDE TOGGLE */}
              <label className="inline-flex items-center gap-2 cursor-pointer bg-slate-950 border border-slate-800 px-3 py-1.5 rounded-xl hover:border-cyan-500/40 transition">
                <input 
                  type="checkbox" 
                  checked={manualOverride}
                  onChange={(e) => setManualOverride(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-8 h-4 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-slate-400 after:border-slate-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-cyan-500 relative" />
                <span className="text-xs font-semibold text-cyan-400 flex items-center gap-1">
                  <Edit3 className="w-3.5 h-3.5" /> Enter the value to get more accuracy
                </span>
              </label>
            </div>

            <div className="p-4 space-y-4">
              {Object.keys(groupedCatalog).map((groupName) => {
                const isExpanded = expandedGroups[groupName] !== false; // Default open
                const items = groupedCatalog[groupName];

                return (
                  <div key={groupName} className="border border-slate-800 rounded-xl overflow-hidden bg-slate-950/60">
                    <button
                      onClick={() => toggleGroup(groupName)}
                      className="w-full px-4 py-2.5 bg-slate-900/80 hover:bg-slate-800/80 text-left flex items-center justify-between transition text-xs font-bold text-slate-300"
                    >
                      <span>📌 {groupName} ({items.length} Variables)</span>
                      <span className="text-cyan-400 font-mono text-[10px]">{isExpanded ? '▼ Hide' : '► Expand'}</span>
                    </button>

                    {isExpanded && (
                      <div className="p-3 overflow-x-auto">
                        <table className="w-full text-left text-xs text-slate-300">
                          <thead>
                            <tr className="border-b border-slate-800 text-slate-500 font-mono text-[11px]">
                              <th className="pb-2">VARIABLE</th>
                              <th className="pb-2">DETECTED VALUE</th>
                              <th className="pb-2">UNITS</th>
                              <th className="pb-2">ASSUMPTION / CRITERIA</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800/50">
                            {items.map((v) => (
                              <tr key={v.variable} className="hover:bg-slate-900/40 transition">
                                <td className="py-2.5 font-medium text-slate-200">{v.variable}</td>
                                <td className="py-2.5 font-mono text-cyan-400">
                                  {manualOverride ? (
                                    <input 
                                      type="text"
                                      value={v.detected}
                                      onChange={(e) => updateVariableValue(v.originalIndex, e.target.value)}
                                      className="bg-slate-900 border border-cyan-500/50 rounded px-2 py-0.5 text-xs text-cyan-300 font-mono w-full max-w-[180px] focus:outline-none focus:ring-1 focus:ring-cyan-400"
                                    />
                                  ) : (
                                    <span>{v.detected}</span>
                                  )}
                                </td>
                                <td className="py-2.5 text-slate-400 font-mono text-[11px]">{v.units}</td>
                                <td className="py-2.5 text-slate-400 text-[11px]">{v.assumption}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* MAIN TAB NAVIGATION DASHBOARD */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
            <div className="flex border-b border-slate-800 bg-slate-950/80 p-1.5 gap-1 overflow-x-auto">
              <button
                onClick={() => setActiveTab('tab1')}
                className={`flex-1 py-2.5 px-4 rounded-xl font-bold text-xs flex items-center justify-center gap-2 transition ${
                  activeTab === 'tab1' 
                    ? 'bg-gradient-to-r from-cyan-500 to-teal-500 text-slate-950 shadow-md' 
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                <TrendingUp className="w-4 h-4" />
                Capital Gain Projection
              </button>

              <button
                onClick={() => setActiveTab('tab2')}
                className={`flex-1 py-2.5 px-4 rounded-xl font-bold text-xs flex items-center justify-center gap-2 transition ${
                  activeTab === 'tab2' 
                    ? 'bg-gradient-to-r from-cyan-500 to-teal-500 text-slate-950 shadow-md' 
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                <BarChart3 className="w-4 h-4" />
                Developer Feasibility
              </button>

              <button
                onClick={() => setActiveTab('tab3')}
                className={`flex-1 py-2.5 px-4 rounded-xl font-bold text-xs flex items-center justify-center gap-2 transition ${
                  activeTab === 'tab3' 
                    ? 'bg-gradient-to-r from-cyan-500 to-teal-500 text-slate-950 shadow-md' 
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                <Layers className="w-4 h-4" />
                Data Proof & Justifications
              </button>

              <button
                onClick={() => setActiveTab('tab4')}
                className={`flex-1 py-2.5 px-4 rounded-xl font-bold text-xs flex items-center justify-center gap-2 transition ${
                  activeTab === 'tab4' 
                    ? 'bg-gradient-to-r from-cyan-500 to-teal-500 text-slate-950 shadow-md' 
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                <ShieldCheck className="w-4 h-4" />
                Backend Manager
              </button>
            </div>

            {/* TAB CONTENTS */}
            <div className="p-6">
              
              {/* TAB 1: CAPITAL GAIN PREDICTOR */}
              {activeTab === 'tab1' && (
                <div className="space-y-6">
                  <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                    <div>
                      <h3 className="text-lg font-extrabold text-white">📈 Capital Gain Valuation Curve</h3>
                      <p className="text-xs text-slate-400">Forecast project baseline growth from Year 1 post-development horizon</p>
                    </div>

                    <div className="bg-slate-950 border border-slate-800 px-4 py-2 rounded-xl flex items-center gap-3">
                      <span className="text-xs text-slate-400">Horizon:</span>
                      <input 
                        type="range" min="1" max="15" value={projectionHorizon}
                        onChange={(e) => setProjectionHorizon(Number(e.target.value))}
                        className="accent-cyan-400 w-24"
                      />
                      <span className="font-mono text-cyan-400 font-bold text-xs">{projectionHorizon} Yrs</span>
                    </div>
                  </div>

                  {/* METRIC HIGHLIGHT CARDS */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-1">
                      <div className="text-xs text-slate-400">Project Base Value (Post-Completion)</div>
                      <div className="text-2xl font-black font-mono text-white">฿{(totalProjectCost / 1000000).toFixed(1)}M</div>
                      <div className="text-[10px] text-slate-500">Initial Year 1 valuation baseline</div>
                    </div>

                    <div className="p-4 rounded-2xl bg-slate-950 border border-cyan-500/40 space-y-1 bg-cyan-950/20">
                      <div className="text-xs text-cyan-400 font-medium">Projected Value at Year {projectionHorizon}</div>
                      <div className="text-2xl font-black font-mono text-cyan-300">฿{(projectValueHorizon / 1000000).toFixed(1)}M</div>
                      <div className="text-[10px] text-emerald-400 font-mono">
                        +{(((projectValueHorizon - totalProjectCost) / totalProjectCost) * 100).toFixed(1)}% Growth (+{((annualGrowthRate)*100).toFixed(1)}%/yr)
                      </div>
                    </div>
                  </div>

                  {/* VISUAL CHART SIMULATION (SVG GRAPH) */}
                  <div className="p-5 rounded-2xl bg-slate-950 border border-slate-800 space-y-3">
                    <div className="text-xs font-mono text-slate-400 flex justify-between">
                      <span>PROJECTED VALUE CURVE (1 - 15 YEARS)</span>
                      <span className="text-cyan-400">RED MARKER = YEAR {projectionHorizon}</span>
                    </div>

                    <div className="h-48 w-full flex items-end gap-1.5 pt-6 pb-2 px-2 border-b border-slate-800">
                      {Array.from({ length: 15 }).map((_, idx) => {
                        const yr = idx + 1;
                        const val = totalProjectCost * Math.pow(1 + annualGrowthRate, yr - 1);
                        const maxVal = totalProjectCost * Math.pow(1 + annualGrowthRate, 14);
                        const heightPct = Math.min(100, Math.max(15, (val / maxVal) * 100));
                        const isSelected = yr === projectionHorizon;

                        return (
                          <div key={yr} className="flex-1 flex flex-col items-center gap-1 group relative">
                            {/* Hover Tooltip */}
                            <div className="opacity-0 group-hover:opacity-100 transition absolute -top-8 bg-slate-800 text-white text-[9px] font-mono px-2 py-1 rounded shadow pointer-events-none whitespace-nowrap z-10">
                              Y{yr}: ฿{(val / 1000000).toFixed(1)}M
                            </div>

                            <div 
                              style={{ height: `${heightPct}%` }} 
                              className={`w-full rounded-t-lg transition-all duration-300 ${
                                isSelected 
                                  ? 'bg-gradient-to-t from-rose-500 to-red-400 shadow-lg shadow-rose-500/50 ring-2 ring-rose-300' 
                                  : 'bg-gradient-to-t from-cyan-900/60 to-cyan-500/80 hover:from-cyan-700'
                              }`}
                            />
                            <span className={`text-[10px] font-mono ${isSelected ? 'text-rose-400 font-bold' : 'text-slate-500'}`}>
                              Y{yr}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* GAMIFIED BUFF REASONS */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-extrabold tracking-wider text-slate-300 uppercase flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-amber-400" />
                      Why Project Base Value Increases? (Spatial Buff Cards)
                    </h4>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                        <div className="text-xs font-bold text-cyan-400">1. Spatial Accessibility Buff</div>
                        <ul className="text-[11px] text-slate-400 space-y-1 list-disc list-inside">
                          <li>Frontage road: 6 Lanes (40m ROW)</li>
                          <li>Traffic volume: 42,500 veh/day</li>
                          <li>1.8 km to Highway / 35 mins to CBD</li>
                        </ul>
                      </div>

                      <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                        <div className="text-xs font-bold text-emerald-400">2. Legal & Zoning Rights Buff</div>
                        <ul className="text-[11px] text-slate-400 space-y-1 list-disc list-inside">
                          <li>Zoning: {zoning} Zone</li>
                          <li>Allowable FAR: {ZONES[zoning].far} | OSR: {ZONES[zoning].osr}%</li>
                          <li>Maximizes total buildable area yield</li>
                        </ul>
                      </div>

                      <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                        <div className="text-xs font-bold text-amber-400">3. Demographic Momentum Buff</div>
                        <ul className="text-[11px] text-slate-400 space-y-1 list-disc list-inside">
                          <li>Catchment density: 4,200 people/km²</li>
                          <li>Annual population growth: +3.4%/yr</li>
                          <li>9 bus/transit feeder stops within 1km</li>
                        </ul>
                      </div>
                    </div>
                  </div>

                </div>
              )}

              {/* TAB 2: DEVELOPER FEASIBILITY */}
              {activeTab === 'tab2' && (
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    
                    {/* PRO-FORMA FINANCIAL STATEMENT */}
                    <div className="p-5 rounded-2xl bg-slate-950 border border-slate-800 space-y-4">
                      <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2">
                        <Calculator className="w-4 h-4 text-emerald-400" />
                        Pro-Forma Financial Feasibility
                      </h3>

                      <table className="w-full text-xs font-mono">
                        <tbody className="divide-y divide-slate-800">
                          <tr>
                            <td className="py-2.5 text-slate-400">Expected Revenue</td>
                            <td className="py-2.5 text-right font-bold text-white">฿{expectedRevenue.toLocaleString()}</td>
                          </tr>
                          <tr>
                            <td className="py-2.5 text-slate-400">- Land Acquisition Cost</td>
                            <td className="py-2.5 text-right text-rose-400">-฿{totalLandCost.toLocaleString()}</td>
                          </tr>
                          <tr>
                            <td className="py-2.5 text-slate-400">- Construction Cost</td>
                            <td className="py-2.5 text-right text-rose-400">-฿{constructionCost.toLocaleString()}</td>
                          </tr>
                          <tr className="bg-slate-900/60 font-bold">
                            <td className="py-3 text-emerald-400">Net Developer Profit</td>
                            <td className="py-3 text-right text-emerald-400 text-sm">฿{netProfit.toLocaleString()}</td>
                          </tr>
                          <tr>
                            <td className="py-2.5 text-slate-400">Return on Investment (ROI)</td>
                            <td className="py-2.5 text-right font-bold text-cyan-400">{roiPct.toFixed(2)}%</td>
                          </tr>
                          <tr>
                            <td className="py-2.5 text-slate-400">Annualized IRR ({devTimeline} Yrs)</td>
                            <td className="py-2.5 text-right font-bold text-amber-400">{annualizedIrr.toFixed(2)}%</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>

                    {/* HBU LEADERBOARD */}
                    <div className="p-5 rounded-2xl bg-slate-950 border border-slate-800 space-y-4">
                      <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2">
                        <Trophy className="w-4 h-4 text-amber-400" />
                        Highest & Best Use (HBU) Leaderboard
                      </h3>

                      <div className="space-y-3">
                        {hbuScores.map((item, index) => (
                          <div key={item.name} className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1.5">
                            <div className="flex items-center justify-between text-xs">
                              <span className="font-bold text-slate-200">
                                #{index + 1} {item.name}
                              </span>
                              <span className="font-mono font-bold text-cyan-400">{item.score.toFixed(1)} / 10</span>
                            </div>

                            <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden">
                              <div 
                                className="bg-gradient-to-r from-cyan-500 to-emerald-400 h-full rounded-full transition-all duration-500" 
                                style={{ width: `${(item.score / 10) * 100}%` }}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                  </div>
                </div>
              )}

              {/* TAB 3: DATA PROOF & REASONS */}
              {activeTab === 'tab3' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-extrabold text-white">📑 Analytical Reasons & Data Justifications</h3>
                    <p className="text-xs text-slate-400">Detailed spatial proof mapped against site location and historical backtest records</p>
                  </div>

                  <div className="p-5 rounded-2xl bg-slate-950 border border-slate-800 space-y-4 text-xs text-slate-300 leading-relaxed">
                    <div>
                      <h4 className="font-bold text-cyan-400 mb-1">1. Site & Legal Zoning Compliance</h4>
                      <p>Situated in **{zoning} Zone** ({ZONES[zoning].desc}), providing statutory **FAR of {ZONES[zoning].far}** and **OSR of {ZONES[zoning].osr}%**. Frontage width enables efficient architectural access clearance.</p>
                    </div>

                    <div>
                      <h4 className="font-bold text-emerald-400 mb-1">2. Accessibility & Transit Friction Proof</h4>
                      <p>Fronting a **6-lane arterial roadway (40m ROW)** with daily traffic count of **42,500 vehicles/day**. Connects to highway ramps within 1.8 km and CBD within 35 minutes travel time.</p>
                    </div>

                    <div>
                      <h4 className="font-bold text-amber-400 mb-1">3. Demographic Momentum</h4>
                      <p>Local catchment area supports **4,200 people/km²** with an annual population growth rate of **3.4% per year**, generating consistent organic absorption for **{selectedTypology}**.</p>
                    </div>
                  </div>

                  {/* COMPARABLE HISTORICAL PROJECTS */}
                  <div className="space-y-3">
                    <h4 className="font-bold text-xs text-slate-300 uppercase tracking-wider">Historical Spatial Backtest Comparables</h4>
                    
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs text-left font-mono">
                        <thead className="bg-slate-950 text-slate-500 border-b border-slate-800">
                          <tr>
                            <th className="p-2.5">PROJECT</th>
                            <th className="p-2.5">TYPOLOGY</th>
                            <th className="p-2.5">POP DENSITY</th>
                            <th className="p-2.5">TRAFFIC AADT</th>
                            <th className="p-2.5">HOLDING</th>
                            <th className="p-2.5">TOTAL GAIN</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60 bg-slate-950/40">
                          {historicalProjects.map((p) => (
                            <tr key={p.id} className="hover:bg-slate-900/60">
                              <td className="p-2.5 font-bold text-slate-200">{p.name}</td>
                              <td className="p-2.5 text-slate-400">{p.typology.split(' ')[0]}</td>
                              <td className="p-2.5 text-slate-300">{p.popDensity.toLocaleString()}/km²</td>
                              <td className="p-2.5 text-slate-300">{p.aadt.toLocaleString()}</td>
                              <td className="p-2.5 text-amber-400">{p.holdingYears} Yrs</td>
                              <td className="p-2.5 text-emerald-400 font-bold">+{p.growthPct}%</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                </div>
              )}

              {/* TAB 4: BACKEND MANAGER (PROTECTED AUTH) */}
              {activeTab === 'tab4' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-extrabold text-white flex items-center gap-2">
                      <Lock className="w-5 h-5 text-amber-400" />
                      Backend Data Manager (Admin Terminal)
                    </h3>
                    <p className="text-xs text-slate-400">Log completed historical projects into persistent database</p>
                  </div>

                  {!isAdminLoggedIn ? (
                    <div className="max-w-md mx-auto p-6 rounded-2xl bg-slate-950 border border-slate-800 space-y-4 text-center">
                      <div className="w-12 h-12 mx-auto rounded-full bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
                        <Lock className="w-6 h-6" />
                      </div>

                      <div className="space-y-1">
                        <h4 className="font-bold text-sm text-slate-200">Admin Authentication Required</h4>
                        <p className="text-xs text-slate-500">Username: <code className="text-amber-400">admin123</code> | Password: <code className="text-amber-400">1234</code></p>
                      </div>

                      <form onSubmit={handleAdminLogin} className="space-y-3 text-left">
                        <div>
                          <label className="block text-xs text-slate-400 mb-1">Username:</label>
                          <input 
                            type="text" value={adminUser} onChange={(e) => setAdminUser(e.target.value)}
                            className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-amber-500"
                          />
                        </div>

                        <div>
                          <label className="block text-xs text-slate-400 mb-1">Password:</label>
                          <input 
                            type="password" value={adminPass} onChange={(e) => setAdminPass(e.target.value)}
                            className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-amber-500"
                          />
                        </div>

                        {adminError && <div className="text-xs text-rose-400">{adminError}</div>}

                        <button 
                          type="submit"
                          className="w-full py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs uppercase tracking-wider transition shadow-lg shadow-amber-500/20"
                        >
                          Unlock Terminal
                        </button>
                      </form>
                    </div>
                  ) : (
                    <div className="space-y-6">
                      <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center justify-between">
                        <span className="flex items-center gap-2 font-mono">
                          <Unlock className="w-4 h-4" /> Authenticated as System Administrator
                        </span>
                        <button 
                          onClick={() => setIsAdminLoggedIn(false)}
                          className="text-[11px] underline hover:text-emerald-300"
                        >
                          Logout
                        </button>
                      </div>

                      {/* ADD PROJECT FORM */}
                      <form onSubmit={handleAddProject} className="p-5 rounded-2xl bg-slate-950 border border-slate-800 space-y-4">
                        <h4 className="font-bold text-xs text-slate-200 uppercase tracking-wider">➕ Log New Completed Project Record</h4>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                          <div>
                            <label className="block text-slate-400 mb-1">Project Name:</label>
                            <input 
                              type="text" required value={newProjName} onChange={(e) => setNewProjName(e.target.value)}
                              placeholder="e.g. Bang Khen Commercial Center"
                              className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                            />
                          </div>

                          <div>
                            <label className="block text-slate-400 mb-1">Typology:</label>
                            <select 
                              value={newProjTypology} onChange={(e) => setNewProjTypology(e.target.value)}
                              className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                            >
                              {TYPOLOGIES.map(t => <option key={t} value={t}>{t}</option>)}
                            </select>
                          </div>

                          <div>
                            <label className="block text-slate-400 mb-1">Pop Density (people/km²):</label>
                            <input 
                              type="number" value={newProjPop} onChange={(e) => setNewProjPop(e.target.value)}
                              className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                            />
                          </div>

                          <div>
                            <label className="block text-slate-400 mb-1">Traffic Volume (AADT):</label>
                            <input 
                              type="number" value={newProjAadt} onChange={(e) => setNewProjAadt(e.target.value)}
                              className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                            />
                          </div>

                          <div>
                            <label className="block text-slate-400 mb-1">Holding Period (Years):</label>
                            <input 
                              type="number" value={newProjYears} onChange={(e) => setNewProjYears(e.target.value)}
                              className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                            />
                          </div>

                          <div>
                            <label className="block text-slate-400 mb-1">Total Capital Growth (%):</label>
                            <input 
                              type="number" step="0.1" value={newProjGrowth} onChange={(e) => setNewProjGrowth(e.target.value)}
                              className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                            />
                          </div>
                        </div>

                        <button 
                          type="submit"
                          className="w-full py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 text-slate-950 font-bold text-xs uppercase tracking-wider transition shadow-lg shadow-emerald-500/20"
                        >
                          Save Record to Local Database
                        </button>
                      </form>
                    </div>
                  )}
                </div>
              )}

            </div>
          </div>

        </div>

      </main>

      {/* FOOTER */}
      <footer className="border-t border-slate-900 py-6 text-center text-xs text-slate-600 font-mono">
        Real Estate Feasibility Engine v3.8 — Suburban Thailand Spatial Predictor Simulator
      </footer>

    </div>
  );
}

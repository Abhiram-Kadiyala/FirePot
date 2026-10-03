from pathlib import Path
import io
import math
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from algorithms.graph import build_graph
from algorithms.greedy import greedy_station_placement
from algorithms.dijkstra import shortest_path
from utils.coverage import calculate_coverage
from utils.visualization import build_map

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

st.set_page_config(page_title="FIREOPT", page_icon="🔥", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
:root { --red:#ef4444; --navy:#07111f; --panel:#0e1b2d; --muted:#9fb0c3; }
.stApp { background: radial-gradient(circle at 10% 0%, #18263b 0%, #08111f 38%, #050a12 100%); color:#f8fafc; }
.block-container { max-width: 1450px; padding-top: 1.1rem; padding-bottom: 3rem; }
[data-testid="stSidebar"] { background:#07111f; border-right:1px solid #1f334f; }
.hero { padding:28px 30px; border-radius:24px; background:linear-gradient(120deg, rgba(239,68,68,.18), rgba(10,20,35,.94) 45%, rgba(22,40,65,.88)); border:1px solid rgba(255,255,255,.09); box-shadow:0 18px 55px rgba(0,0,0,.28); margin-bottom:18px; }
.hero h1 { font-size:3.15rem; line-height:1; margin:0; letter-spacing:-2px; }
.hero h2 { font-size:1rem; letter-spacing:2px; margin:.65rem 0; color:#fca5a5; }
.hero p { font-size:1.55rem; line-height:1.25; margin:.9rem 0 .3rem; font-weight:700; }
.badge { display:inline-block; margin-top:12px; padding:7px 12px; border:1px solid #7f1d1d; border-radius:999px; color:#fecaca; font-size:.78rem; font-weight:700; letter-spacing:.8px; }
.kpi { background:linear-gradient(180deg,#102036,#0a1627); border:1px solid #203753; padding:17px; border-radius:18px; min-height:108px; box-shadow:0 10px 25px rgba(0,0,0,.18); }
.kpi .label { color:#9fb0c3; font-size:.84rem; }
.kpi .value { font-size:1.8rem; font-weight:800; margin-top:4px; }
.section-card { background:rgba(12,25,43,.82); border:1px solid #1f3652; border-radius:20px; padding:18px; margin:10px 0 18px; }
.pipeline { display:grid; grid-template-columns:repeat(6,1fr); gap:8px; align-items:stretch; }
.pipe { padding:13px 8px; background:#0e1d31; border:1px solid #203a59; border-radius:14px; text-align:center; font-size:.84rem; }
.pipe strong { display:block; color:#fca5a5; margin-bottom:5px; }
.result { border:1px solid #7f1d1d; background:linear-gradient(140deg,rgba(127,29,29,.22),rgba(12,25,43,.9)); border-radius:22px; padding:22px; }
.small-muted { color:#9fb0c3; font-size:.88rem; }
div[data-testid="stMetric"] { background:#0d1b2d; border:1px solid #1f3652; border-radius:16px; padding:12px; }
.stButton>button { border-radius:12px; font-weight:700; }
</style>
""", unsafe_allow_html=True)


def load_demo():
    return pd.read_csv(DATA_DIR / "neighborhoods.csv"), pd.read_csv(DATA_DIR / "roads.csv")


def validate_data(n_df, r_df):
    if n_df is None or r_df is None or n_df.empty or r_df.empty:
        raise ValueError("Dataset is empty. Please provide both neighborhoods and roads.")
    needed_n = {"id", "name", "latitude", "longitude"}
    needed_r = {"from", "to", "time"}
    miss_n = needed_n - set(n_df.columns)
    miss_r = needed_r - set(r_df.columns)
    if miss_n:
        raise ValueError(f"Neighborhood file is missing columns: {', '.join(sorted(miss_n))}")
    if miss_r:
        raise ValueError(f"Road file is missing columns: {', '.join(sorted(miss_r))}")
    n_df = n_df.copy()
    r_df = r_df.copy()
    n_df["id"] = n_df["id"].astype(str).str.strip()
    n_df["name"] = n_df["name"].astype(str).str.strip()
    r_df["from"] = r_df["from"].astype(str).str.strip()
    r_df["to"] = r_df["to"].astype(str).str.strip()
    if n_df["id"].duplicated().any():
        raise ValueError("Duplicate neighborhood IDs were found.")
    for c in ["latitude", "longitude"]:
        n_df[c] = pd.to_numeric(n_df[c], errors="coerce")
    r_df["time"] = pd.to_numeric(r_df["time"], errors="coerce")
    if n_df[["latitude","longitude"]].isna().any().any():
        raise ValueError("Latitude/longitude values must be valid numbers.")
    if r_df["time"].isna().any() or (r_df["time"] <= 0).any():
        raise ValueError("Every road time must be a positive number.")
    valid = set(n_df["id"])
    bad = r_df[~r_df["from"].isin(valid) | ~r_df["to"].isin(valid)]
    if not bad.empty:
        raise ValueError("One or more roads reference a neighborhood ID that does not exist.")
    return n_df, r_df


def initialize_state():
    defaults = {
        "stations": [], "decision_log": [], "coverage_cache": {}, "greedy_stats": {},
        "coverage": None, "route": [], "route_result": None, "route_steps": [],
        "optimized": False, "explain": False, "gap_analysis": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_results():
    for k, v in {
        "stations": [], "decision_log": [], "coverage_cache": {}, "greedy_stats": {},
        "coverage": None, "route": [], "route_result": None, "route_steps": [],
        "optimized": False, "explain": False, "gap_analysis": False,
    }.items():
        st.session_state[k] = v


def run_optimization(graph, station_count, target_time):
    selected, log, cache, stats = greedy_station_placement(graph, station_count, target_time)
    cov = calculate_coverage(graph, selected, target_time)
    st.session_state.stations = selected
    st.session_state.decision_log = log
    st.session_state.coverage_cache = cache
    st.session_state.greedy_stats = stats
    st.session_state.coverage = cov
    st.session_state.route = []
    st.session_state.route_result = None
    st.session_state.route_steps = []
    st.session_state.optimized = True
    st.session_state.explain = False
    st.session_state.gap_analysis = False


def kpi_card(label, value):
    st.markdown(f'<div class="kpi"><div class="label">{label}</div><div class="value">{value}</div></div>', unsafe_allow_html=True)

initialize_state()

st.markdown("""
<div class="hero">
  <h1>🔥 FIREOPT</h1>
  <h2>INTELLIGENT FIRE STATION PLACEMENT & EMERGENCY COVERAGE OPTIMIZATION</h2>
  <p>Place Smarter.<br>Respond Faster.<br>Save More.</p>
  <span class="badge">DAA • GREEDY • DIJKSTRA • GRAPH OPTIMIZATION</span>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 🎛️ Control Center")
    presentation_mode = st.toggle("🎤 Presentation Mode", value=False)
    dataset_mode = st.selectbox("Dataset", ["Demo City", "Upload CSV"])
    uploaded_n = uploaded_r = None
    if dataset_mode == "Upload CSV":
        uploaded_n = st.file_uploader("Neighborhoods CSV", type=["csv"])
        uploaded_r = st.file_uploader("Roads CSV", type=["csv"])
    station_count = st.slider("🔥 Number of stations", 1, 5, 3)
    target_time = st.slider("⏱️ Target response time", 3, 15, 8, 1)
    optimize = st.button("🚀 Optimize Placement", use_container_width=True, type="primary")
    demo = st.button("🎬 Run Demo", use_container_width=True)
    reset = st.button("🔄 Reset", use_container_width=True)
    st.divider()
    st.caption("Demo / Simulation Dataset — not real-world emergency data.")

if reset:
    reset_results()
    st.rerun()

try:
    if dataset_mode == "Demo City" or demo:
        n_df, r_df = load_demo()
    else:
        if uploaded_n is None or uploaded_r is None:
            st.info("Upload both `neighborhoods.csv` and `roads.csv` to use a custom dataset.")
            st.stop()
        n_df = pd.read_csv(uploaded_n)
        r_df = pd.read_csv(uploaded_r)
    n_df, r_df = validate_data(n_df, r_df)
    graph = build_graph(n_df, r_df)
except Exception as exc:
    st.error(f"Dataset error: {exc}")
    st.stop()

if station_count > len(n_df):
    station_count = len(n_df)
    st.warning("Station count exceeded available neighborhoods and was reduced automatically.")

if demo:
    with st.status("Running FIREOPT demo...", expanded=True) as status:
        st.write("1. Loading city network...")
        st.write("2. Building graph...")
        st.write("3. Running Dijkstra coverage calculations...")
        st.write("4. Calculating coverage...")
        st.write("5. Running Greedy placement...")
        st.write("6. Selecting stations...")
        run_optimization(graph, station_count, target_time)
        st.write("7. Generating final coverage...")
        status.update(label="Demo complete", state="complete")

if optimize:
    run_optimization(graph, station_count, target_time)

if not st.session_state.optimized:
    run_optimization(graph, station_count, target_time)

# Recompute when sliders changed so scenario always reflects controls.
if len(st.session_state.stations) != min(station_count, len(n_df)):
    run_optimization(graph, station_count, target_time)
else:
    # Detect target changes by checking cached station coverage against fresh optimization.
    # Cheap enough for 25-node demo and keeps UI genuinely dynamic.
    fresh_sel, fresh_log, fresh_cache, fresh_stats = greedy_station_placement(graph, station_count, target_time)
    if fresh_sel != st.session_state.stations:
        run_optimization(graph, station_count, target_time)
    else:
        st.session_state.decision_log = fresh_log
        st.session_state.coverage_cache = fresh_cache
        st.session_state.greedy_stats = fresh_stats
        st.session_state.coverage = calculate_coverage(graph, st.session_state.stations, target_time)

cov = st.session_state.coverage
stations = st.session_state.stations

c1, c2, c3, c4, c5 = st.columns(5)
with c1: kpi_card("🏘️ Total Neighborhoods", cov["total"])
with c2: kpi_card("🔥 Fire Stations", len(stations))
with c3: kpi_card("🛡️ Coverage", f'{cov["coverage_pct"]:.1f}%')
with c4: kpi_card("⏱️ Avg Response", "—" if not math.isfinite(cov["avg_response"]) else f'{cov["avg_response"]:.1f} min')
with c5: kpi_card("⚠️ Uncovered Areas", cov["uncovered"])

st.markdown("### 🗺️ Emergency Coverage Map")
map_height = 720 if presentation_mode else 610
folium_map = build_map(n_df, r_df, cov, stations, st.session_state.route, height=map_height)
st_folium(folium_map, width=None, height=map_height, returned_objects=[])

if presentation_mode:
    st.markdown("### 🏆 Optimization Snapshot")
    a,b,c = st.columns(3)
    a.metric("Recommended Stations", ", ".join(stations))
    b.metric("Coverage", f'{cov["covered"]}/{cov["total"]} ({cov["coverage_pct"]:.1f}%)')
    c.metric("Target", f"≤ {target_time} min")
    if st.session_state.decision_log:
        st.markdown("### 🧠 Key Greedy Decisions")
        present_rows = [{"Step": x["step"], "Selected": x["selected"], "New Coverage": x["new_coverage"], "Covered After": x["covered_after"]} for x in st.session_state.decision_log]
        st.dataframe(pd.DataFrame(present_rows), hide_index=True, use_container_width=True)
    st.stop()

st.markdown("### 🧠 Why were these stations selected?")
summary_rows = [{"Step": x["step"], "Candidate": x["selected"], "New Coverage": f'+{x["new_coverage"]}', "Decision": "🔥 Selected"} for x in st.session_state.decision_log]
st.dataframe(pd.DataFrame(summary_rows), hide_index=True, use_container_width=True)
with st.expander("🔍 View all candidate calculations"):
    all_rows = []
    for step in st.session_state.decision_log:
        for row in step["candidates"]:
            all_rows.append({"Step": row["step"], "Candidate": row["candidate"], "New Coverage": row["new_coverage"], "Coverage if selected": row["total_coverage_if_selected"], "Decision": "Selected" if row["candidate"] == step["selected"] else "Considered"})
    st.dataframe(pd.DataFrame(all_rows), hide_index=True, use_container_width=True)

if st.button("🧠 Explain My Decision"):
    st.session_state.explain = True
if st.session_state.explain:
    for step in st.session_state.decision_log:
        st.info(f"Step {step['step']}: **{step['selected']}** was selected because it provided the maximum additional coverage among the remaining candidates, adding **{step['new_coverage']}** currently uncovered neighborhoods within the **{target_time}-minute** target. Algorithm: **Greedy + Dijkstra**.")

st.markdown("### 🚒 Emergency Route Explorer")
r1, r2, r3 = st.columns([1,1,.8])
with r1:
    route_station = st.selectbox("Select Fire Station", stations, key="route_station")
with r2:
    route_dest = st.selectbox("Select Destination", list(n_df["id"].astype(str)), key="route_destination")
with r3:
    st.write("")
    st.write("")
    find_route = st.button("Find Shortest Route", use_container_width=True)

if find_route:
    if route_station == route_dest:
        st.session_state.route = [route_station]
        st.session_state.route_result = (0.0, [route_station])
        st.session_state.route_steps = [f"Start and destination are both {route_station}; travel time is 0."]
    else:
        time_value, path, steps = shortest_path(graph, route_station, route_dest)
        st.session_state.route = path
        st.session_state.route_result = (time_value, path)
        st.session_state.route_steps = steps

if st.session_state.route_result:
    rt, path = st.session_state.route_result
    if path and math.isfinite(rt):
        status = "✅ Within Target" if rt <= target_time else "⚠️ Response time exceeds target"
        st.success(f"**Shortest Route:** {' → '.join(path)}  \n\n**Total Response Time:** {rt:.2f} min  |  **Target:** {target_time} min  |  **Status:** {status}")
    else:
        st.warning("No available path exists between the selected station and destination.")
    with st.expander("🔍 How Dijkstra found this route"):
        if st.session_state.route_steps:
            for i, line in enumerate(st.session_state.route_steps, 1):
                st.write(f"{i}. {line}")

st.markdown("### ⚠️ Coverage Gaps")
uncovered_rows = []
for nid, d in cov["details"].items():
    if not d["covered"]:
        uncovered_rows.append({"Neighborhood": nid, "Closest Station": d["closest_station"], "Response Time": "Unreachable" if not math.isfinite(d["time"]) else f'{d["time"]:.1f} min'})
st.write(f"**{cov['uncovered']} neighborhoods** remain outside the target response time.")
if uncovered_rows:
    st.dataframe(pd.DataFrame(uncovered_rows), hide_index=True, use_container_width=True)
else:
    st.success("All neighborhoods are covered within the selected target response time.")

if st.button("💡 Analyze Coverage Gap"):
    st.session_state.gap_analysis = True
if st.session_state.gap_analysis:
    uncovered_set = {nid for nid, d in cov["details"].items() if not d["covered"]}
    if not uncovered_set:
        st.success("No coverage gap remains for this scenario.")
    else:
        best, gain = None, set()
        for candidate, cover_set in st.session_state.coverage_cache.items():
            if candidate in stations:
                continue
            new_gain = cover_set & uncovered_set
            if best is None or len(new_gain) > len(gain):
                best, gain = candidate, new_gain
        if best:
            st.info(f"Adding a station at **{best}** could cover **{len(gain)}** of the currently uncovered neighborhoods within {target_time} minutes: {', '.join(sorted(gain)) if gain else 'none at this target'}.")

st.markdown("### 📊 Impact Analysis — Before vs After")
# Baseline: first neighborhood as a simple single-station reference configuration.
baseline_station = [str(n_df.iloc[0]["id"])]
before = calculate_coverage(graph, baseline_station, target_time)
impact_df = pd.DataFrame({
    "Metric": ["Coverage", "Covered", "Uncovered", "Avg Response"],
    "Before": [f'{before["coverage_pct"]:.1f}%', before["covered"], before["uncovered"], "—" if not math.isfinite(before["avg_response"]) else f'{before["avg_response"]:.1f} min'],
    "After": [f'{cov["coverage_pct"]:.1f}%', cov["covered"], cov["uncovered"], "—" if not math.isfinite(cov["avg_response"]) else f'{cov["avg_response"]:.1f} min'],
})
st.dataframe(impact_df, hide_index=True, use_container_width=True)
st.caption(f"Before = reference configuration with one station at {baseline_station[0]}; After = greedy-optimized {len(stations)}-station configuration.")

st.markdown("### 🔬 What-If Simulator")
scenario_records = []
for k in range(1, min(5, len(n_df)) + 1):
    sel, _, _, _ = greedy_station_placement(graph, k, target_time)
    c = calculate_coverage(graph, sel, target_time)
    scenario_records.append({"Stations": k, "Coverage %": round(c["coverage_pct"], 2)})
scenario_df = pd.DataFrame(scenario_records)
ch1, ch2 = st.columns(2)
with ch1:
    fig = px.line(scenario_df, x="Stations", y="Coverage %", markers=True, title="Coverage vs Number of Stations")
    fig.update_layout(template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)
with ch2:
    time_records = []
    for t in range(3, 16):
        sel, _, _, _ = greedy_station_placement(graph, station_count, t)
        c = calculate_coverage(graph, sel, t)
        time_records.append({"Response Time": t, "Coverage %": round(c["coverage_pct"], 2)})
    time_df = pd.DataFrame(time_records)
    fig = px.line(time_df, x="Response Time", y="Coverage %", markers=True, title="Response Time vs Coverage")
    fig.update_layout(template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

st.markdown("### 📈 Coverage Charts")
c1, c2 = st.columns(2)
station_assignments = {s: 0 for s in stations}
response_times = []
for _, d in cov["details"].items():
    if math.isfinite(d["time"]):
        response_times.append(d["time"])
    if d["closest_station"] in station_assignments:
        station_assignments[d["closest_station"]] += 1
with c1:
    assign_df = pd.DataFrame({"Station": list(station_assignments.keys()), "Assigned Neighborhoods": list(station_assignments.values())})
    fig = px.bar(assign_df, x="Station", y="Assigned Neighborhoods", title="Coverage by Closest Station")
    fig.update_layout(template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)
with c2:
    fig = px.histogram(pd.DataFrame({"Response Time": response_times}), x="Response Time", nbins=10, title="Response Time Distribution")
    fig.update_layout(template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

c3, c4 = st.columns(2)
with c3:
    fig = px.line(scenario_df, x="Stations", y="Coverage %", markers=True, title="Coverage vs Number of Stations")
    fig.update_layout(template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)
with c4:
    pie_df = pd.DataFrame({"Status": ["Covered", "Uncovered"], "Count": [cov["covered"], cov["uncovered"]]})
    fig = px.pie(pie_df, names="Status", values="Count", hole=.58, title="Covered vs Uncovered")
    fig.update_layout(template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

st.markdown("### 🧩 Algorithm Pipeline")
st.markdown("""
<div class="pipeline">
  <div class="pipe"><strong>1</strong>CITY ROAD NETWORK</div>
  <div class="pipe"><strong>2</strong>GRAPH MODEL</div>
  <div class="pipe"><strong>3</strong>DIJKSTRA<br><span class="small-muted">Shortest paths</span></div>
  <div class="pipe"><strong>4</strong>COVERAGE ANALYSIS</div>
  <div class="pipe"><strong>5</strong>GREEDY<br><span class="small-muted">Max new coverage</span></div>
  <div class="pipe"><strong>6</strong>FINAL STATION PLACEMENT</div>
</div>
""", unsafe_allow_html=True)

st.markdown("### 🧮 Algorithm Statistics")
s1,s2,s3,s4,s5,s6 = st.columns(6)
s1.metric("Graph Nodes", len(graph.nodes()))
s2.metric("Graph Edges", graph.edge_count())
s3.metric("Dijkstra Runs", st.session_state.greedy_stats.get("dijkstra_runs", 0) + cov.get("dijkstra_runs", 0))
s4.metric("Greedy Iterations", len(st.session_state.decision_log))
s5.metric("Candidates Evaluated", st.session_state.greedy_stats.get("candidate_evaluations", 0))
s6.metric("Covered", cov["covered"])

st.markdown("### 🏆 Final Optimization Result")
status_text = "✅ Full Target Coverage Achieved" if cov["uncovered"] == 0 else "⚠️ Coverage Gaps Remain"
avg_text = "—" if not math.isfinite(cov["avg_response"]) else f'{cov["avg_response"]:.1f} minutes'
st.markdown(f"""
<div class="result">
  <h3>Recommended Fire Stations</h3>
  <p style="font-size:1.35rem;font-weight:800">🔥 {' &nbsp;&nbsp; 🔥 '.join(stations)}</p>
  <p><b>Coverage:</b> {cov['coverage_pct']:.1f}% &nbsp; • &nbsp; {cov['covered']} / {cov['total']} neighborhoods</p>
  <p><b>Average Response:</b> {avg_text} &nbsp; • &nbsp; <b>Target:</b> {target_time} minutes</p>
  <p><b>Status:</b> {status_text}</p>
</div>
""", unsafe_allow_html=True)

with st.expander("ℹ️ About this prototype"):
    st.write("FIREOPT uses a fictional Demo / Simulation Dataset. It is designed to demonstrate DAA concepts—weighted graphs, Dijkstra shortest paths, path reconstruction and greedy maximum-additional-coverage optimization. It is not an operational emergency dispatch system.")

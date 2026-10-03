# 🔥 FIREOPT
## Intelligent Fire Station Placement & Emergency Coverage Optimization

**Place Smarter. Respond Faster. Save More.**

FIREOPT is a fully functional DAA hackathon prototype that models a city as a weighted graph and recommends fire-station locations that maximize neighborhood coverage within a target emergency response time.

## Problem Statement
Select fire-station locations to maximize reachable neighborhoods within a target response time.

## Motivation
Emergency infrastructure placement is a graph optimization problem: road travel times affect which neighborhoods can be reached quickly, while a limited number of stations makes placement decisions important. FIREOPT demonstrates this with a safe **Demo / Simulation Dataset**; it does not use real emergency-response data.

## Objectives
- Model neighborhoods as graph nodes and roads as weighted edges.
- Implement Dijkstra's shortest path algorithm manually.
- Implement greedy maximum-additional-coverage station placement.
- Compute coverage and response-time metrics dynamically.
- Visualize stations, coverage gaps and routes on an interactive map.
- Provide a presentation-friendly dashboard for hackathon judging.

## Features
- Greedy station placement with candidate-by-candidate decision logs
- Manual Dijkstra implementation with route reconstruction and trace
- Interactive Folium map
- Coverage KPIs and Plotly charts
- Emergency Route Explorer
- Coverage gap analysis
- Before-vs-after impact analysis
- What-if simulator
- Demo mode and Presentation Mode
- CSV upload support with validation

## Algorithms Used
### Graph Representation
Neighborhoods are nodes. Roads are undirected weighted edges. Each edge weight is travel time in minutes.

### Dijkstra in FIREOPT
For a selected station, Dijkstra maintains tentative travel times in a min-heap. It repeatedly chooses the unvisited node with the smallest current distance and relaxes its neighbors. A predecessor table is maintained so the final shortest route can be reconstructed.

Time complexity with a binary heap: **O((V + E) log V)**.

### Greedy Placement in FIREOPT
At each iteration FIREOPT evaluates every remaining candidate neighborhood and measures how many **new, currently uncovered** neighborhoods it can cover within the target response time. The candidate with maximum new coverage is selected, then the process repeats.

If `k` stations are requested and Dijkstra coverage is cached once per candidate, the main placement phase is roughly **O(V · (V+E) log V + kV)** for this implementation.

## Technology Stack
- Python
- Streamlit
- Pandas
- Folium + streamlit-folium
- Plotly
- NetworkX is included as an optional graph utility dependency, while the core Dijkstra logic is implemented manually.

## Project Architecture
```text
fireopt/
├── app.py
├── requirements.txt
├── README.md
├── algorithms/
│   ├── __init__.py
│   ├── graph.py
│   ├── dijkstra.py
│   └── greedy.py
├── data/
│   ├── neighborhoods.csv
│   └── roads.csv
└── utils/
    ├── coverage.py
    └── visualization.py
```

## Dataset Format
`neighborhoods.csv`
```csv
id,name,latitude,longitude
N1,Central,17.4500,78.3800
```

`roads.csv`
```csv
from,to,time
N1,N2,4
```

For upload mode, upload both files using the corresponding file uploaders in the sidebar.

## Installation
```bash
python -m venv .venv
```
Windows:
```bash
.venv\Scripts\activate
```
macOS/Linux:
```bash
source .venv/bin/activate
```
Then:
```bash
pip install -r requirements.txt
```

## Run
```bash
streamlit run app.py
```

## Example Workflow
1. Choose the Demo City dataset.
2. Set the number of stations and target response time.
3. Click **Optimize Placement**.
4. Inspect recommended stations, coverage, greedy decisions and map.
5. Use **Emergency Route Explorer** to inspect a Dijkstra shortest path.
6. Enable **Presentation Mode** for a cleaner judge-facing demo.

## Limitations
- Demo data is fictional and simplified.
- Road travel times are static rather than live traffic estimates.
- Greedy placement is an approximation and does not guarantee a globally optimal set-cover solution.
- This prototype is decision-support/simulation software, not an operational emergency dispatch system.

## Future Enhancements
- Real GIS road-network ingestion
- Traffic-aware dynamic weights
- Capacity and station-cost constraints
- Multi-objective optimization
- Exact/ILP benchmark comparison against greedy
- Accessibility and resilience analysis for blocked roads

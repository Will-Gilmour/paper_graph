# paper_graph Frontend

React application for interactive citation network visualization. Renders papers as nodes and citations as edges on an explorable, GPU-laid-out graph.

## Tech Stack

- **React** – UI framework
- **Vite** – Build tool and dev server
- **Sigma.js** – WebGL graph rendering
- **graphology** – Graph data structures (nodes, edges)
- **react-split** – Resizable sidebar layout
- **react-router-dom** – Routing

## Architecture

The main view is a split layout: a **GraphCanvas** (left) and a **Sidebar** (right). The header holds **SearchBar**, **FilterPanel**, and **GraphSwitcher**. Data flows from the backend API (`VITE_API_URL`); the graph is built incrementally via NDJSON streaming and LOD.

```
App
├── Header (SearchBar, FilterPanel, GraphSwitcher)
├── GraphCanvas  ←── nodes/edges, clusters, filters, POI, recommendations
└── Sidebar      ←── selected paper, clusters, search results, Papers of Interest
```

## Key Components

### GraphCanvas (Main Graph)

The central visualization. Papers are nodes; citation links are edges. Built with **graphology** (in-memory graph) and **Sigma.js** (WebGL renderer).

#### Data Loading

1. **Initial load** – Fetches NDJSON from `/export/initial.ndjson`. Nodes stream in batches of 200 to keep the UI responsive. Optional `top_n` limits how many nodes load (by citation count).
2. **LOD (Level of Detail)** – When zoomed in (camera ratio &lt; 0.5), fetches `/lod/nodes` with viewport bounds (`x_min`, `x_max`, `y_min`, `y_max`). Extra nodes and edges are added so the graph fills the view. When zooming out, those LOD nodes are removed to save memory and keep rendering fast.

#### Node Styling

- **Size** – Log-scaled importance: `citations / (1 + age)^decayFactor`. More cited and newer papers are larger. Capped so very highly cited papers don’t dominate.
- **Color** – One pastel color per cluster (parent cluster ID). Unknown cluster → grey.
- **Filtering** – A `nodeReducer` hides nodes that fail the active filters: cluster selection, year range, min citations.

#### Interactions

- **Hover** – Tooltip with title, authors, year, citations, importance score. Metadata is lazy-loaded from `/paper/{doi}` if missing.
- **Click** – Fetches ego network from `/ego?doi=...&depth=1` and temporarily adds neighbouring papers and edges. Highlights the clicked paper and its immediate neighbours. Click empty space to clear.
- **Search result** – When the user searches, the first result is centred and its ego network is highlighted.

#### Overlays

- **Cluster labels** – Parent (and when zoomed in, sub-) cluster labels are overlaid at cluster centroids. Visibility depends on zoom; collision culling avoids label overlap.

#### Papers of Interest and Recommendations

- **Papers of Interest** – Marked papers get a gold border and larger size. Stored in localStorage.
- **Recommendations** – Suggested papers (from the reading-list API) get a cyan border. POI and recommendations can be loaded into the graph even if they weren’t in the initial set.

---

### Sidebar

Tabs: **Details**, **Clusters**, **Search**, **My Papers**.

- **Details** – Selected paper metadata, add/remove from Papers of Interest, citations and references.
- **Clusters** – Hierarchical list (parent → sub-clusters) with checkboxes. Selection drives `clusterFilter`; only nodes in selected clusters are shown.
- **Search** – Results from header search; click or hover to focus on the graph.
- **My Papers** – Papers of Interest; recommendations; hover to highlight them on the graph.

---

### FilterPanel

- **Year range** – Hide papers outside `year_min`–`year_max`.
- **Min citations** – Hide papers below a citation threshold.
- **Decay factor** – Tunes importance vs. recency (higher = newer papers favoured).
- **Node limit** – Optional cap on how many nodes load initially (persisted in localStorage).

---

### GraphSwitcher

Dropdown to choose the active graph (pipeline run). Changing it reloads the graph for the new run.

---

### PipelineBuildPage

Form at `/admin/build` to configure and submit new pipeline builds (seed DOIs, depth, GPU settings, etc.).

## Concepts

| Concept | Description |
|--------|-------------|
| **Importance score** | `cited_count / (1 + age)^decayFactor` – balances impact and recency |
| **Ego network** | A paper plus its direct neighbours (citations and references) |
| **Papers of Interest** | User-curated set; affects recommendations and graph highlighting |
| **LOD** | Load extra nodes when zoomed in; drop them when zoomed out |

## API Usage

The frontend talks to the backend at `VITE_API_URL`:

- `GET /export/initial.ndjson` – Initial node stream
- `GET /lod/nodes?x_min=...` – LOD nodes in viewport
- `GET /paper/{doi}` – Paper metadata
- `GET /ego?doi=...&depth=1` – Ego network
- `GET /clusters` – Cluster list and metadata
- `GET /labels/parent`, `GET /labels/sub` – Cluster labels
- `GET /find?query=...` – Search
- `GET /reading_list` – Recommendations (uses POI and spatial data)

## Running

### Development (standalone)
```bash
cd frontend
npm install
npm run dev
```

Requires the backend at `http://localhost:8000` (or set `VITE_API_URL` in `.env`).

### Via Docker
See the [root README](../README.md). Frontend runs at http://localhost:5173.

## Tests

### Unit (Vitest)
```bash
cd frontend
npm test -- --run
```

### E2E (Playwright)
```bash
cd frontend
npm run test:e2e
```

# paper_graph Frontend

React application for interactive citation network visualization. Renders papers as nodes and citations as edges on an explorable graph.

## Tech Stack

- **React** – UI framework
- **Vite** – Build tool and dev server
- **Sigma.js** – Graph visualization (WebGL)
- **graphology** – Graph data structures
- **react-split** – Resizable sidebar layout
- **react-router-dom** – Routing

## Main Components

- **GraphCanvas** – Renders the citation graph with Sigma.js; handles zoom, pan, LOD, node highlighting
- **Sidebar** – Paper details, search results, Papers of Interest, recommendations
- **SearchBar** – Free-text and DOI search
- **FilterPanel** – Year range, citation count, decay factor
- **GraphSwitcher** – Select which graph build to view
- **PipelineBuildPage** – Configure and launch new graph builds (`/admin/build`)

## Concepts

- **Graph visualization** – Papers are nodes; citation relationships are edges. Node size reflects importance (citation-weighted).
- **Papers of Interest** – Mark papers to track; stored in localStorage; affects recommendations.
- **Search** – Substring, fuzzy, and spatial search; results highlight on the graph.
- **LOD (Level of Detail)** – At low zoom, fewer nodes render for performance; more appear as you zoom in.

## Running

### Development (standalone)
```bash
cd frontend
npm install
npm run dev
```

Requires the backend API at `http://localhost:8000` (or set `VITE_API_URL` in `.env`).

### Via Docker
See the [root README](../README.md) for the full stack. Frontend runs at http://localhost:5173.

## Tests

### Unit tests (Vitest)
```bash
cd frontend
npm test -- --run
```

Watch mode (auto-rerun on changes):
```bash
npm test
```

### E2E tests (Playwright)
```bash
cd frontend
npm run test:e2e
```

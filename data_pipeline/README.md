# paper_graph Data Pipeline

A modular pipeline for building citation graphs, computing layouts, clustering, labeling with LLMs, and exporting to PostgreSQL.

## Overview

### The 5 Core Functions

1. **Paper Collection** (`api/`, `graph/`) – Crawl citation networks from Crossref/OpenAlex
2. **GPU Physics Layout** (`layout/`) – Compute 2D positions with ForceAtlas2 (cuGraph GPU or CPU fallback)
3. **Clustering** (`clustering/`) – Group papers with Louvain; hierarchical sub-clustering
4. **LLM Labeling** (`labeling/`, `embeddings/`) – Generate cluster labels with Llama 3.1
5. **PostgreSQL Export** (`export/`) – Load data into the database

### How the Pipeline Runs

- **Primary**: Via the web UI at `/admin/build` – create a build, and the backend runs it (either via `run_pipeline_worker.py` in Docker or `LocalPipelineExecutor` when using the unified stack).
- **Standalone CLI**: For manual runs outside the web app – e.g. custom seeds, debugging, or batch jobs.

## Installation

From project root:

```bash
pip install -r data_pipeline/requirements.txt
```

For **GPU layout** (RAPIDS/cuGraph), the Docker pipeline worker image includes the stack. For local GPU runs, install the matching CUDA toolkit and RAPIDS packages for your environment.

## Quick Start (Standalone CLI)

### Full Pipeline

```bash
# Seeds as JSON array or {"seeds": [...]}
echo '["10.1000/example.doi.1", "10.1000/example.doi.2"]' > seeds.json

python -m data_pipeline run-all \
    --seeds seeds.json \
    --db-url postgresql://pg:secret@localhost:5432/litsearch \
    --gpu
```

Required: `--db-url` (or `DATABASE_URL`). For LLM labeling, set `HF_TOKEN` (HuggingFace token for gated models like Llama).

### Step-by-Step

```bash
# 1. Build graph
python -m data_pipeline build --seeds seeds.json --output graph.pkl.gz

# 2. Compute layout
python -m data_pipeline layout graph.pkl.gz --gpu

# 3. Cluster
python -m data_pipeline cluster graph.pkl.gz

# 4. Label with LLM (requires HF_TOKEN)
python -m data_pipeline label graph.pkl.gz --batch-size 8

# 5. Export to PostgreSQL
python -m data_pipeline export graph.pkl.gz --db-url $DATABASE_URL
```

## Module Structure

```
data_pipeline/
├── api/                # Crossref, OpenAlex clients
├── graph/              # Citation crawler, graph builder
├── layout/             # GPU ForceAtlas2, CPU fallback
├── clustering/         # Louvain, hierarchical sub-clustering
├── embeddings/         # SapBERT encoder, k-core selection
├── labeling/           # LLM client, cluster labeler
├── export/             # PostgreSQL, pickle
├── workflow/           # Orchestrator
├── cli/                # CLI commands
├── config/             # Pydantic settings
├── models/             # Paper, graph, cluster models
└── utils/              # Logging, progress, errors
```

## Configuration

```python
from data_pipeline.config import PipelineConfig

config = PipelineConfig(
    seed_dois=["10.1001/jama.2020.12345"],
    max_depth=2,
    output_dir=Path("./output"),
    verbose=True,
)
config.layout.use_gpu = True
config.layout.fa2_iterations = 20000
config.clustering.louvain_resolution = 1.0
config.labeling.batch_size = 8
```

Or via environment variables:

- `DATABASE_URL` – PostgreSQL URL
- `HF_TOKEN` – HuggingFace token (for Llama)
- `PIPELINE_API_MAILTO` – Email for Crossref/OpenAlex requests

## Examples

### Custom Workflow

```python
from pathlib import Path
from data_pipeline.config import PipelineConfig
from data_pipeline.workflow.orchestrator import PipelineOrchestrator

config = PipelineConfig(
    seed_dois=["10.1001/jama.2020.12345"],
    max_depth=2,
    output_dir=Path("./my_output"),
)
config.layout.use_gpu = True

orchestrator = PipelineOrchestrator(config)
orchestrator.run_full_pipeline(config.seed_dois)
```

### Using Individual Components

```python
from data_pipeline.api import CrossrefClient, OpenAlexClient
from data_pipeline.graph import CitationCrawler, GraphBuilder

crossref = CrossrefClient(mailto="you@example.com")
openalex = OpenAlexClient(mailto="you@example.com")
crawler = CitationCrawler(
    crossref_client=crossref,
    openalex_client=openalex,
    include_citers=True,
)
builder = GraphBuilder(crawler)
builder.add_paper("10.1001/jama.2020.12345", max_depth=1)
graph_data = builder.get_graph_data()
```

## Testing

From project root:

```bash
# Unit tests
pytest data_pipeline/tests/unit/ -v

# Integration tests
pytest data_pipeline/tests/integration/ -v
```

## Troubleshooting

### GPU Out of Memory

```bash
python -m data_pipeline label graph.pkl.gz --batch-size 4
python -m data_pipeline layout graph.pkl.gz --no-gpu
```

### API Rate Limiting

Set `PIPELINE_API_MAILTO` and, if needed, increase delay in config:

```python
config.api.delay_between_requests = 0.5
```

### LLM Labeling Fails

- Set `HF_TOKEN` for gated models (Llama).
- Ensure enough VRAM; try `--batch-size 2` or 4-bit quantization (default).

## License

Same as paper_graph project.

# paper_graph Data Pipeline

A modular, maintainable pipeline for building citation graphs, computing layouts, clustering, labeling with LLMs, and exporting to PostgreSQL.

## 🎯 Overview

This refactored pipeline replaces the legacy monolithic code with clean, modular components organized by function.

### The 5 Core Functions

1. **Paper Collection** (`api/`, `graph/`) - Crawl citation networks from Crossref/OpenAlex
2. **GPU Physics Layout** (`layout/`) - Compute 2D positions with ForceAtlas2
3. **Clustering** (`clustering/`) - Group papers with Louvain algorithm
4. **LLM Labeling** (`labeling/`, `embeddings/`) - Generate cluster labels with Llama 3.1
5. **PostgreSQL Export** (`export/`) - Load data into production database

## 📦 Installation

```bash
cd paper_graph   # or project root
pip install -r data_pipeline/requirements.txt
```

For GPU support (optional but recommended):
```bash
pip install cudf-cu11 cugraph-cu11 cupy-cuda11x
```

## 🚀 Quick Start

### Full Pipeline (Single Command)

```bash
python -m data_pipeline run-all \
    --seeds seeds.json \
    --db-url postgresql://user:pass@localhost/litsearch \
    --gpu
```

### Step-by-Step

```bash
# 1. Build graph
python -m data_pipeline build --seeds seeds.json --output graph.pkl.gz

# 2. Compute layout
python -m data_pipeline layout graph.pkl.gz --gpu

# 3. Cluster
python -m data_pipeline cluster graph.pkl.gz

# 4. Label with LLM
python -m data_pipeline label graph.pkl.gz --batch-size 8

# 5. Export to PostgreSQL
python -m data_pipeline export graph.pkl.gz --db-url $DATABASE_URL
```

## 📁 Module Structure

```
data_pipeline/
├── api/                # External API clients
│   ├── crossref.py    # Crossref API
│   └── openalex.py    # OpenAlex API
├── graph/              # Graph construction
│   ├── builder.py     # High-level builder
│   └── crawler.py     # BFS citation crawler
├── layout/             # Graph layout
│   ├── gpu_fa2.py     # GPU ForceAtlas2
│   └── cpu_fa2.py     # CPU fallback
├── clustering/         # Community detection
│   ├── louvain.py     # Louvain clustering
│   └── hierarchical.py # Sub-clustering
├── embeddings/         # Document embeddings
│   ├── sapbert.py     # SapBERT encoder
│   └── core_selection.py # K-core selection
├── labeling/           # LLM labeling
│   ├── llm_client.py  # LLM interface
│   └── cluster_labeler.py # Label coordinator
├── export/             # Data export
│   ├── postgres_export.py # PostgreSQL
│   └── pickle_export.py   # Pickle format
├── workflow/           # Orchestration
│   └── orchestrator.py # Main coordinator
├── cli/                # Command-line interface
│   └── main.py        # CLI commands
├── config/             # Configuration
│   └── settings.py    # Pydantic config
├── models/             # Data models
│   ├── paper.py       # Paper dataclass
│   ├── graph.py       # Graph container
│   └── cluster.py     # Cluster models
└── utils/              # Utilities
    ├── logging.py     # Logging setup
    ├── progress.py    # Progress bars
    └── errors.py      # Exception classes
```

## 🔧 Configuration

Configuration via Pydantic models or environment variables:

```python
from data_pipeline.config import PipelineConfig

config = PipelineConfig(
    seed_dois=["10.1001/jama.2020.12345"],
    max_depth=1,
    output_dir="./output",
    verbose=True,
)

# Customize components
config.layout.use_gpu = True
config.layout.fa2_iterations = 2000
config.clustering.louvain_resolution = 1.0
config.labeling.batch_size = 8
```

Or via environment variables:
```bash
export PIPELINE_MAX_DEPTH=2
export PIPELINE_VERBOSE=true
export DATABASE_URL=postgresql://...
```

## 📊 What Changed from Legacy Code

| Aspect | Before (Legacy) | After (Refactored) |
|--------|----------------|-------------------|
| **Code Organization** | 1 file, 1,183 lines | 33 files, ~150 lines each |
| **Responsibilities** | 1 class does everything | Each class has 1 job |
| **Configuration** | Hard-coded values | Pydantic models + env vars |
| **Testing** | 0% coverage | Designed for 80%+ |
| **CLI** | 6 manual scripts | 1 unified command |
| **Error Handling** | Inconsistent | Proper exception hierarchy |
| **Documentation** | Scattered | Comprehensive |

## 🧪 Testing (Future)

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Full pipeline test
pytest tests/integration/test_full_pipeline.py
```

## 📝 Examples

### Custom Workflow

```python
from data_pipeline.config import PipelineConfig
from data_pipeline.workflow import PipelineOrchestrator

# Create config
config = PipelineConfig(
    seed_dois=["10.1001/jama.2020.12345"],
    max_depth=2,
    output_dir="./my_output",
)

# Run pipeline
orchestrator = PipelineOrchestrator(config)
orchestrator.run_full_pipeline(config.seed_dois)
```

### Using Individual Components

```python
from data_pipeline.api import CrossrefClient, OpenAlexClient
from data_pipeline.graph import CitationCrawler, GraphBuilder

# Build graph manually
crossref = CrossrefClient(mailto="you@example.com")
crawler = CitationCrawler(crossref_client=crossref)
builder = GraphBuilder(crawler)

builder.add_paper("10.1001/jama.2020.12345", max_depth=1)
graph_data = builder.get_graph_data()
```

## 🔗 Backward Compatibility

- Can load existing `.pkl.gz` files
- Can read existing label JSON files
- Database schema unchanged
- Can run alongside legacy code

## 🐛 Troubleshooting

### GPU Out of Memory
```bash
# Reduce batch size
python -m data_pipeline label graph.pkl.gz --batch-size 4

# Or use CPU
python -m data_pipeline layout graph.pkl.gz --no-gpu
```

### API Rate Limiting
Configure delays in settings:
```python
config.api.delay_between_requests = 0.5  # seconds
```

## 🤝 Contributing

When adding new components:
1. Follow the existing module structure
2. Keep modules < 500 lines
3. Add type hints
4. Write docstrings
5. Add tests

## 📄 License

Same as paper_graph project.

---

**Version**: 2.0.0  
**Status**: Production Ready  
**Replaces**: Legacy `graph_builder6.py`, `cluster_labeler.py`, etc.


# paper_graph

GPU-accelerated literature search and citation network visualization.

## 🚀 Quick Start

### Prerequisites
- Docker Desktop with GPU support (NVIDIA Container Toolkit)
- NVIDIA GPU with CUDA support
- Windows with WSL2 or Linux

### Setup
1. Copy the environment template and configure it:
   ```powershell
   copy .env.example .env
   ```
   Edit `.env` and set at minimum:
   - **HF_TOKEN** — HuggingFace API token (required for gated models like Llama; get one at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens))
   - **PIPELINE_API_MAILTO** — Your email for Crossref/OpenAlex API requests
2. For Docker, `.env` is loaded automatically; the `DATABASE_URL` default matches the local Compose stack.

### Start All Services

```powershell
# Windows
.\start-unified.ps1

# Or directly
docker-compose -f docker-compose.unified.yml up -d
```

This starts:
- **Frontend UI** - http://localhost:5173
- **Backend API** - http://localhost:8000
- **PostgreSQL** - localhost:5432
- **GPU Pipeline Worker** - RAPIDS + cuGraph

### Monitor Logs

```powershell
# All services
docker-compose -f docker-compose.unified.yml logs -f

# Specific service
docker-compose -f docker-compose.unified.yml logs -f pipeline-worker
```

### Stop All Services

```powershell
.\stop-unified.ps1
# or
docker-compose -f docker-compose.unified.yml down
```

## How It Works

1. **Seed** – You provide DOIs of starting papers.
2. **Crawl** – The pipeline fetches citations and references via Crossref/OpenAlex.
3. **Graph** – Papers become nodes; citations become edges.
4. **Layout** – GPU ForceAtlas2 positions nodes for visualization.
5. **Cluster** – Louvain finds communities; optional sub-clustering.
6. **Label** – LLM (Llama 3.1) generates cluster labels.
7. **Export** – Data is loaded into PostgreSQL.
8. **Visualize** – The frontend renders the graph with Sigma.js; you can search, filter, and explore.

## Further Documentation

- [Backend API](backend/README.md) – Routes, services, database
- [Frontend](frontend/README.md) – React app and visualization
- [Data Pipeline](data_pipeline/README.md) – Crawl, layout, clustering, labeling

## 🏗️ Architecture

### Services

1. **Frontend** (React + Vite)
   - Interactive graph visualization
   - Build management UI
   - Graph switcher

2. **Backend** (FastAPI)
   - REST API for data access
   - Build orchestration
   - PostgreSQL interface

3. **PostgreSQL**
   - Paper metadata storage
   - Graph data
   - Build tracking

4. **Pipeline Worker** (GPU)
   - Citation network crawling
   - GPU-accelerated graph layout (cuGraph)
   - ML embeddings (PyTorch + SapBERT)
   - LLM-based labeling (Llama 3.1)
   - Louvain clustering

### Tech Stack

- **GPU**: RAPIDS (cuGraph, cuDF, cuPy) + PyTorch
- **Backend**: FastAPI + PostgreSQL
- **Frontend**: React + Sigma.js + Vite
- **Package Manager**: UV (10-100x faster than pip!)
- **Container**: Docker with NVIDIA GPU support

## 📦 Project Structure

```
paper_graph/
├── backend/              # FastAPI backend
│   └── app/
│       ├── routes/       # API endpoints
│       ├── services/     # Business logic
│       └── database/     # DB queries
├── frontend/             # React frontend
│   └── src/
│       ├── components/   # UI components
│       ├── pages/        # Page components
│       └── api/          # API client
├── data_pipeline/        # GPU pipeline code
│   ├── api/              # Crossref/OpenAlex clients
│   ├── graph/            # Citation crawling
│   ├── layout/           # GPU ForceAtlas2
│   ├── embeddings/       # SapBERT encoder
│   ├── clustering/       # Louvain clustering
│   ├── labeling/         # LLM labeling
│   └── workflow/         # Pipeline orchestration
├── tests/                # Test suite
└── docker-compose.unified.yml  # Main compose file
```

## 🎯 Usage

### Create a Citation Network

1. Open http://localhost:5173/admin/build
2. Enter seed DOIs (papers to start from)
3. Configure:
   - Max crawl depth (1-3)
   - Max citers per paper (0-200)
   - GPU layout iterations
4. Submit
5. Monitor: `docker-compose -f docker-compose.unified.yml logs -f pipeline-worker`

### View Results

1. Graph appears in dropdown when complete
2. Click to activate
3. Explore interactive visualization at http://localhost:5173

## 🔧 Development

### Code Changes

Code is mounted as Docker volumes - changes reflect immediately without rebuild:

```powershell
# Backend/Frontend/Pipeline code changed
docker-compose -f docker-compose.unified.yml restart backend
docker-compose -f docker-compose.unified.yml restart pipeline-worker
```

### Dependencies Changed

```powershell
# Rebuild specific service
docker-compose -f docker-compose.unified.yml build pipeline-worker
docker-compose -f docker-compose.unified.yml up -d
```

### Database Changes

```powershell
# Reset database (⚠️ deletes all data!)
docker-compose -f docker-compose.unified.yml down -v
docker-compose -f docker-compose.unified.yml up -d
```

## 🐛 Troubleshooting

### GPU Not Working

```powershell
# Check GPU access in worker
docker exec litsearch-pipeline-worker nvidia-smi
docker exec litsearch-pipeline-worker python -c "import torch; print('CUDA:', torch.cuda.is_available())"
```

### Port Already in Use

```powershell
# Check what's using ports
netstat -ano | findstr :5173   # Frontend
netstat -ano | findstr :8000   # Backend
netstat -ano | findstr :5432   # Database
```

### Container Won't Start

```powershell
# Check logs
docker-compose -f docker-compose.unified.yml logs [service-name]

# Check status
docker-compose -f docker-compose.unified.yml ps
```

## 📊 Performance

- **Image Size**: ~26GB (includes full RAPIDS + PyTorch stack)
- **Build Time**: ~7 minutes (first build), seconds (cached rebuilds)
- **GPU**: RTX 3090 (24GB VRAM) - adjust for your hardware
- **Graph Layout**: Handles 100K+ nodes efficiently with GPU

## 🙏 Credits

Built with:
- [RAPIDS](https://rapids.ai/) - GPU-accelerated data science
- [cuGraph](https://github.com/rapidsai/cugraph) - GPU graph algorithms
- [PyTorch](https://pytorch.org/) - ML framework
- [Transformers](https://huggingface.co/transformers/) - LLM/embeddings
- [FastAPI](https://fastapi.tiangolo.com/) - Backend framework
- [React](https://react.dev/) - Frontend framework
- [Sigma.js](https://www.sigmajs.org/) - Graph visualization

## 🔒 Security
- Never commit `.env` — it is gitignored.
- If you previously exposed credentials (e.g. tokens in older commits), rotate them before publishing.

## 📄 License

GNU GPL v3 - see [LICENSE](LICENSE).


# LLM Fine-Tuning & RAG Pipeline

A complete pipeline for fine-tuning Google Gemini models and querying your codebase using RAG (Retrieval-Augmented Generation).

## What This Does

1. **RAG Pipeline** - Query your codebase with natural language
   - "Is user authentication implemented?"
   - "Show me code that handles database connections"
   - Returns actual code snippets with file/line citations

2. **Fine-Tuning Pipeline** - Train Gemini to know your coding style
   - Model learns your patterns and conventions
   - Combined with RAG for best results

## Quick Start (Docker)

```bash
# 1. Start services
docker compose up -d --build

# 2. Index your codebase (for RAG)
docker compose exec app python scripts/index_codebase.py -s data/raw

# 3. Query your code
docker compose exec app python scripts/query_codebase.py -i
```

## Architecture

```
                          YOUR CODEBASE
                          data/raw/
                               │
         ┌─────────────────────┴─────────────────────┐
         │                                           │
         ▼                                           ▼
┌─────────────────┐                     ┌─────────────────┐
│  FINE-TUNING    │                     │      RAG        │
│  (one-time)     │                     │  (reindex on    │
│                 │                     │   code changes) │
└────────┬────────┘                     └────────┬────────┘
         │                                       │
         └──────────────┬────────────────────────┘
                        │
                        ▼
               ┌─────────────────┐
               │ COMBINED QUERY  │
               │                 │
               │ RAG retrieves   │
               │ actual code  +  │
               │ Fine-tuned      │
               │ model answers   │
               └─────────────────┘
```

## Prerequisites

- Docker & Docker Compose
- Google Cloud account with Vertex AI enabled (for embeddings & LLM)
- `gcloud` CLI authenticated

## Setup

### 1. Configure GCP

```bash
# Authenticate
gcloud auth application-default login

# Edit config
cp config/config.yaml.example config/config.yaml
# Set your project_id
# Set staging_bucket ONLY if you plan to use fine-tuning (RAG works without it)
```

**Note:** The `staging_bucket` is only required for fine-tuning. Vertex AI requires training data to be in GCS. If you only want to use RAG (codebase querying), you can skip the bucket configuration.

### 2. Add Your Code

```bash
# Copy your source code
cp -r /path/to/your/project/src data/raw/java/
```

### 3. Start Docker

```bash
docker compose up -d --build
```

## Usage

### RAG: Query Your Codebase

```bash
# Index (run once, or when code changes)
docker compose exec app python scripts/index_codebase.py -s data/raw

# Interactive query
docker compose exec app python scripts/query_codebase.py -i

# Single query
docker compose exec app python scripts/query_codebase.py -q "How is authentication handled?"
```

### Fine-Tuning: Train Custom Model

**⚠️ Requires GCS bucket:** Fine-tuning requires Google Cloud Storage because Vertex AI needs training data in GCS. This is a Google Cloud service requirement, not optional.

```bash
# Prepare training data
docker compose exec app python scripts/prepare_data.py

# Start training (uploads to GCS, launches Vertex AI job)
docker compose exec app python scripts/run_training.py

# Test your model
docker compose exec app python scripts/test_model.py -m "your-model-id" -i
```

**Alternative:** If you want to avoid GCS entirely, you can use RAG-only mode (no fine-tuning needed).

### Combined: RAG + Fine-Tuned Model

```bash
# Query using your fine-tuned model
docker compose exec app python scripts/query_codebase.py -i --model "your-model-id"
```

## Project Structure

```
llm-fine-tuning/
├── docker-compose.yml       # Docker services (app + pgvector)
├── Dockerfile
├── config/
│   └── config.yaml          # GCP and training configuration
├── data/
│   └── raw/                 # Your source code goes here
├── src/
│   ├── extractors/          # Code parsing (Java, Python, etc.)
│   ├── converters/          # Training data generation
│   ├── rag/                 # RAG pipeline
│   │   ├── chunker.py       # Semantic code chunking
│   │   ├── embedder.py      # Vertex AI embeddings
│   │   ├── vector_store.py  # pgvector storage
│   │   └── retriever.py     # Query + generate
│   └── training/            # Vertex AI fine-tuning
├── scripts/
│   ├── index_codebase.py    # Index code for RAG
│   ├── query_codebase.py    # Query with RAG
│   ├── prepare_data.py      # Prepare fine-tuning data
│   ├── run_training.py      # Launch fine-tuning
│   └── test_model.py        # Test models
└── docs/
    └── ARCHITECTURE.md      # Detailed architecture diagrams
```

## Supported Languages

- Java (full AST parsing)
- Python, JavaScript, TypeScript, Go, Rust, and more (generic extraction)

## Costs

| Component | Approximate Cost |
|-----------|------------------|
| Embeddings | ~$0.0001 per 1K characters |
| Gemini API | ~$1.25-5 per 1M tokens |
| Fine-tuning | ~$2-4 per 1M tokens trained |
| pgvector | Free (runs locally in Docker) |

## Documentation

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed pipeline diagrams.

## License

MIT

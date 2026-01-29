# Quick Start Guide

Get up and running in 5 minutes with Docker.

## Prerequisites

1. **Docker** and **Docker Compose** installed
2. **Google Cloud Account** with billing enabled
3. **Vertex AI API** enabled in your project
4. `gcloud` CLI authenticated

## Step 1: Setup

```bash
# Clone and enter project
cd llm-fine-tuning

# Authenticate with Google Cloud
gcloud auth application-default login

# Start Docker services
docker compose up -d --build
```

This starts:
- `app` - Python application
- `pgvector` - PostgreSQL with vector search

## Step 2: Configure

Edit `config/config.yaml`:

```yaml
gcp:
  project_id: "your-actual-project-id"  # Change this
  location: "us-central1"
  staging_bucket: "gs://your-bucket-name"  # Change this (for fine-tuning)

training:
  base_model: "gemini-2.5-pro"

rag:
  embedding_model: "text-embedding-005"
  llm_model: "gemini-2.5-pro"
```

## Step 3: Add Your Code

```bash
# Copy your source files
cp -r /path/to/your/java/project/src data/raw/java/

# Or Python, TypeScript, etc.
cp -r /path/to/your/python/project data/raw/
```

## Step 4: RAG - Query Your Codebase

```bash
# Index your code (creates embeddings, stores in pgvector)
docker compose exec app python scripts/index_codebase.py -s data/raw

# Query interactively
docker compose exec app python scripts/query_codebase.py -i
```

Example queries:
- "Is user authentication implemented?"
- "Show me how database connections are handled"
- "What design patterns are used?"

## Step 5: Fine-Tuning (Optional)

Train a custom model that knows your coding style:

```bash
# Generate training data
docker compose exec app python scripts/prepare_data.py --strategy code_explanation

# Upload and start training
docker compose exec app python scripts/run_training.py
```

Training takes 1-4 hours. When done, use your model with RAG:

```bash
docker compose exec app python scripts/query_codebase.py -i --model "your-tuned-model-id"
```

## Common Commands

```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# View logs
docker compose logs -f app

# Rebuild after code changes
docker compose up -d --build

# Shell into container
docker compose exec app bash
```

## Troubleshooting

### "No source files found"
Place your code in `data/raw/` (Java in `data/raw/java/`)

### "Connection refused" to database
Wait a few seconds for pgvector to start, or check `docker compose ps`

### "Permission denied" on Docker
Run `sudo usermod -aG docker $USER` and log out/in

### Vertex AI authentication errors
Run `gcloud auth application-default login` and restart containers

## Costs

| Operation | Cost |
|-----------|------|
| Index 1000 code chunks | ~$0.10 |
| 100 RAG queries | ~$0.50-2.00 |
| Fine-tune (1000 examples, 3 epochs) | ~$5-15 |

## Next Steps

1. Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed diagrams
2. Try different `--strategy` options for fine-tuning
3. Use `--model` flag to combine RAG with your fine-tuned model

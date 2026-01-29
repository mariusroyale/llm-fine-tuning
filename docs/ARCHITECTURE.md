# LLM Fine-Tuning & RAG Pipeline Architecture

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           COMPLETE PIPELINE                                     │
└─────────────────────────────────────────────────────────────────────────────────┘

                              YOUR CODEBASE
                              data/raw/
                                   │
                                   ▼
         ┌─────────────────────────┴─────────────────────────┐
         │                                                   │
         ▼                                                   ▼
┌─────────────────────┐                         ┌─────────────────────┐
│   FINE-TUNING PATH  │                         │      RAG PATH       │
│                     │                         │                     │
│ Teaches model your  │                         │ Retrieves actual    │
│ coding style        │                         │ code for queries    │
└─────────────────────┘                         └─────────────────────┘
         │                                                   │
         ▼                                                   ▼
┌─────────────────────┐                         ┌─────────────────────┐
│ 1. Prepare Data     │                         │ 1. Index Codebase   │
│                     │                         │                     │
│ prepare_data.py     │                         │ index_codebase.py   │
│ - Extract code      │                         │ - Chunk code        │
│ - Generate prompts  │                         │ - Embed chunks      │
│ - Output JSONL      │                         │ - Store in pgvector │
└─────────────────────┘                         └─────────────────────┘
         │                                                   │
         ▼                                                   ▼
┌─────────────────────┐                         ┌─────────────────────┐
│ 2. Train            │                         │ 2. Query            │
│                     │                         │                     │
│ run_training.py     │                         │ query_codebase.py   │
│ - Upload to GCS     │                         │ - Embed question    │
│ - Fine-tune on      │                         │ - Retrieve chunks   │
│   Vertex AI         │                         │ - LLM generates     │
│ - Monitor job       │                         │   answer            │
└─────────────────────┘                         └─────────────────────┘
         │                                                   │
         ▼                                                   │
┌─────────────────────┐                                      │
│ 3. Test             │                                      │
│                     │                                      │
│ test_model.py       │                                      │
│ - Query tuned model │                                      │
│ - Compare with base │                                      │
└─────────────────────┘                                      │
         │                                                   │
         └─────────────────────────┬─────────────────────────┘
                                   │
                                   ▼
                         ┌─────────────────────┐
                         │   YOUR QUESTIONS    │
                         │                     │
                         │ "Is X implemented?" │
                         │ "Write code like Y" │
                         └─────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────┐
│  QUICK REFERENCE                                                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  RAG (query existing code):                                                     │
│    docker compose exec app python scripts/index_codebase.py -s data/raw         │
│    docker compose exec app python scripts/query_codebase.py -i                  │
│                                                                                 │
│  Fine-tuning (teach model your style):                                          │
│    docker compose exec app python scripts/prepare_data.py                       │
│    docker compose exec app python scripts/run_training.py                       │
│    docker compose exec app python scripts/test_model.py -m MODEL -i             │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

# Fine-Tuning Pipeline (Detailed)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        LLM FINE-TUNING PIPELINE                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  STEP 1: DATA INGESTION                                                         │
│  python scripts/prepare_data.py -s data/raw -o data/processed                   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│   data/raw/java/*.java                                                          │
│          │                                                                      │
│          ▼                                                                      │
│   ┌──────────────────┐                                                          │
│   │  JavaExtractor   │  src/extractors/java_extractor.py                        │
│   │                  │  - Parses .java files                                    │
│   │                  │  - Extracts: class name, methods, fields, Javadoc        │
│   └────────┬─────────┘                                                          │
│            │                                                                    │
│            ▼                                                                    │
│   ┌──────────────────┐                                                          │
│   │    Strategy      │  src/converters/strategies/                              │
│   │                  │                                                          │
│   │  Choose one:     │                                                          │
│   │  • code_explanation  → "Explain this code" prompts                          │
│   │  • code_generation   → "Write code that does X" prompts                     │
│   │  • code_review       → "Review this code" prompts                           │
│   └────────┬─────────┘                                                          │
│            │                                                                    │
│            ▼                                                                    │
│   ┌──────────────────┐                                                          │
│   │ CodeToJSONLConverter │  src/converters/code_to_jsonl.py                     │
│   │                  │                                                          │
│   │  Formats each example:                                                      │
│   │  {                                                                          │
│   │    "systemInstruction": {"role": "system", "parts": [...]},                 │
│   │    "contents": [                                                            │
│   │      {"role": "user", "parts": [{"text": "prompt"}]},                       │
│   │      {"role": "model", "parts": [{"text": "response"}]}                     │
│   │    ]                                                                        │
│   │  }                                                                          │
│   └────────┬─────────┘                                                          │
│            │                                                                    │
│            ▼                                                                    │
│   ┌────────────────────────────────────────┐                                    │
│   │  data/processed/                       │                                    │
│   │    ├── train.jsonl      (90%)          │                                    │
│   │    └── validation.jsonl (10%)          │                                    │
│   └────────────────────────────────────────┘                                    │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  STEP 2: UPLOAD & TRAIN                                                         │
│  python scripts/run_training.py                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│   ┌──────────────────┐         ┌──────────────────┐                             │
│   │  upload_data.py  │ ──────► │   Google Cloud   │                             │
│   │                  │         │   Storage (GCS)  │                             │
│   │  - Counts examples         │                  │                             │
│   │  - Estimates tokens        │  gs://bucket/    │                             │
│   │  - Uploads to GCS          │   └─ training/   │                             │
│   └──────────────────┘         │       ├─ train.jsonl                           │
│                                │       └─ validation.jsonl                      │
│                                └────────┬─────────┘                             │
│                                         │                                       │
│                                         ▼                                       │
│                                ┌──────────────────┐                             │
│   ┌──────────────────┐         │   Vertex AI      │                             │
│   │  start_tuning.py │ ──────► │   Fine-Tuning    │                             │
│   │                  │         │                  │                             │
│   │  Config:                   │  - Base: gemini-2.5-flash                      │
│   │  - epochs: 3               │  - Supervised tuning                           │
│   │  - learning_rate: 1.0      │  - Creates tuned model                         │
│   │  - adapter_size: 4         │                  │                             │
│   └──────────────────┘         └────────┬─────────┘                             │
│                                         │                                       │
│                                         ▼                                       │
│                                ┌──────────────────┐                             │
│   ┌──────────────────┐         │   Tuning Job     │                             │
│   │    monitor.py    │ ◄────── │   Status         │                             │
│   │                  │         │                  │                             │
│   │  Polls every 60s           │  RUNNING...      │                             │
│   │  until complete            │  SUCCEEDED ✓     │                             │
│   └──────────────────┘         └────────┬─────────┘                             │
│                                         │                                       │
│                                         ▼                                       │
│                                ┌──────────────────┐                             │
│                                │  Tuned Model     │                             │
│                                │                  │                             │
│                                │  models/your-    │                             │
│                                │  tuned-model-id  │                             │
│                                └────────┬─────────┘                             │
│                                         │                                       │
└─────────────────────────────────────────┼───────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  STEP 3: TEST                                                                   │
│  python scripts/test_model.py -m "models/your-tuned-model" -i --compare         │
└─────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│   ┌──────────────────┐                                                          │
│   │  test_model.py   │                                                          │
│   └────────┬─────────┘                                                          │
│            │                                                                    │
│            ├─────────────────────────────────────────────────────┐              │
│            │                                                     │              │
│            ▼                                                     ▼              │
│   ┌──────────────────┐                                 ┌──────────────────┐     │
│   │  Tuned Model     │                                 │  Base Model      │     │
│   │                  │                                 │  gemini-2.5-pro  │     │
│   │  Your fine-tuned │                                 │                  │     │
│   │  model           │                                 │  (--compare)     │     │
│   └────────┬─────────┘                                 └────────┬─────────┘     │
│            │                                                     │              │
│            └─────────────────────┬───────────────────────────────┘              │
│                                  │                                              │
│                                  ▼                                              │
│                         ┌──────────────────┐                                    │
│                         │     Output       │                                    │
│                         │                  │                                    │
│                         │  Side-by-side    │                                    │
│                         │  comparison of   │                                    │
│                         │  responses       │                                    │
│                         └──────────────────┘                                    │
│                                                                                 │
│   Modes:                                                                        │
│   • Single prompt:  -p "your prompt"                                            │
│   • Interactive:    -i (maintains conversation history)                         │
│   • Compare:        --compare (shows both tuned + base responses)               │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────┐
│  CONFIGURATION: config/config.yaml                                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  gcp:                                                                           │
│    project_id: "your-project"                                                   │
│    location: "us-central1"                                                      │
│    staging_bucket: "gs://your-bucket"                                           │
│                                                                                 │
│  training:                                                                      │
│    base_model: "gemini-2.5-flash"                                               │
│    epochs: 3                                                                    │
│    learning_rate_multiplier: 1.0                                                │
│    adapter_size: 4                                                              │
│                                                                                 │
│  strategy:                                                                      │
│    system_instruction: "You are a code expert..."                               │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────┐
│  QUICK START: FINE-TUNING                                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  1. Add your Java code:     cp -r /path/to/java/src data/raw/java/              │
│  2. Configure GCP:          vim config/config.yaml                              │
│  3. Prepare data:           python scripts/prepare_data.py                      │
│  4. Train:                  python scripts/run_training.py                      │
│  5. Test:                   python scripts/test_model.py -m MODEL -i            │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

# RAG (Retrieval-Augmented Generation) Pipeline

Use RAG to query your codebase with natural language:
- "Is user authentication already implemented?"
- "Show me code that handles database connections"
- "What classes implement the Repository pattern?"

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           RAG PIPELINE                                          │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  INDEXING PHASE                                                                 │
│  python scripts/index_codebase.py -s data/raw                                   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│   data/raw/                                                                     │
│   ├── java/*.java                                                               │
│   ├── *.py                                                                      │
│   └── *.ts, *.js, etc.                                                          │
│          │                                                                      │
│          ▼                                                                      │
│   ┌──────────────────┐                                                          │
│   │   CodeChunker    │  src/rag/chunker.py                                      │
│   │                  │                                                          │
│   │  - Reuses JavaExtractor & GenericExtractor                                  │
│   │  - Splits code into semantic chunks (classes, methods)                      │
│   │  - Preserves metadata (file path, line numbers, docs)                       │
│   └────────┬─────────┘                                                          │
│            │                                                                    │
│            ▼                                                                    │
│   ┌──────────────────┐                                                          │
│   │  VertexEmbedder  │  src/rag/embedder.py                                     │
│   │                  │                                                          │
│   │  - Vertex AI text-embedding-005                                             │
│   │  - Batch processing for efficiency                                          │
│   │  - 768-dimensional vectors                                                  │
│   └────────┬─────────┘                                                          │
│            │                                                                    │
│            ▼                                                                    │
│   ┌──────────────────┐                                                          │
│   │  PgVectorStore   │  src/rag/vector_store.py                                 │
│   │                  │                                                          │
│   │  - PostgreSQL + pgvector                                                    │
│   │  - Cosine similarity search                                                 │
│   │  - Stores: embedding, code, metadata                                        │
│   └──────────────────┘                                                          │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  QUERY PHASE                                                                    │
│  python scripts/query_codebase.py -q "Is authentication implemented?"           │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│   User Query: "Is user authentication implemented?"                             │
│          │                                                                      │
│          ▼                                                                      │
│   ┌──────────────────┐                                                          │
│   │  VertexEmbedder  │  Embed the query                                         │
│   └────────┬─────────┘                                                          │
│            │                                                                    │
│            ▼                                                                    │
│   ┌──────────────────┐                                                          │
│   │  PgVectorStore   │  Similarity search (top-k)                               │
│   │                  │                                                          │
│   │  Returns:                                                                   │
│   │  ├── AuthService.java:authenticate() (score: 0.92)                          │
│   │  ├── TokenValidator.java:validate()  (score: 0.87)                          │
│   │  └── UserController.java:login()     (score: 0.81)                          │
│   └────────┬─────────┘                                                          │
│            │                                                                    │
│            ▼                                                                    │
│   ┌──────────────────┐                                                          │
│   │  CodeRetriever   │  src/rag/retriever.py                                    │
│   │                  │                                                          │
│   │  - Builds context from retrieved chunks                                     │
│   │  - Calls LLM (Gemini) with query + code context                             │
│   │  - Returns answer with file/line citations                                  │
│   └────────┬─────────┘                                                          │
│            │                                                                    │
│            ▼                                                                    │
│   ┌──────────────────────────────────────────────────────────────────┐          │
│   │  Response:                                                       │          │
│   │                                                                  │          │
│   │  "Yes, user authentication is implemented in AuthService.java.   │          │
│   │   The authenticate() method at line 45 handles credential        │          │
│   │   validation:                                                    │          │
│   │                                                                  │          │
│   │   ```java                                                        │          │
│   │   public AuthResult authenticate(String user, String pass) {     │          │
│   │       // actual code from your codebase                          │          │
│   │   }                                                              │          │
│   │   ```                                                            │          │
│   │                                                                  │          │
│   │   Sources:                                                       │          │
│   │   1. src/auth/AuthService.java:45-78                             │          │
│   │   2. src/auth/TokenValidator.java:23-41                          │          │
│   └──────────────────────────────────────────────────────────────────┘          │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────┐
│  RAG CONFIGURATION: config/config.yaml                                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  rag:                                                                           │
│    embedding_model: "text-embedding-005"                                        │
│    llm_model: "gemini-2.5-pro"                                                  │
│    top_k: 5                                                                     │
│                                                                                 │
│    pgvector:                                                                    │
│      host: "localhost"                                                          │
│      port: 5432                                                                 │
│      database: "codebase_rag"                                                   │
│      user: "postgres"                                                           │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────┐
│  QUICK START: RAG                                                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Prerequisites:                                                                 │
│  1. Install PostgreSQL with pgvector extension                                  │
│  2. Create database:  createdb codebase_rag                                     │
│  3. Configure GCP project in config/config.yaml                                 │
│                                                                                 │
│  Usage:                                                                         │
│  1. Index codebase:   python scripts/index_codebase.py -s data/raw              │
│  2. Query:            python scripts/query_codebase.py -q "your question"       │
│  3. Interactive:      python scripts/query_codebase.py -i                       │
│                                                                                 │
│  Options:                                                                       │
│  --top-k N           Retrieve N chunks (default: 5)                             │
│  --language java     Filter by language                                         │
│  --retrieve-only     Show chunks without LLM generation                         │
│  --reset             Reindex from scratch                                       │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────┐
│  FINE-TUNING vs RAG: WHEN TO USE WHICH                                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  FINE-TUNING (scripts/run_training.py)                                          │
│  ├── Best for: Teaching model your coding style/patterns                        │
│  ├── Use when: You want the model to write code like your team                  │
│  └── Trade-off: Requires retraining when codebase changes                       │
│                                                                                 │
│  RAG (scripts/query_codebase.py)                                                │
│  ├── Best for: Answering questions about existing code                          │
│  ├── Use when: "Is X implemented?" / "Where is Y handled?"                      │
│  └── Trade-off: Just reindex when codebase changes (fast)                       │
│                                                                                 │
│  COMBINED (recommended for production)                                          │
│  ├── Fine-tune for coding style + domain knowledge                              │
│  └── RAG for accurate code retrieval + citations                                │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

# Docker Setup

Run everything with Docker—no local PostgreSQL installation needed.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  DOCKER QUICK START                                                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  # 1. Start everything (builds app + starts pgvector)                           │
│  docker compose up -d                                                           │
│                                                                                 │
│  # 2. Index your codebase                                                       │
│  docker compose exec app python scripts/index_codebase.py -s data/raw           │
│                                                                                 │
│  # 3. Query                                                                     │
│  docker compose exec app python scripts/query_codebase.py -i                    │
│                                                                                 │
│  # 4. Fine-tuning (prepare data)                                                │
│  docker compose exec app python scripts/prepare_data.py                         │
│                                                                                 │
│  # Stop services                                                                │
│  docker compose down                                                            │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────┐
│  DOCKER ARCHITECTURE                                                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────┐      ┌─────────────────┐                                   │
│  │      app        │      │    pgvector     │                                   │
│  │                 │      │                 │                                   │
│  │  Python 3.11    │─────▶│  PostgreSQL 16  │                                   │
│  │  + dependencies │      │  + pgvector     │                                   │
│  │                 │      │                 │                                   │
│  └────────┬────────┘      └─────────────────┘                                   │
│           │                                                                     │
│           ▼                                                                     │
│  ┌─────────────────┐                                                            │
│  │  Mounted Volumes│                                                            │
│  │                 │                                                            │
│  │  - ./data/raw   │  Your source code                                          │
│  │  - ./config     │  Configuration                                             │
│  │  - ~/.config/   │  GCP credentials                                           │
│  │      gcloud     │                                                            │
│  └─────────────────┘                                                            │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────┐
│  ENVIRONMENT VARIABLES                                                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Database (auto-configured in docker-compose):                                  │
│    PGHOST=pgvector                                                              │
│    PGPORT=5432                                                                  │
│    PGDATABASE=codebase_rag                                                      │
│    PGUSER=postgres                                                              │
│    PGPASSWORD=postgres                                                          │
│                                                                                 │
│  GCP (mount your credentials or set):                                           │
│    GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json                     │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

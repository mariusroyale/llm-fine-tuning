# LLM Fine-Tuning & RAG Pipeline Architecture

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           COMPLETE PIPELINE                                     │
└─────────────────────────────────────────────────────────────────────────────────┘

                              YOUR CODEBASE
                              data/raw/
                                   │
         ┌─────────────────────────┴─────────────────────────┐
         │                                                   │
         ▼                                                   ▼
┌─────────────────────┐                         ┌─────────────────────┐
│   FINE-TUNING       │                         │      RAG            │
│   (one-time)        │                         │   (reindex on       │
│                     │                         │    code changes)    │
│ Teaches model your  │                         │                     │
│ coding style        │                         │ Retrieves actual    │
└─────────────────────┘                         │ code for queries    │
         │                                      └─────────────────────┘
         ▼                                                   │
┌─────────────────────┐                                      │
│ 1. prepare_data.py  │                                      │
│ 2. run_training.py  │                                      │
│ 3. test_model.py    │                                      │
└─────────────────────┘                                      │
         │                                                   │
         │  Creates tuned model                              │
         │                                                   ▼
         │                                      ┌─────────────────────┐
         │                                      │ index_codebase.py   │
         │                                      │ - Chunk code        │
         │                                      │ - Embed + store     │
         │                                      └─────────────────────┘
         │                                                   │
         └──────────────────┐       ┌────────────────────────┘
                            │       │
                            ▼       ▼
                   ┌─────────────────────────┐
                   │   COMBINED QUERY        │
                   │                         │
                   │   query_codebase.py     │
                   │   --model YOUR_MODEL    │
                   │                         │
                   │   RAG retrieves code    │
                   │         +               │
                   │   Fine-tuned model      │
                   │   generates answer      │
                   └─────────────────────────┘
                              │
                              ▼
                   ┌─────────────────────────┐
                   │   ACCURATE ANSWERS      │
                   │                         │
                   │ • Real code snippets    │
                   │ • Knows your patterns   │
                   │ • File/line citations   │
                   └─────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────┐
│  QUICK REFERENCE                                                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  1. DATA INGESTION - Add your source code and templates                         │
│     data/raw/                                                                   │
│       ├── java/           # Java source files                                   │
│       ├── templates/      # JSON templates (optional)                           │
│       └── docs/           # Documentation (optional)                            │
│                                                                                 │
│  2. START SERVICES                                                              │
│     docker compose up -d                                                        │
│                                                                                 │
│  3. INDEX CODEBASE - Build searchable vector database                           │
│     docker compose exec app python scripts/index_codebase.py -s data/raw        │
│                                                                                 │
│  4. QUERY CODEBASE - Ask questions about your code                              │
│     docker compose exec app python scripts/query_codebase.py -i                 │
│     docker compose exec app python scripts/query_codebase.py -q "..." --with-deps│
│     docker compose exec app python scripts/query_codebase.py --class-lookup NAME│
│                                                                                 │
│  5. (Optional) FINE-TUNING - Train model on your coding style                   │
│     docker compose exec app python scripts/prepare_data.py                      │
│     docker compose exec app python scripts/run_training.py                      │
│     docker compose exec app python scripts/test_model.py -m MODEL -i            │
│                                                                                 │
│  6. (Optional) TEMPLATE TRAINING - Train model to generate your JSON templates  │
│     docker compose exec app python scripts/generate_template_training.py \      │
│       -j data/raw/java -t data/raw/templates -o data/training                   │
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
│   │  • code_explanation    → "Explain this code" prompts                        │
│   │  • code_generation     → "Write code that does X" prompts                   │
│   │  • code_review         → "Review this code" prompts                         │
│   │  • template_generation → "Generate JSON template from Java" prompts         │
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
│   │  Config:                   │  - Base: gemini-2.5-pro                      │
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
│    staging_bucket: "gs://your-bucket"  # REQUIRED for fine-tuning only          │
│                                         # RAG works without GCS                 │
│                                                                                 │
│  training:                                                                      │
│    base_model: "gemini-2.5-pro"                                               │
│    epochs: 3                                                                    │
│    learning_rate_multiplier: 1.0                                                │
│    adapter_size: 4                                                              │
│                                                                                 │
│  strategy:                                                                      │
│    system_instruction: "You are a code expert..."                               │
│                                                                                 │
│  NOTE: staging_bucket is ONLY needed for fine-tuning. Vertex AI requires       │
│        training data in GCS - this is a Google Cloud service requirement.       │
│        RAG uses local pgvector storage and doesn't need GCS.                    │
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
│   │  - Indexes JSON templates with class reference detection                    │
│   │  - Extracts class dependencies from imports                                 │
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
│  --with-deps         Include class dependencies in context                      │
│  --class-lookup X    Look up class X with all relationships                     │
│  --template-deps X   Find Java classes referenced by template X                 │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────┐
│  FINE-TUNING vs RAG vs COMBINED                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  OPTION 1: RAG Only (quick start)                                               │
│  ├── Query → Retrieve code → Base Gemini → Answer                               │
│  ├── Pro: No training needed, accurate code retrieval                           │
│  └── Con: Model doesn't know your domain terminology                            │
│                                                                                 │
│  OPTION 2: Fine-tuning Only                                                     │
│  ├── Query → Fine-tuned model → Answer                                          │
│  ├── Pro: Model knows your coding style                                         │
│  └── Con: May hallucinate code, needs retraining on changes                     │
│                                                                                 │
│  OPTION 3: Combined (recommended)                                               │
│  ├── Query → Retrieve code → Fine-tuned model → Answer                          │
│  ├── Pro: Best of both worlds                                                   │
│  └── Model knows your style + sees actual code = accurate & contextual          │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────┐
│  COMBINED FLOW (RAG + Fine-tuned Model)                                         │
└─────────────────────────────────────────────────────────────────────────────────┘

   User Query: "How does our authentication work?"
          │
          ▼
   ┌──────────────────┐
   │  1. RETRIEVE     │  RAG retrieves actual code chunks
   │                  │  from your indexed codebase
   │  index_codebase  │
   │  + pgvector      │
   └────────┬─────────┘
            │
            ▼
   ┌──────────────────┐
   │  2. GENERATE     │  Fine-tuned model receives:
   │                  │  - Your question
   │  Fine-tuned      │  - Retrieved code snippets
   │  Gemini          │
   │                  │  Model understands your domain
   │                  │  + sees actual code = best answer
   └────────┬─────────┘
            │
            ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │  Response:                                                       │
   │                                                                  │
   │  "Our authentication uses JWT tokens via AuthService.           │
   │   The flow is: login() → validateCredentials() → generateToken() │
   │                                                                  │
   │   [Actual code snippet from your codebase]                       │
   │                                                                  │
   │   This follows our standard service pattern..."                  │
   │   ↑                                                              │
   │   Model knows YOUR patterns because it was fine-tuned            │
   └──────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────┐
│  HOW TO USE COMBINED MODE                                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Step 1: Fine-tune your model (one-time)                                        │
│    docker compose exec app python scripts/prepare_data.py                       │
│    docker compose exec app python scripts/run_training.py                       │
│    # Note your tuned model ID: models/your-tuned-model-xxxx                     │
│                                                                                 │
│  Step 2: Index your codebase (rerun when code changes)                          │
│    docker compose exec app python scripts/index_codebase.py -s data/raw         │
│                                                                                 │
│  Step 3: Query with your fine-tuned model                                       │
│    docker compose exec app python scripts/query_codebase.py -i \                │
│      --model "models/your-tuned-model-xxxx"                                     │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

# Template Generation & Dependency-Aware Features

Train the model to generate JSON templates from Java classes, and query with full dependency context.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  TEMPLATE GENERATION TRAINING                                                   │
│  python scripts/generate_template_training.py -j data/raw/java -t data/raw/templates │
└─────────────────────────────────────────────────────────────────────────────────┘

   Input: Java Class                    Output: JSON Template
   ┌─────────────────────────┐          ┌─────────────────────────┐
   │ public class UserService │   →     │ {                       │
   │   extends BaseService   │   →     │   "name": "UserService",│
   │   implements IUserOps { │   →     │   "extends": "BaseService",
   │                         │   →     │   "implements": ["IUserOps"],
   │   private UserRepo repo;│   →     │   "properties": {       │
   │   ...                   │   →     │     "repo": {           │
   │ }                       │   →     │       "$ref": "UserRepo"│
   └─────────────────────────┘          │     }                   │
                                        │   },                    │
                                        │   "dependencies": [     │
                                        │     "UserRepo",         │
                                        │     "BaseService"       │
                                        │   ]                     │
                                        │ }                       │
                                        └─────────────────────────┘

   The script:
   1. Extracts all Java classes from java directory
   2. Loads existing JSON templates from templates directory
   3. Matches classes to templates by:
      - Exact name (UserService.java → UserService.json)
      - Class references found in templates
      - Manual mappings file (optional)
   4. Generates training data:
      - User: "Generate template for this Java class: [code]"
      - Model: "Here's the template: [JSON]"


┌─────────────────────────────────────────────────────────────────────────────────┐
│  DEPENDENCY-AWARE RAG QUERIES                                                   │
└─────────────────────────────────────────────────────────────────────────────────┘

   Regular query:              Dependency-aware query:
   ┌──────────────────┐       ┌──────────────────┐
   │ Retrieves only   │       │ Retrieves chunks │
   │ matching chunks  │       │ + their deps     │
   └────────┬─────────┘       └────────┬─────────┘
            │                          │
            ▼                          ▼
   ┌──────────────────┐       ┌──────────────────┐
   │ AuthService.java │       │ AuthService.java │
   │                  │       │ + UserRepo.java  │
   │                  │       │ + TokenService   │
   │                  │       │ + user-template  │
   └──────────────────┘       └──────────────────┘

   Enable with: --with-deps

   Special query modes:

   # Look up a class with all its relationships
   python scripts/query_codebase.py --class-lookup UserService

   # Find Java classes referenced by a template
   python scripts/query_codebase.py --template-deps "config/user.json"


┌─────────────────────────────────────────────────────────────────────────────────┐
│  CROSS-REFERENCE DETECTION                                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  When indexing, the chunker automatically detects:                              │
│                                                                                 │
│  Java → Java references:                                                        │
│    - Import statements (same project classes)                                   │
│    - extends/implements clauses                                                 │
│    - Field types                                                                │
│    - Method parameter/return types                                              │
│                                                                                 │
│  JSON → Java references:                                                        │
│    - PascalCase identifiers that match known classes                            │
│    - Values in "$ref", "type", "class" fields                                   │
│                                                                                 │
│  This enables bidirectional queries:                                            │
│    "What templates use UserService?" → finds templates referencing it           │
│    "What Java classes does this template need?" → finds referenced classes      │
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

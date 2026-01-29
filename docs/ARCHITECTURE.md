# LLM Fine-Tuning Pipeline Architecture

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
│  QUICK START                                                                    │
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

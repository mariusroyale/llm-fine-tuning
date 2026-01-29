# Google Vertex AI Fine-Tuning Project

A complete pipeline for fine-tuning Google Gemini models using your Java classes and source code.

## Project Overview

This project enables you to:
1. **Extract knowledge** from Java classes and source code
2. **Transform** code into training datasets (JSONL format)
3. **Upload** to Google Cloud Storage
4. **Fine-tune** Gemini models via Vertex AI
5. **Evaluate** and deploy your custom model

## Recommended Use Cases for Your Java Code

Based on Google's fine-tuning capabilities, here are the best applications:

### 1. Code Understanding & Generation
- Train the model to understand YOUR coding patterns
- Generate code that follows your project's conventions
- Answer questions about your codebase architecture

### 2. Code Review Assistant
- Train on your code + review comments
- Generate code reviews in your team's style

### 3. Documentation Generator
- Train on code + documentation pairs
- Auto-generate docs matching your standards

### 4. Bug Pattern Detection
- Train on buggy code + fixes
- Identify similar patterns in new code

## Supported Models (Vertex AI)

| Model | Max Training Tokens | Best For |
|-------|---------------------|----------|
| Gemini 2.5 Pro | 131,072 | Complex reasoning, large codebases |
| Gemini 2.5 Flash | 131,072 | Fast inference, balanced quality |
| Gemini 2.5 Flash-Lite | 131,072 | Cost-effective, high volume |

## Project Structure

```
llm-fine-tuning/
├── README.md
├── requirements.txt
├── config/
│   └── config.yaml              # GCP and training configuration
├── data/
│   ├── raw/                     # Your Java source files go here
│   │   └── java/
│   ├── processed/               # Converted training data
│   │   ├── train.jsonl
│   │   └── validation.jsonl
│   └── examples/                # Example training data
├── src/
│   ├── __init__.py
│   ├── extractors/              # Code extraction modules
│   │   ├── __init__.py
│   │   ├── java_extractor.py    # Parse Java classes
│   │   └── generic_extractor.py # Other source files
│   ├── converters/              # Transform to training format
│   │   ├── __init__.py
│   │   ├── code_to_jsonl.py     # Main converter
│   │   └── strategies/          # Different training strategies
│   │       ├── __init__.py
│   │       ├── code_explanation.py
│   │       ├── code_generation.py
│   │       └── code_review.py
│   ├── training/                # Vertex AI integration
│   │   ├── __init__.py
│   │   ├── upload_data.py       # GCS upload
│   │   ├── start_tuning.py      # Launch fine-tuning job
│   │   └── monitor.py           # Job monitoring
│   └── evaluation/              # Model evaluation
│       ├── __init__.py
│       └── evaluate_model.py
├── scripts/
│   ├── prepare_data.py          # End-to-end data preparation
│   ├── run_training.py          # Launch training
│   └── test_model.py            # Test fine-tuned model
└── notebooks/
    └── exploration.ipynb        # Data exploration
```

## Quick Start

### Prerequisites
- Python 3.10+
- Google Cloud account with Vertex AI enabled
- `gcloud` CLI authenticated

### Installation

```bash
pip install -r requirements.txt
gcloud auth application-default login
```

### Step 1: Add Your Java Code

Place your Java source files in `data/raw/java/`:
```bash
cp -r /path/to/your/java/project/* data/raw/java/
```

### Step 2: Configure

Edit `config/config.yaml` with your GCP settings.

### Step 3: Prepare Training Data

```bash
python scripts/prepare_data.py --strategy code_explanation
```

### Step 4: Start Fine-Tuning

```bash
python scripts/run_training.py
```

### Step 5: Test Your Model

```bash
python scripts/test_model.py --prompt "Explain the UserService class"
```

## Training Data Format

Each training example follows this JSONL structure:

```json
{
  "systemInstruction": {
    "role": "system",
    "parts": [{"text": "You are an expert Java developer..."}]
  },
  "contents": [
    {"role": "user", "parts": [{"text": "Explain this Java class: ..."}]},
    {"role": "model", "parts": [{"text": "This class implements..."}]}
  ]
}
```

## Cost Estimation

| Component | Cost |
|-----------|------|
| Training | ~$0.002-0.007 per 1K tokens × epochs |
| Storage | ~$0.02/GB/month (GCS) |
| Inference | Same as base model rates |

## Requirements

- Minimum 100 training examples recommended
- Quality > Quantity for best results
- Validation set recommended (up to 5,000 examples)

## License

MIT

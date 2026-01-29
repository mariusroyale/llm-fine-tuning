# Quick Start Guide

Get your fine-tuned Gemini model running in 5 steps.

## Prerequisites

1. **Google Cloud Account** with billing enabled
2. **Vertex AI API** enabled in your project
3. **GCS Bucket** for storing training data
4. Python 3.10+

## Step 1: Setup

```bash
# Clone and enter project
cd llm-fine-tuning

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Authenticate with Google Cloud
gcloud auth application-default login
```

## Step 2: Configure

Edit `config/config.yaml`:

```yaml
gcp:
  project_id: "your-actual-project-id"  # ← Change this
  location: "us-central1"
  staging_bucket: "gs://your-bucket-name"  # ← Change this

training:
  base_model: "gemini-2.5-pro"  # Options: gemini-2.5-pro, gemini-2.5-flash, gemini-2.5-flash-lite
  epochs: 3
```

## Step 3: Add Your Java Code

```bash
# Copy your Java source files
cp -r /path/to/your/java/project/src data/raw/java/
```

**What to include:**
- Service classes
- Controllers
- Repositories
- Domain models
- Utility classes

**Minimum:** 100+ examples recommended (roughly 20-30 Java classes)

## Step 4: Prepare Training Data

```bash
# Generate training examples
python scripts/prepare_data.py --strategy code_explanation

# Check output
head -1 data/processed/train.jsonl | python -m json.tool
```

**Available strategies:**
- `code_explanation` - Train model to explain code (default)
- `code_generation` - Train model to write code in your style
- `code_review` - Train model to review code

## Step 5: Train and Deploy

```bash
# Upload data and start training
python scripts/run_training.py

# This will:
# 1. Upload data to GCS
# 2. Start fine-tuning job
# 3. Monitor progress
```

Training typically takes **1-4 hours** depending on dataset size.

## Step 6: Test Your Model

```bash
# Interactive testing
python scripts/test_model.py -m "projects/YOUR_PROJECT/locations/us-central1/models/YOUR_MODEL" -i

# Single prompt
python scripts/test_model.py -m "YOUR_MODEL" -p "Explain the UserService class"
```

## Estimated Costs

| Component | Approximate Cost |
|-----------|------------------|
| 1000 training examples, 3 epochs | ~$5-15 |
| Inference (per 1M tokens) | Same as base model |
| GCS Storage | < $1/month |

## Troubleshooting

### "No source files found"
→ Place Java files in `data/raw/java/`

### "Only X examples generated"
→ Add more source code (aim for 100+ examples)

### Training job fails
→ Check Vertex AI console for error details
→ Verify GCS bucket permissions

### "Model not found"
→ Training may still be in progress (check Vertex AI console)

## Next Steps

1. **Improve quality**: Manually review and edit training examples
2. **Add more data**: Include documentation, comments, code reviews
3. **Try different strategies**: Mix explanation + generation examples
4. **Evaluate**: Compare base model vs tuned model responses

## Resources

- [Vertex AI Fine-Tuning Docs](https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini-use-supervised-tuning)
- [Gemini API Reference](https://ai.google.dev/gemini-api/docs)
- [Training Data Best Practices](https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini-supervised-tuning-prepare)

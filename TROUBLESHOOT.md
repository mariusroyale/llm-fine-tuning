# Troubleshooting: "no configuration file provided: not found"

If you're seeing this error even for simple commands like `ls`, it's likely not coming from our scripts.

## Quick Fix

Try running commands directly in the container:

```bash
# Enter the container interactively
docker compose exec app bash

# Then inside the container, run:
python scripts/simple_test.py
python scripts/check_config.py
ls -la /app/config/
```

## Alternative: Run without docker compose exec

```bash
# Use docker exec directly
docker exec llm-fine-tuning python scripts/simple_test.py
docker exec llm-fine-tuning ls -la /app/config/
```

## Check if config file exists

```bash
# From host (WSL)
ls -la config/

# From container
docker exec llm-fine-tuning ls -la /app/config/
```

## Create config file if missing

If the config file doesn't exist, create it:

```bash
# Make sure config directory exists
mkdir -p config

# The config.yaml file should already exist in your project
# If not, copy from the example or create a minimal one
```

## Verify volume mount

Check if files are being mounted correctly:

```bash
docker exec llm-fine-tuning ls -la /app/
docker exec llm-fine-tuning cat /app/config/config.yaml | head -5
```

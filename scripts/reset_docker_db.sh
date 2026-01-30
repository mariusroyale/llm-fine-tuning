#!/bin/bash
# Reset Docker containers and wipe database volume

set -e

echo "🛑 Stopping Docker containers..."
docker compose down

echo "🗑️  Removing containers..."
docker compose rm -f

echo "💾 Removing database volume (pgvector_data)..."
docker volume rm llm-fine-tuning_pgvector_data 2>/dev/null || docker volume rm pgvector_data 2>/dev/null || echo "Volume not found (may already be removed)"

echo "🚀 Starting Docker containers..."
docker compose up -d

echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 5

echo "✅ Docker reset complete!"
echo ""
echo "Next steps:"
echo "  1. Wait for containers to be healthy (check with: docker compose ps)"
echo "  2. Re-index your codebase:"
echo "     docker compose exec app python scripts/index_codebase.py -s data/raw --reset"

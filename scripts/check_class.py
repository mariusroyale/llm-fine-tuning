#!/usr/bin/env python3
"""Check if a class exists in the database."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
from src.rag.vector_store import PgVectorStore

# Load config
with open("config/config.yaml") as f:
    cfg = yaml.safe_load(f)

pg = cfg["rag"]["pgvector"]

store = PgVectorStore(
    host=pg["host"],
    port=pg["port"],
    database=pg["database"],
    user=pg["user"],
    password=pg["password"],
    embedding_dimensions=768,
)

store.connect()

# Check for PaymentMethodConfig
class_name = "PaymentMethodConfig"
print(f"\nChecking for class: {class_name}\n")

# Exact match
cur = store._conn.cursor()
cur.execute(
    "SELECT class_name, file_path, chunk_type FROM code_chunks WHERE class_name = %s AND chunk_type = 'class'",
    (class_name,),
)
exact_match = cur.fetchall()
print(f"Exact match (class_name='{class_name}' AND chunk_type='class'):")
for row in exact_match:
    print(f"  {row}")

# Partial match
cur.execute(
    "SELECT class_name, file_path, chunk_type FROM code_chunks WHERE class_name LIKE %s OR file_path LIKE %s LIMIT 20",
    (f"%{class_name}%", f"%{class_name}%"),
)
partial_match = cur.fetchall()
print(f"\nPartial match (class_name or file_path LIKE '%{class_name}%'):")
for row in partial_match:
    print(f"  {row}")

# Check file path
cur.execute(
    "SELECT class_name, file_path, chunk_type FROM code_chunks WHERE file_path LIKE %s LIMIT 10",
    ("%PaymentMethodConfig.java%",),
)
file_match = cur.fetchall()
print(f"\nFile path match (file_path LIKE '%PaymentMethodConfig.java%'):")
for row in file_match:
    print(f"  {row}")

# Check all class chunks
cur.execute(
    "SELECT COUNT(*) FROM code_chunks WHERE chunk_type = 'class' AND language = 'java'"
)
total_java_classes = cur.fetchone()[0]
print(f"\nTotal Java class chunks in database: {total_java_classes}")

store.close()

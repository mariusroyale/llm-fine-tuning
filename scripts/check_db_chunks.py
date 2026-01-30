#!/usr/bin/env python3
"""Check what chunks exist in the database for a specific class."""

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

print("\n" + "="*80)
print("Checking database for PaymentMethodConfig chunks")
print("="*80 + "\n")

# Check for PaymentMethodConfig class
cur = store._conn.cursor()
cur.execute("""
    SELECT class_name, chunk_type, file_path, start_line, end_line, 
           LENGTH(content) as content_length,
           metadata->>'parent_class' as parent_class
    FROM code_chunks 
    WHERE class_name LIKE '%PaymentMethodConfig%' 
       OR file_path LIKE '%PaymentMethodConfig%'
    ORDER BY chunk_type, class_name
    LIMIT 50
""")

rows = cur.fetchall()

if rows:
    print(f"Found {len(rows)} chunks related to PaymentMethodConfig:\n")
    
    # Group by chunk_type
    by_type = {}
    for row in rows:
        chunk_type = row[1] or "unknown"
        if chunk_type not in by_type:
            by_type[chunk_type] = []
        by_type[chunk_type].append(row)
    
    for chunk_type in sorted(by_type.keys()):
        chunks = by_type[chunk_type]
        print(f"\n[{chunk_type.upper()}] ({len(chunks)} chunks):")
        print("-" * 80)
        for row in chunks:
            class_name, ct, file_path, start_line, end_line, content_len, parent_class = row
            print(f"  Class: {class_name or '(none)'}")
            print(f"  File:  {file_path}")
            print(f"  Lines: {start_line}-{end_line}")
            print(f"  Size:  {content_len:,} chars")
            if parent_class:
                print(f"  Parent: {parent_class}")
            print()
else:
    print("❌ No chunks found for PaymentMethodConfig!\n")

# Check for enum chunks specifically
print("\n" + "="*80)
print("Checking for enum chunks")
print("="*80 + "\n")

cur.execute("""
    SELECT class_name, chunk_type, file_path, 
           metadata->>'parent_class' as parent_class
    FROM code_chunks 
    WHERE chunk_type = 'enum'
    ORDER BY class_name
    LIMIT 20
""")

enum_rows = cur.fetchall()

if enum_rows:
    print(f"Found {len(enum_rows)} enum chunks:\n")
    for row in enum_rows:
        class_name, chunk_type, file_path, parent_class = row
        print(f"  {class_name or '(unnamed)'}")
        if parent_class:
            print(f"    Parent: {parent_class}")
        print(f"    File: {file_path}\n")
else:
    print("❌ No enum chunks found!\n")

# Check total counts
print("\n" + "="*80)
print("Database Statistics")
print("="*80 + "\n")

cur.execute("SELECT COUNT(*) FROM code_chunks")
total = cur.fetchone()[0]
print(f"Total chunks: {total:,}")

cur.execute("SELECT COUNT(*) FROM code_chunks WHERE chunk_type = 'class'")
class_count = cur.fetchone()[0]
print(f"Class chunks: {class_count:,}")

cur.execute("SELECT COUNT(*) FROM code_chunks WHERE chunk_type = 'enum'")
enum_count = cur.fetchone()[0]
print(f"Enum chunks: {enum_count:,}")

cur.execute("SELECT COUNT(*) FROM code_chunks WHERE chunk_type = 'method'")
method_count = cur.fetchone()[0]
print(f"Method chunks: {method_count:,}")

store.close()

#!/usr/bin/env python3
"""Test inner enum extraction and chunking without re-indexing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.extractors.java_extractor import JavaExtractor
from src.rag.chunker import CodeChunker

# Test on PaymentMethodConfig.java
test_file = Path("data/raw/java/PaymentMethodConfig.java")

if not test_file.exists():
    print(f"❌ File not found: {test_file}")
    sys.exit(1)

print(f"\n{'='*80}")
print(f"Testing inner enum extraction and chunking on: {test_file.name}")
print(f"{'='*80}\n")

# Step 1: Test extraction
print("Step 1: Testing extraction...")
extractor = JavaExtractor(max_lines=10000)
classes = extractor.extract_file(test_file)

if not classes:
    print("❌ No classes extracted!")
    sys.exit(1)

main_class = classes[0]
print(f"✅ Found main class: {main_class.name}")
print(f"   Type: {main_class.class_type}")
print(f"   Package: {main_class.package}")
print(f"   Inner classes: {len(main_class.inner_classes)}")

if main_class.inner_classes:
    print(f"\n✅ Inner types found:")
    for inner in main_class.inner_classes:
        print(f"   - {inner.name} ({inner.class_type})")
        print(f"     Source length: {len(inner.source_code)} chars")
else:
    print("\n❌ No inner types found!")
    print("\nExpected to find:")
    print("   - Type (enum)")
    print("   - Category (enum)")
    print("   - PMCategoryOptions (enum)")
    sys.exit(1)

# Verify expected enums
expected_enums = {"Type", "Category", "PMCategoryOptions"}
found_enums = {inner.name for inner in main_class.inner_classes if inner.class_type == "enum"}

missing = expected_enums - found_enums
if missing:
    print(f"\n⚠️  Missing expected enums: {missing}")
    sys.exit(1)
else:
    print(f"\n✅ All expected enums found: {found_enums}")

# Step 2: Test chunking
print(f"\n{'='*80}")
print("Step 2: Testing chunking...")
print(f"{'='*80}\n")

chunker = CodeChunker(include_classes=True, include_methods=False)
chunks = chunker._chunk_java_class(main_class, Path("data/raw"))

print(f"✅ Created {len(chunks)} chunks from {main_class.name}")

# Check for inner enum chunks
inner_enum_chunks = [c for c in chunks if c.chunk_type == "enum" and c.class_name and "." in c.class_name]
main_class_chunks = [c for c in chunks if c.chunk_type == "class" and c.class_name == main_class.name]

print(f"\nChunk breakdown:")
print(f"   Main class chunks: {len(main_class_chunks)}")
print(f"   Inner enum chunks: {len(inner_enum_chunks)}")

if inner_enum_chunks:
    print(f"\n✅ Inner enum chunks created:")
    for chunk in inner_enum_chunks:
        print(f"   - {chunk.class_name} ({chunk.chunk_type})")
        print(f"     Content length: {len(chunk.content)} chars")
        print(f"     Metadata parent_class: {chunk.metadata.get('parent_class', 'N/A')}")
else:
    print("\n❌ No inner enum chunks created!")
    print("   Expected chunks:")
    for enum_name in expected_enums:
        print(f"   - {main_class.name}.{enum_name} (enum)")
    sys.exit(1)

# Verify all expected enum chunks exist
expected_chunk_names = {f"{main_class.name}.{e}" for e in expected_enums}
found_chunk_names = {c.class_name for c in inner_enum_chunks}

missing_chunks = expected_chunk_names - found_chunk_names
if missing_chunks:
    print(f"\n⚠️  Missing expected enum chunks: {missing_chunks}")
    sys.exit(1)
else:
    print(f"\n✅ All expected enum chunks created: {found_chunk_names}")

print("\n" + "="*80)
print("✅ All tests passed! Inner enum extraction and chunking work correctly.")
print("="*80 + "\n")

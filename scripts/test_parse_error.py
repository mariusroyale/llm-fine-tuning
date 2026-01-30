#!/usr/bin/env python3
"""Test parsing errors to see what's actually failing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.extractors.java_extractor import JavaExtractor

extractor = JavaExtractor(max_lines=10000)

# Test PaymentMethodConfig
pmc_file = Path("data/raw/java/PaymentMethodConfig.java")
if pmc_file.exists():
    print(f"\n{'='*80}")
    print(f"Testing: {pmc_file}")
    print(f"{'='*80}")
    try:
        classes = extractor.extract_file(pmc_file)
        print(f"✅ Successfully parsed: {len(classes)} classes found")
        for cls in classes:
            print(f"  - {cls.name} ({cls.class_type})")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
else:
    print(f"File not found: {pmc_file}")

# Test User.java if it exists
user_files = list(Path("data/raw/java").glob("**/User.java"))
if user_files:
    for user_file in user_files:
        print(f"\n{'='*80}")
        print(f"Testing: {user_file}")
        print(f"{'='*80}")
        try:
            classes = extractor.extract_file(user_file)
            print(f"✅ Successfully parsed: {len(classes)} classes found")
            for cls in classes:
                print(f"  - {cls.name} ({cls.class_type})")
        except Exception as e:
            print(f"❌ Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
else:
    print("\nNo User.java files found")

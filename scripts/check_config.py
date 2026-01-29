#!/usr/bin/env python3
"""Quick script to check if config file exists and show its location."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

script_dir = Path(__file__).parent.parent
config_path = script_dir / "config" / "config.yaml"

print(f"Script directory: {script_dir}")
print(f"Config path: {config_path}")
print(f"Config absolute path: {config_path.absolute()}")
print(f"Config exists: {config_path.exists()}")

if config_path.exists():
    print(f"\n✓ Config file found!")
    print(f"  Size: {config_path.stat().st_size} bytes")
else:
    print(f"\n✗ Config file NOT found!")
    print(f"\nTo create it:")
    print(f"  mkdir -p {config_path.parent}")
    print(f"  # Then create {config_path} with your GCP settings")

#!/usr/bin/env python3
"""Generate training data for Java-to-Template tasks.

This script pairs Java classes with their corresponding JSON templates
and generates JSONL training data for fine-tuning the model to create
templates from Java code.

Usage:
    python scripts/generate_template_training.py \
        --java-dir data/raw/java \
        --template-dir data/raw/templates \
        --output-dir data/training \
        --config config/config.yaml

The script will:
1. Extract Java classes from the source directory
2. Load JSON templates from the template directory
3. Match classes to templates by:
   - Exact name matching (UserService.java -> UserService.json)
   - Class reference detection in templates
   - Manual mapping file (if provided)
4. Generate training examples pairing code with templates
"""

import argparse
import json
import logging
import random
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.converters.strategies.template_generation import (
    TemplateExample,
    TemplateGenerationStrategy,
)
from src.extractors.java_extractor import JavaClass, JavaExtractor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class MatchedPair:
    """A matched Java class and template pair."""

    java_class: JavaClass
    template_path: Path
    template_content: dict
    match_type: str  # 'exact', 'reference', 'manual'


class TemplateTrainingGenerator:
    """Generate training data from Java class and template pairs."""

    def __init__(
        self,
        java_dir: Path,
        template_dir: Path,
        mapping_file: Optional[Path] = None,
        system_instruction: Optional[str] = None,
    ):
        self.java_dir = java_dir
        self.template_dir = template_dir
        self.mapping_file = mapping_file
        self.system_instruction = system_instruction

        self.java_extractor = JavaExtractor()
        self.strategy = TemplateGenerationStrategy(
            system_instruction=system_instruction,
            template_dir=template_dir,
        )

        # Manual mappings: class_name -> template_path
        self.manual_mappings: dict[str, str] = {}
        if mapping_file and mapping_file.exists():
            self._load_manual_mappings(mapping_file)

    def _load_manual_mappings(self, mapping_file: Path) -> None:
        """Load manual class-to-template mappings from a JSON file."""
        try:
            with open(mapping_file, "r", encoding="utf-8") as f:
                self.manual_mappings = json.load(f)
            logger.info(f"Loaded {len(self.manual_mappings)} manual mappings")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Could not load mappings file: {e}")

    def generate(
        self,
        output_dir: Path,
        train_file: str = "template_train.jsonl",
        validation_file: str = "template_validation.jsonl",
        validation_split: float = 0.1,
        include_synthetic: bool = True,
    ) -> dict:
        """Generate training data from matched pairs.

        Args:
            output_dir: Directory to write output files
            train_file: Name of training file
            validation_file: Name of validation file
            validation_split: Fraction for validation set
            include_synthetic: Include synthetic templates for unmatched classes

        Returns:
            Statistics about the generation
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Extract all Java classes
        logger.info(f"Extracting Java classes from {self.java_dir}")
        java_classes = self.java_extractor.extract_directory(self.java_dir)
        logger.info(f"Found {len(java_classes)} Java classes")

        # Load all templates
        logger.info(f"Loading templates from {self.template_dir}")
        templates = self._load_templates()
        logger.info(f"Found {len(templates)} JSON templates")

        # Match classes to templates
        matched_pairs = self._match_classes_to_templates(java_classes, templates)
        logger.info(f"Matched {len(matched_pairs)} class-template pairs")

        # Generate training examples from matched pairs
        all_examples = []

        for pair in matched_pairs:
            self.strategy.add_template_example(
                pair.java_class,
                pair.template_path,
                pair.template_content,
            )

        # Get examples from real pairs
        paired_examples = self.strategy.generate_paired_examples()
        all_examples.extend(paired_examples)
        logger.info(f"Generated {len(paired_examples)} examples from real pairs")

        # Optionally add synthetic examples for unmatched classes
        if include_synthetic:
            matched_class_names = {p.java_class.name for p in matched_pairs}
            unmatched_classes = [
                c for c in java_classes if c.name not in matched_class_names
            ]

            synthetic_count = 0
            for java_class in unmatched_classes:
                examples = self.strategy.generate_class_examples(java_class)
                all_examples.extend(examples)
                synthetic_count += len(examples)

            logger.info(f"Generated {synthetic_count} synthetic examples")

        # Shuffle and split
        random.shuffle(all_examples)

        n_validation = int(len(all_examples) * validation_split)
        validation_examples = all_examples[:n_validation]
        training_examples = all_examples[n_validation:]

        # Write JSONL files
        self._write_jsonl(training_examples, output_dir / train_file)
        self._write_jsonl(validation_examples, output_dir / validation_file)

        stats = {
            "total_java_classes": len(java_classes),
            "total_templates": len(templates),
            "matched_pairs": len(matched_pairs),
            "match_breakdown": self._count_match_types(matched_pairs),
            "training_examples": len(training_examples),
            "validation_examples": len(validation_examples),
            "output_files": {
                "train": str(output_dir / train_file),
                "validation": str(output_dir / validation_file),
            },
        }

        logger.info(f"Generation complete: {stats}")
        return stats

    def _load_templates(self) -> dict[str, dict]:
        """Load all JSON templates from the template directory."""
        templates = {}

        if not self.template_dir.exists():
            return templates

        for template_file in self.template_dir.rglob("*.json"):
            try:
                with open(template_file, "r", encoding="utf-8") as f:
                    content = json.load(f)
                templates[str(template_file)] = {
                    "path": template_file,
                    "content": content,
                    "name": template_file.stem,
                }
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load template {template_file}: {e}")

        return templates

    def _match_classes_to_templates(
        self,
        java_classes: list[JavaClass],
        templates: dict[str, dict],
    ) -> list[MatchedPair]:
        """Match Java classes to their corresponding templates."""
        pairs = []
        used_templates = set()

        # Build class lookup
        class_by_name = {c.name: c for c in java_classes}

        # 1. Manual mappings (highest priority)
        for class_name, template_name in self.manual_mappings.items():
            if class_name in class_by_name:
                # Find the template
                for template_path, template_data in templates.items():
                    if template_data["name"] == template_name or template_path.endswith(
                        template_name
                    ):
                        pairs.append(
                            MatchedPair(
                                java_class=class_by_name[class_name],
                                template_path=template_data["path"],
                                template_content=template_data["content"],
                                match_type="manual",
                            )
                        )
                        used_templates.add(template_path)
                        break

        # 2. Exact name matching
        for template_path, template_data in templates.items():
            if template_path in used_templates:
                continue

            template_name = template_data["name"]

            # Try exact match (e.g., UserService.json -> UserService.java)
            if template_name in class_by_name:
                pairs.append(
                    MatchedPair(
                        java_class=class_by_name[template_name],
                        template_path=template_data["path"],
                        template_content=template_data["content"],
                        match_type="exact",
                    )
                )
                used_templates.add(template_path)

        # 3. Reference-based matching
        class_pattern = re.compile(r"^[A-Z][a-zA-Z0-9]+(?:[A-Z][a-zA-Z0-9]+)*$")

        for template_path, template_data in templates.items():
            if template_path in used_templates:
                continue

            # Find class references in template
            references = self._find_class_references(
                template_data["content"], class_pattern
            )

            # Match to the most specific class reference
            for ref in references:
                if ref in class_by_name and ref not in [
                    p.java_class.name for p in pairs
                ]:
                    pairs.append(
                        MatchedPair(
                            java_class=class_by_name[ref],
                            template_path=template_data["path"],
                            template_content=template_data["content"],
                            match_type="reference",
                        )
                    )
                    used_templates.add(template_path)
                    break

        return pairs

    def _find_class_references(self, obj: any, pattern: re.Pattern) -> list[str]:
        """Find class references in a JSON structure."""
        references = []

        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(key, str) and pattern.match(key):
                    references.append(key)
                if isinstance(value, str) and pattern.match(value):
                    references.append(value)
                references.extend(self._find_class_references(value, pattern))
        elif isinstance(obj, list):
            for item in obj:
                references.extend(self._find_class_references(item, pattern))

        return references

    def _count_match_types(self, pairs: list[MatchedPair]) -> dict[str, int]:
        """Count pairs by match type."""
        counts = {"exact": 0, "reference": 0, "manual": 0}
        for pair in pairs:
            counts[pair.match_type] = counts.get(pair.match_type, 0) + 1
        return counts

    def _to_vertex_format(self, example) -> dict:
        """Convert a training example to Vertex AI format."""
        return {
            "systemInstruction": {
                "role": "system",
                "parts": [{"text": example.system_instruction}],
            },
            "contents": [
                {"role": "user", "parts": [{"text": example.user_prompt}]},
                {"role": "model", "parts": [{"text": example.model_response}]},
            ],
        }

    def _write_jsonl(self, examples: list, output_file: Path) -> None:
        """Write examples to a JSONL file."""
        with open(output_file, "w", encoding="utf-8") as f:
            for example in examples:
                vertex_format = self._to_vertex_format(example)
                f.write(json.dumps(vertex_format, ensure_ascii=False) + "\n")

        logger.info(f"Wrote {len(examples)} examples to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate template training data from Java classes"
    )
    parser.add_argument(
        "-j",
        "--java-dir",
        type=Path,
        required=True,
        help="Directory containing Java source files",
    )
    parser.add_argument(
        "-t",
        "--template-dir",
        type=Path,
        required=True,
        help="Directory containing JSON templates",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("data/training"),
        help="Output directory for training files",
    )
    parser.add_argument(
        "-m",
        "--mapping-file",
        type=Path,
        help="Optional JSON file with manual class-to-template mappings",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        help="Optional config file",
    )
    parser.add_argument(
        "--validation-split",
        type=float,
        default=0.1,
        help="Fraction of data for validation (default: 0.1)",
    )
    parser.add_argument(
        "--no-synthetic",
        action="store_true",
        help="Don't generate synthetic templates for unmatched classes",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load config if provided
    system_instruction = None
    if args.config and args.config.exists():
        with open(args.config, "r") as f:
            config = yaml.safe_load(f)
            system_instruction = config.get("training", {}).get(
                "template_system_instruction"
            )

    # Validate directories
    if not args.java_dir.exists():
        logger.error(f"Java directory does not exist: {args.java_dir}")
        sys.exit(1)

    if not args.template_dir.exists():
        logger.warning(
            f"Template directory does not exist: {args.template_dir}. "
            "Will generate synthetic templates only."
        )
        args.template_dir.mkdir(parents=True, exist_ok=True)

    # Generate training data
    generator = TemplateTrainingGenerator(
        java_dir=args.java_dir,
        template_dir=args.template_dir,
        mapping_file=args.mapping_file,
        system_instruction=system_instruction,
    )

    stats = generator.generate(
        output_dir=args.output_dir,
        validation_split=args.validation_split,
        include_synthetic=not args.no_synthetic,
    )

    # Print summary
    print("\n" + "=" * 50)
    print("Template Training Data Generation Complete")
    print("=" * 50)
    print(f"Java classes processed: {stats['total_java_classes']}")
    print(f"Templates loaded: {stats['total_templates']}")
    print(f"Matched pairs: {stats['matched_pairs']}")
    print(f"  - Exact matches: {stats['match_breakdown'].get('exact', 0)}")
    print(f"  - Reference matches: {stats['match_breakdown'].get('reference', 0)}")
    print(f"  - Manual matches: {stats['match_breakdown'].get('manual', 0)}")
    print(f"Training examples: {stats['training_examples']}")
    print(f"Validation examples: {stats['validation_examples']}")
    print(f"\nOutput files:")
    print(f"  Train: {stats['output_files']['train']}")
    print(f"  Validation: {stats['output_files']['validation']}")


if __name__ == "__main__":
    main()

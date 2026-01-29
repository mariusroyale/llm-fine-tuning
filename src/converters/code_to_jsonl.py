"""Convert source code to JSONL training format for Vertex AI fine-tuning."""

import json
import random
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from ..extractors.generic_extractor import CodeBlock, GenericExtractor
from ..extractors.java_extractor import JavaClass, JavaExtractor
from .strategies.code_explanation import CodeExplanationStrategy
from .strategies.code_generation import CodeGenerationStrategy
from .strategies.code_review import CodeReviewStrategy
from .strategies.template_generation import TemplateGenerationStrategy


class CodeToJSONLConverter:
    """Convert extracted code into JSONL format for Vertex AI fine-tuning."""

    STRATEGIES = {
        "code_explanation": CodeExplanationStrategy,
        "code_generation": CodeGenerationStrategy,
        "code_review": CodeReviewStrategy,
        "template_generation": TemplateGenerationStrategy,
    }

    def __init__(
        self,
        strategy: str = "code_explanation",
        system_instruction: Optional[str] = None,
        validation_split: float = 0.1,
        max_validation: int = 500,
    ):
        """Initialize the converter.

        Args:
            strategy: The training strategy to use
            system_instruction: Custom system instruction (optional)
            validation_split: Fraction of data for validation (0.0-1.0)
            max_validation: Maximum validation examples
        """
        if strategy not in self.STRATEGIES:
            raise ValueError(
                f"Unknown strategy: {strategy}. Choose from: {list(self.STRATEGIES.keys())}"
            )

        strategy_class = self.STRATEGIES[strategy]
        self.strategy = strategy_class(system_instruction=system_instruction)
        self.validation_split = validation_split
        self.max_validation = max_validation

        # Extractors
        self.java_extractor = JavaExtractor()
        self.generic_extractor = GenericExtractor()

    def convert_directory(
        self,
        source_dir: Path,
        output_dir: Path,
        train_file: str = "train.jsonl",
        validation_file: str = "validation.jsonl",
    ) -> dict:
        """Convert all source files in a directory to training data.

        Args:
            source_dir: Directory containing source code
            output_dir: Directory to write JSONL files
            train_file: Name of training file
            validation_file: Name of validation file

        Returns:
            Statistics about the conversion
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Extract all classes
        java_classes = self.java_extractor.extract_directory(source_dir / "java")
        other_code = self.generic_extractor.extract_directory(source_dir)

        # Generate training examples
        all_examples = []

        for java_class in java_classes:
            examples = self.strategy.generate_class_examples(java_class)
            all_examples.extend(examples)

        # Shuffle for randomness
        random.shuffle(all_examples)

        # Split into train/validation
        n_validation = min(
            int(len(all_examples) * self.validation_split),
            self.max_validation,
        )
        n_training = len(all_examples) - n_validation

        training_examples = all_examples[:n_training]
        validation_examples = all_examples[n_training:]

        # Write JSONL files
        self._write_jsonl(training_examples, output_dir / train_file)
        self._write_jsonl(validation_examples, output_dir / validation_file)

        return {
            "total_classes": len(java_classes),
            "total_examples": len(all_examples),
            "training_examples": len(training_examples),
            "validation_examples": len(validation_examples),
            "strategy": type(self.strategy).__name__,
        }

    def convert_file(self, source_file: Path) -> list[dict]:
        """Convert a single source file to training examples.

        Args:
            source_file: Path to a source file

        Returns:
            List of training examples in JSONL format
        """
        if source_file.suffix == ".java":
            classes = self.java_extractor.extract_file(source_file)
            examples = []
            for java_class in classes:
                class_examples = self.strategy.generate_class_examples(java_class)
                examples.extend(class_examples)
            return [self._to_vertex_format(ex) for ex in examples]
        else:
            # For other languages, use generic extractor
            blocks = self.generic_extractor.extract_file(source_file)
            # TODO: Implement strategies for other languages
            return []

    def _to_vertex_format(self, example) -> dict:
        """Convert a training example to Vertex AI format.

        Format:
        {
            "systemInstruction": {
                "role": "system",
                "parts": [{"text": "..."}]
            },
            "contents": [
                {"role": "user", "parts": [{"text": "..."}]},
                {"role": "model", "parts": [{"text": "..."}]}
            ]
        }
        """
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


def convert_java_to_training_data(
    source_dir: str,
    output_dir: str,
    strategy: str = "code_explanation",
    system_instruction: Optional[str] = None,
) -> dict:
    """Convenience function to convert Java code to training data.

    Args:
        source_dir: Directory containing Java source code
        output_dir: Directory to write JSONL files
        strategy: Training strategy (code_explanation, code_generation, code_review)
        system_instruction: Optional custom system instruction

    Returns:
        Conversion statistics
    """
    converter = CodeToJSONLConverter(
        strategy=strategy,
        system_instruction=system_instruction,
    )

    return converter.convert_directory(
        Path(source_dir),
        Path(output_dir),
    )

#!/usr/bin/env python3
"""Prepare training data from source code."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import click
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.converters.code_to_jsonl import CodeToJSONLConverter

console = Console()


@click.command()
@click.option(
    "--source-dir",
    "-s",
    type=click.Path(exists=True, path_type=Path),
    default=Path("data/raw"),
    help="Directory containing source code",
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path),
    default=Path("data/processed"),
    help="Output directory for JSONL files",
)
@click.option(
    "--strategy",
    "-t",
    type=click.Choice(["code_explanation", "code_generation", "code_review"]),
    default="code_explanation",
    help="Training strategy to use",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    default=Path("config/config.yaml"),
    help="Configuration file",
)
@click.option(
    "--validation-split",
    type=float,
    default=0.1,
    help="Fraction of data for validation (0.0-1.0)",
)
def main(
    source_dir: Path,
    output_dir: Path,
    strategy: str,
    config: Path,
    validation_split: float,
):
    """Prepare training data from source code files.

    This script:
    1. Extracts Java classes and other source code
    2. Converts them to training examples
    3. Outputs train.jsonl and validation.jsonl
    """
    console.print(
        Panel.fit(
            "[bold blue]Google Vertex AI Fine-Tuning[/bold blue]\n"
            "Training Data Preparation",
            border_style="blue",
        )
    )

    # Load config if exists
    cfg = {}
    if config.exists():
        with open(config) as f:
            cfg = yaml.safe_load(f)
        console.print(f"[dim]Loaded config from {config}[/dim]")

    # Get system instruction from config if available
    system_instruction = None
    if "strategy" in cfg and "system_instruction" in cfg["strategy"]:
        system_instruction = cfg["strategy"]["system_instruction"]

    console.print(f"\n[bold]Configuration:[/bold]")
    console.print(f"  Source Directory: {source_dir}")
    console.print(f"  Output Directory: {output_dir}")
    console.print(f"  Strategy: {strategy}")
    console.print(f"  Validation Split: {validation_split:.0%}")
    console.print()

    # Check source directory
    java_dir = source_dir / "java"
    if not java_dir.exists():
        console.print(f"[yellow]Warning: {java_dir} not found[/yellow]")
        console.print(f"[dim]Create this directory and add your Java files[/dim]")

        # Check if there are any files at all
        all_files = list(source_dir.rglob("*"))
        source_files = [
            f
            for f in all_files
            if f.is_file() and f.suffix in [".java", ".py", ".js", ".ts"]
        ]

        if not source_files:
            console.print(f"\n[red]No source files found in {source_dir}[/red]")
            console.print("\n[bold]To get started:[/bold]")
            console.print("  1. Copy your Java files to data/raw/java/")
            console.print("  2. Run this script again")
            return

    # Create converter
    converter = CodeToJSONLConverter(
        strategy=strategy,
        system_instruction=system_instruction,
        validation_split=validation_split,
    )

    # Convert
    console.print("[bold]Processing source files...[/bold]")
    stats = converter.convert_directory(source_dir, output_dir)

    # Display results
    console.print("\n[bold green]Conversion Complete![/bold green]\n")

    table = Table(title="Dataset Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Java Classes Processed", str(stats["total_classes"]))
    table.add_row("Total Examples Generated", str(stats["total_examples"]))
    table.add_row("Training Examples", str(stats["training_examples"]))
    table.add_row("Validation Examples", str(stats["validation_examples"]))
    table.add_row("Strategy Used", stats["strategy"])

    console.print(table)

    # Output files
    console.print(f"\n[bold]Output Files:[/bold]")
    train_file = output_dir / "train.jsonl"
    val_file = output_dir / "validation.jsonl"

    if train_file.exists():
        size_kb = train_file.stat().st_size / 1024
        console.print(f"  [green]{train_file}[/green] ({size_kb:.1f} KB)")

    if val_file.exists():
        size_kb = val_file.stat().st_size / 1024
        console.print(f"  [green]{val_file}[/green] ({size_kb:.1f} KB)")

    # Next steps
    if stats["total_examples"] >= 100:
        console.print("\n[bold]Next Steps:[/bold]")
        console.print("  1. Review generated examples in data/processed/")
        console.print(
            "  2. Upload to GCS: python scripts/run_training.py --upload-only"
        )
        console.print("  3. Start training: python scripts/run_training.py")
    else:
        console.print(
            f"\n[yellow]Warning: Only {stats['total_examples']} examples generated.[/yellow]"
        )
        console.print(
            "Google recommends at least 100 examples for effective fine-tuning."
        )
        console.print("Add more source code to data/raw/java/ and run again.")


if __name__ == "__main__":
    main()

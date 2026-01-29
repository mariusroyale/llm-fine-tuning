#!/usr/bin/env python3
"""Upload data and start fine-tuning on Vertex AI."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import click
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from src.training.monitor import monitor_tuning_job
from src.training.start_tuning import list_tuning_jobs, start_fine_tuning_job
from src.training.upload_data import (
    count_examples,
    estimate_tokens,
    upload_training_data,
)

console = Console()


@click.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    default=Path("config/config.yaml"),
    help="Configuration file",
)
@click.option(
    "--data-dir",
    "-d",
    type=click.Path(exists=True, path_type=Path),
    default=Path("data/processed"),
    help="Directory containing JSONL training files",
)
@click.option(
    "--upload-only",
    is_flag=True,
    help="Only upload data, don't start training",
)
@click.option(
    "--skip-upload",
    is_flag=True,
    help="Skip upload, assume data is already in GCS",
)
@click.option(
    "--monitor/--no-monitor",
    default=True,
    help="Monitor job progress after starting",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be done without executing",
)
def main(
    config: Path,
    data_dir: Path,
    upload_only: bool,
    skip_upload: bool,
    monitor: bool,
    dry_run: bool,
):
    """Upload training data and start fine-tuning on Vertex AI.

    This script:
    1. Uploads training data to Google Cloud Storage
    2. Starts a supervised fine-tuning job
    3. Monitors the job until completion
    """
    console.print(
        Panel.fit(
            "[bold blue]Google Vertex AI Fine-Tuning[/bold blue]\nTraining Pipeline",
            border_style="blue",
        )
    )

    # Load configuration
    with open(config) as f:
        cfg = yaml.safe_load(f)

    gcp_config = cfg.get("gcp", {})
    training_config = cfg.get("training", {})

    project_id = gcp_config.get("project_id")
    location = gcp_config.get("location", "us-central1")
    bucket = gcp_config.get("staging_bucket")

    if project_id == "YOUR_PROJECT_ID":
        console.print(
            "[red]Error: Please update config/config.yaml with your GCP project ID[/red]"
        )
        return

    if bucket == "gs://YOUR_BUCKET_NAME":
        console.print(
            "[red]Error: Please update config/config.yaml with your GCS bucket[/red]"
        )
        return

    # Show configuration
    console.print(f"\n[bold]GCP Configuration:[/bold]")
    console.print(f"  Project: {project_id}")
    console.print(f"  Location: {location}")
    console.print(f"  Bucket: {bucket}")

    console.print(f"\n[bold]Training Configuration:[/bold]")
    console.print(
        f"  Base Model: {training_config.get('base_model', 'gemini-2.5-pro')}"
    )
    console.print(f"  Epochs: {training_config.get('epochs', 3)}")
    console.print(
        f"  Learning Rate Multiplier: {training_config.get('learning_rate_multiplier', 1.0)}"
    )
    console.print(f"  Adapter Size: {training_config.get('adapter_size', 4)}")

    # Check local data
    train_file = data_dir / "train.jsonl"
    val_file = data_dir / "validation.jsonl"

    if train_file.exists():
        n_train = count_examples(train_file)
        tokens = estimate_tokens(train_file)
        console.print(f"\n[bold]Training Data:[/bold]")
        console.print(f"  Training examples: {n_train}")
        console.print(f"  Estimated tokens: {tokens:,}")

        if val_file.exists():
            n_val = count_examples(val_file)
            console.print(f"  Validation examples: {n_val}")

        if n_train < 100:
            console.print(
                f"\n[yellow]Warning: {n_train} training examples is below the recommended minimum of 100[/yellow]"
            )
    else:
        console.print(f"\n[red]Error: Training file not found: {train_file}[/red]")
        console.print("Run: python scripts/prepare_data.py first")
        return

    if dry_run:
        console.print("\n[yellow]DRY RUN - No actions taken[/yellow]")
        return

    console.print()

    # Upload data
    if not skip_upload:
        if not Confirm.ask("Upload training data to GCS?"):
            console.print("[yellow]Upload cancelled[/yellow]")
            return

        console.print("\n[bold]Uploading training data...[/bold]")

        # Extract bucket name
        bucket_name = bucket.replace("gs://", "").rstrip("/")

        uris = upload_training_data(
            local_dir=data_dir,
            bucket_name=bucket_name,
            destination_prefix="training",
        )

        training_uri = uris.get("train.jsonl")
        validation_uri = uris.get("validation.jsonl")

        console.print(f"\n[green]Data uploaded successfully![/green]")
    else:
        # Construct URIs from config
        bucket_name = bucket.replace("gs://", "").rstrip("/")
        training_uri = f"gs://{bucket_name}/{training_config.get('training_data', 'training/train.jsonl')}"
        validation_uri = f"gs://{bucket_name}/{training_config.get('validation_data', 'training/validation.jsonl')}"
        console.print(f"\n[dim]Using existing data in GCS[/dim]")

    if upload_only:
        console.print("\n[bold]Upload complete.[/bold]")
        console.print(f"  Training: {training_uri}")
        console.print(f"  Validation: {validation_uri}")
        console.print("\nTo start training, run without --upload-only flag")
        return

    # Start fine-tuning
    if not Confirm.ask("\nStart fine-tuning job?"):
        console.print("[yellow]Training cancelled[/yellow]")
        return

    console.print("\n[bold]Starting fine-tuning job...[/bold]")

    job_info = start_fine_tuning_job(
        project_id=project_id,
        location=location,
        training_data_uri=training_uri,
        base_model=training_config.get("base_model", "gemini-2.5-pro"),
        validation_data_uri=validation_uri,
        epochs=training_config.get("epochs", 3),
        learning_rate_multiplier=training_config.get("learning_rate_multiplier", 1.0),
        adapter_size=training_config.get("adapter_size", 4),
    )

    # Monitor if requested
    if monitor:
        console.print("\n[bold]Monitoring job progress...[/bold]")
        console.print(
            "[dim]Press Ctrl+C to stop monitoring (job will continue)[/dim]\n"
        )

        try:
            final_info = monitor_tuning_job(
                project_id=project_id,
                location=location,
                job_name=job_info["resource_name"],
                poll_interval=60,
            )

            if "SUCCEEDED" in final_info.get("state", ""):
                console.print(
                    "\n[bold green]Fine-tuning completed successfully![/bold green]"
                )
                if "tuned_model_name" in final_info:
                    console.print(f"\n[bold]Your tuned model:[/bold]")
                    console.print(f"  {final_info['tuned_model_name']}")
                    console.print("\nTo test: python scripts/test_model.py")
        except KeyboardInterrupt:
            console.print(
                "\n[yellow]Monitoring stopped. Job continues in background.[/yellow]"
            )
            console.print(f"Job ID: {job_info['resource_name']}")
            console.print(
                "To resume monitoring: python scripts/run_training.py --monitor-job <job_id>"
            )


if __name__ == "__main__":
    main()

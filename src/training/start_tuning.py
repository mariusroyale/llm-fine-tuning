"""Start fine-tuning jobs on Vertex AI."""

from typing import Optional

from google.cloud import aiplatform
from rich.console import Console
from rich.table import Table

console = Console()


# Supported base models for fine-tuning
SUPPORTED_MODELS = {
    "gemini-2.5-pro": "gemini-2.5-pro-preview-05-06",
    "gemini-2.5-flash": "gemini-2.5-flash-preview-04-17",
    "gemini-2.5-flash-lite": "gemini-2.5-flash-lite-preview-06-17",
    "gemini-2.0-flash": "gemini-2.0-flash-001",
    "gemini-2.0-flash-lite": "gemini-2.0-flash-lite-001",
}


def start_fine_tuning_job(
    project_id: str,
    location: str,
    training_data_uri: str,
    base_model: str = "gemini-2.5-flash",
    tuned_model_display_name: Optional[str] = None,
    validation_data_uri: Optional[str] = None,
    epochs: int = 3,
    learning_rate_multiplier: float = 1.0,
    adapter_size: int = 4,
) -> dict:
    """Start a supervised fine-tuning job on Vertex AI.

    Args:
        project_id: GCP project ID
        location: GCP region (e.g., us-central1)
        training_data_uri: GCS URI to training JSONL file
        base_model: Base model to fine-tune
        tuned_model_display_name: Display name for the tuned model
        validation_data_uri: Optional GCS URI to validation JSONL file
        epochs: Number of training epochs (1-10)
        learning_rate_multiplier: Learning rate adjustment (0.1-10)
        adapter_size: LoRA adapter size (1, 4, 8, 16)

    Returns:
        Dict with job information
    """
    # Validate base model
    if base_model not in SUPPORTED_MODELS:
        raise ValueError(
            f"Unsupported model: {base_model}. "
            f"Supported models: {list(SUPPORTED_MODELS.keys())}"
        )

    # Initialize Vertex AI
    aiplatform.init(project=project_id, location=location)

    # Resolve model name
    source_model = SUPPORTED_MODELS[base_model]

    # Default display name
    if not tuned_model_display_name:
        import datetime

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        tuned_model_display_name = f"{base_model}-tuned-{timestamp}"

    console.print(f"\n[bold]Starting Fine-Tuning Job[/bold]")
    console.print(f"  Base Model: {source_model}")
    console.print(f"  Training Data: {training_data_uri}")
    if validation_data_uri:
        console.print(f"  Validation Data: {validation_data_uri}")
    console.print(f"  Epochs: {epochs}")
    console.print(f"  Learning Rate Multiplier: {learning_rate_multiplier}")
    console.print(f"  Adapter Size: {adapter_size}")
    console.print()

    # Create the tuning job
    sft_tuning_job = aiplatform.SupervisedTuningJob(
        source_model=source_model,
        train_dataset=training_data_uri,
        validation_dataset=validation_data_uri,
        epochs=epochs,
        learning_rate_multiplier=learning_rate_multiplier,
        adapter_size=adapter_size,
        tuned_model_display_name=tuned_model_display_name,
    )

    # Start the job
    sft_tuning_job.run()

    console.print(f"[green]Fine-tuning job started![/green]")
    console.print(f"  Job Name: {sft_tuning_job.name}")
    console.print(f"  Job Resource Name: {sft_tuning_job.resource_name}")

    return {
        "job_name": sft_tuning_job.name,
        "resource_name": sft_tuning_job.resource_name,
        "display_name": tuned_model_display_name,
        "state": str(sft_tuning_job.state),
        "base_model": source_model,
    }


def list_tuning_jobs(
    project_id: str,
    location: str,
    limit: int = 10,
) -> list[dict]:
    """List recent fine-tuning jobs.

    Args:
        project_id: GCP project ID
        location: GCP region
        limit: Maximum number of jobs to return

    Returns:
        List of job information dicts
    """
    aiplatform.init(project=project_id, location=location)

    jobs = aiplatform.SupervisedTuningJob.list()

    results = []
    for i, job in enumerate(jobs):
        if i >= limit:
            break
        results.append(
            {
                "name": job.name,
                "display_name": job.display_name,
                "state": str(job.state),
                "create_time": job.create_time.isoformat() if job.create_time else None,
                "end_time": job.end_time.isoformat() if job.end_time else None,
            }
        )

    # Display as table
    if results:
        table = Table(title="Recent Fine-Tuning Jobs")
        table.add_column("Name", style="cyan")
        table.add_column("State", style="green")
        table.add_column("Created")

        for job in results:
            table.add_row(
                job["display_name"] or job["name"],
                job["state"],
                job["create_time"][:19] if job["create_time"] else "N/A",
            )

        console.print(table)

    return results


def get_tuning_job(
    project_id: str,
    location: str,
    job_name: str,
) -> dict:
    """Get details of a specific tuning job.

    Args:
        project_id: GCP project ID
        location: GCP region
        job_name: The job resource name

    Returns:
        Job information dict
    """
    aiplatform.init(project=project_id, location=location)

    job = aiplatform.SupervisedTuningJob(job_name)

    return {
        "name": job.name,
        "resource_name": job.resource_name,
        "display_name": job.display_name,
        "state": str(job.state),
        "create_time": job.create_time.isoformat() if job.create_time else None,
        "end_time": job.end_time.isoformat() if job.end_time else None,
        "tuned_model_name": job.tuned_model_name
        if hasattr(job, "tuned_model_name")
        else None,
        "tuned_model_endpoint_name": (
            job.tuned_model_endpoint_name
            if hasattr(job, "tuned_model_endpoint_name")
            else None
        ),
    }


def cancel_tuning_job(
    project_id: str,
    location: str,
    job_name: str,
) -> bool:
    """Cancel a running tuning job.

    Args:
        project_id: GCP project ID
        location: GCP region
        job_name: The job resource name

    Returns:
        True if cancelled successfully
    """
    aiplatform.init(project=project_id, location=location)

    job = aiplatform.SupervisedTuningJob(job_name)
    job.cancel()

    console.print(f"[yellow]Cancelled job: {job_name}[/yellow]")
    return True

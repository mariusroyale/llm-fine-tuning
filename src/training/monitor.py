"""Monitor fine-tuning jobs on Vertex AI."""

import time
from typing import Optional

from google.cloud import aiplatform
from rich.console import Console
from rich.live import Live
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()


def monitor_tuning_job(
    project_id: str,
    location: str,
    job_name: str,
    poll_interval: int = 60,
    timeout: Optional[int] = None,
) -> dict:
    """Monitor a fine-tuning job until completion.

    Args:
        project_id: GCP project ID
        location: GCP region
        job_name: The job resource name
        poll_interval: Seconds between status checks
        timeout: Maximum seconds to wait (None for unlimited)

    Returns:
        Final job information
    """
    aiplatform.init(project=project_id, location=location)

    job = aiplatform.SupervisedTuningJob(job_name)

    console.print(f"\n[bold]Monitoring Fine-Tuning Job[/bold]")
    console.print(f"  Job: {job_name}")
    console.print(f"  Poll Interval: {poll_interval}s")
    console.print()

    start_time = time.time()
    last_state = None

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Waiting for job to complete...", total=None)

        while True:
            # Refresh job state
            job = aiplatform.SupervisedTuningJob(job_name)
            current_state = str(job.state)

            # Update progress description
            progress.update(task, description=f"Status: {current_state}")

            # Log state changes
            if current_state != last_state:
                console.print(f"[cyan]State changed: {current_state}[/cyan]")
                last_state = current_state

            # Check for terminal states
            if "SUCCEEDED" in current_state:
                progress.update(
                    task, description="[green]Job completed successfully![/green]"
                )
                break
            elif "FAILED" in current_state:
                progress.update(task, description="[red]Job failed![/red]")
                break
            elif "CANCELLED" in current_state:
                progress.update(task, description="[yellow]Job cancelled[/yellow]")
                break

            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                console.print("[yellow]Timeout reached, stopping monitoring[/yellow]")
                break

            time.sleep(poll_interval)

    # Get final job details
    final_info = {
        "name": job.name,
        "state": str(job.state),
        "create_time": job.create_time.isoformat() if job.create_time else None,
        "end_time": job.end_time.isoformat() if job.end_time else None,
        "duration_seconds": (
            (job.end_time - job.create_time).total_seconds()
            if job.end_time and job.create_time
            else None
        ),
    }

    # Add tuned model info if available
    if hasattr(job, "tuned_model_name") and job.tuned_model_name:
        final_info["tuned_model_name"] = job.tuned_model_name
        console.print(f"\n[green]Tuned Model: {job.tuned_model_name}[/green]")

    if hasattr(job, "tuned_model_endpoint_name") and job.tuned_model_endpoint_name:
        final_info["tuned_model_endpoint_name"] = job.tuned_model_endpoint_name
        console.print(f"[green]Endpoint: {job.tuned_model_endpoint_name}[/green]")

    return final_info


def get_job_metrics(
    project_id: str,
    location: str,
    job_name: str,
) -> Optional[dict]:
    """Get training metrics for a completed job.

    Args:
        project_id: GCP project ID
        location: GCP region
        job_name: The job resource name

    Returns:
        Training metrics if available
    """
    aiplatform.init(project=project_id, location=location)

    job = aiplatform.SupervisedTuningJob(job_name)

    # Note: Metrics availability depends on Vertex AI API version
    # This is a placeholder for when metrics are exposed
    metrics = {}

    if hasattr(job, "training_stats"):
        metrics["training_stats"] = job.training_stats

    if hasattr(job, "tuning_data_stats"):
        metrics["tuning_data_stats"] = job.tuning_data_stats

    return metrics if metrics else None


def display_job_summary(
    project_id: str,
    location: str,
    job_name: str,
) -> None:
    """Display a formatted summary of a tuning job.

    Args:
        project_id: GCP project ID
        location: GCP region
        job_name: The job resource name
    """
    aiplatform.init(project=project_id, location=location)

    job = aiplatform.SupervisedTuningJob(job_name)

    table = Table(title="Fine-Tuning Job Summary")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Job Name", job.name)
    table.add_row("Display Name", job.display_name or "N/A")
    table.add_row("State", str(job.state))

    if job.create_time:
        table.add_row("Created", job.create_time.strftime("%Y-%m-%d %H:%M:%S"))

    if job.end_time:
        table.add_row("Completed", job.end_time.strftime("%Y-%m-%d %H:%M:%S"))

        if job.create_time:
            duration = job.end_time - job.create_time
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            table.add_row("Duration", f"{int(hours)}h {int(minutes)}m {int(seconds)}s")

    if hasattr(job, "tuned_model_name") and job.tuned_model_name:
        table.add_row("Tuned Model", job.tuned_model_name)

    console.print(table)

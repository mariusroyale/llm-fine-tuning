"""Upload training data to Google Cloud Storage."""

from pathlib import Path
from typing import Optional

from google.cloud import storage
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def upload_training_data(
    local_dir: Path,
    bucket_name: str,
    destination_prefix: str = "training",
    train_file: str = "train.jsonl",
    validation_file: str = "validation.jsonl",
) -> dict:
    """Upload training data files to Google Cloud Storage.

    Args:
        local_dir: Local directory containing JSONL files
        bucket_name: GCS bucket name (without gs:// prefix)
        destination_prefix: Prefix path in the bucket
        train_file: Name of training file
        validation_file: Name of validation file

    Returns:
        Dict with GCS URIs for uploaded files
    """
    # Remove gs:// prefix if present
    if bucket_name.startswith("gs://"):
        bucket_name = bucket_name[5:]

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    results = {}

    files_to_upload = [
        (local_dir / train_file, f"{destination_prefix}/{train_file}"),
        (local_dir / validation_file, f"{destination_prefix}/{validation_file}"),
    ]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for local_path, gcs_path in files_to_upload:
            if not local_path.exists():
                console.print(
                    f"[yellow]Warning: {local_path} not found, skipping[/yellow]"
                )
                continue

            task = progress.add_task(f"Uploading {local_path.name}...", total=None)

            blob = bucket.blob(gcs_path)
            blob.upload_from_filename(str(local_path))

            gcs_uri = f"gs://{bucket_name}/{gcs_path}"
            results[local_path.name] = gcs_uri

            progress.update(task, completed=True)
            console.print(f"[green]Uploaded to {gcs_uri}[/green]")

    return results


def validate_gcs_files(
    bucket_name: str,
    file_paths: list[str],
) -> dict:
    """Validate that files exist in GCS and return their sizes.

    Args:
        bucket_name: GCS bucket name
        file_paths: List of file paths to validate

    Returns:
        Dict with file info (exists, size)
    """
    if bucket_name.startswith("gs://"):
        bucket_name = bucket_name[5:]

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    results = {}

    for path in file_paths:
        blob = bucket.blob(path)
        if blob.exists():
            blob.reload()
            results[path] = {
                "exists": True,
                "size_bytes": blob.size,
                "size_mb": round(blob.size / (1024 * 1024), 2),
                "updated": blob.updated.isoformat() if blob.updated else None,
            }
        else:
            results[path] = {"exists": False}

    return results


def download_training_data(
    bucket_name: str,
    source_prefix: str,
    local_dir: Path,
) -> list[Path]:
    """Download training data from GCS.

    Args:
        bucket_name: GCS bucket name
        source_prefix: Prefix path in the bucket
        local_dir: Local directory to download to

    Returns:
        List of downloaded file paths
    """
    if bucket_name.startswith("gs://"):
        bucket_name = bucket_name[5:]

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    local_dir.mkdir(parents=True, exist_ok=True)
    downloaded = []

    blobs = bucket.list_blobs(prefix=source_prefix)

    for blob in blobs:
        if blob.name.endswith("/"):
            continue

        filename = Path(blob.name).name
        local_path = local_dir / filename

        console.print(f"Downloading {blob.name}...")
        blob.download_to_filename(str(local_path))
        downloaded.append(local_path)

    return downloaded


def count_examples(file_path: Path) -> int:
    """Count the number of examples in a JSONL file.

    Args:
        file_path: Path to JSONL file

    Returns:
        Number of lines/examples
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return sum(1 for _ in f)


def estimate_tokens(file_path: Path, chars_per_token: float = 4.0) -> int:
    """Estimate token count for a JSONL file.

    Args:
        file_path: Path to JSONL file
        chars_per_token: Average characters per token (default 4)

    Returns:
        Estimated token count
    """
    size_bytes = file_path.stat().st_size
    # Rough estimate: bytes ≈ chars for ASCII/UTF-8
    return int(size_bytes / chars_per_token)

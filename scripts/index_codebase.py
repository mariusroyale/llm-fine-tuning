#!/usr/bin/env python3
"""Index codebase into vector database for RAG queries."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import click
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.rag.chunker import CodeChunker
from src.rag.embedder import VertexEmbedder
from src.rag.vector_store import PgVectorStore

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
    "--config",
    "-c",
    type=str,
    default=None,
    help="Configuration file path (default: config/config.yaml)",
)
@click.option(
    "--reset",
    is_flag=True,
    help="Drop and recreate the table before indexing",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be indexed without actually indexing",
)
@click.option(
    "--batch-size",
    type=int,
    default=100,
    help="Batch size for embedding API calls",
)
def main(
    source_dir: Path,
    config: str | None,
    reset: bool,
    dry_run: bool,
    batch_size: int,
):
    """Index source code into vector database for RAG queries.

    This script:
    1. Chunks source code into semantic units (classes, methods)
    2. Generates embeddings using Vertex AI
    3. Stores chunks and embeddings in PostgreSQL + pgvector

    Examples:
        # Index codebase
        python scripts/index_codebase.py -s data/raw

        # Reset and reindex
        python scripts/index_codebase.py -s data/raw --reset

        # Dry run to see what would be indexed
        python scripts/index_codebase.py -s data/raw --dry-run
    """
    console.print(
        Panel.fit(
            "[bold blue]Codebase RAG Indexer[/bold blue]\nIndex source code for semantic search",
            border_style="blue",
        )
    )

    # Resolve config path
    if config is None:
        # Try default location relative to script directory
        script_dir = Path(__file__).parent.parent
        config_path = script_dir / "config" / "config.yaml"
    else:
        config_path = Path(config)
    
    # Check if config file exists
    if not config_path.exists():
        console.print(f"[red]Error: Configuration file not found: {config_path}[/red]")
        console.print(f"\n[bold]Tried to find config at:[/bold] {config_path.absolute()}")
        console.print("\nPlease create the configuration file:")
        console.print(f"  1. Create directory: mkdir -p {config_path.parent}")
        console.print(f"  2. Create {config_path} with your GCP settings")
        console.print(f"  3. At minimum, set your GCP project_id in the config file")
        console.print("\nExample config structure:")
        console.print("  gcp:")
        console.print("    project_id: 'your-project-id'")
        console.print("    location: 'us-central1'")
        console.print("  rag:")
        console.print("    pgvector:")
        console.print("      host: 'pgvector'  # or 'localhost' if not in Docker")
        console.print("\nOr specify a different config file with --config /path/to/config.yaml")
        return
    
    config = config_path

    # Load configuration
    try:
        with open(config) as f:
            cfg = yaml.safe_load(f)
    except Exception as e:
        console.print(f"[red]Error loading configuration file: {e}[/red]")
        return

    gcp_config = cfg.get("gcp", {})
    rag_config = cfg.get("rag", {})
    pgvector_config = rag_config.get("pgvector", {})

    project_id = gcp_config.get("project_id")
    location = gcp_config.get("location", "us-central1")

    if project_id == "YOUR_PROJECT_ID":
        console.print(
            "[red]Error: Please update config/config.yaml with your GCP project ID[/red]"
        )
        return

    # Show configuration
    console.print(f"\n[bold]Configuration:[/bold]")
    console.print(f"  Source Directory: {source_dir}")
    console.print(f"  GCP Project: {project_id}")
    console.print(f"  Location: {location}")
    console.print(
        f"  Embedding Model: {rag_config.get('embedding_model', 'text-embedding-005')}"
    )
    console.print(
        f"  Database: {pgvector_config.get('host', 'localhost')}:{pgvector_config.get('port', 5432)}/{pgvector_config.get('database', 'codebase_rag')}"
    )
    console.print()

    # Step 1: Chunk source code
    console.print(
        "[bold]Step 1: Chunking source code, templates, and documents...[/bold]"
    )

    chunker = CodeChunker(
        include_methods=True,
        include_classes=True,
        include_documentation=True,
        include_templates=True,
        include_documents=True,
    )

    chunks = chunker.chunk_directory(source_dir)

    if not chunks:
        console.print(f"[yellow]No content found in {source_dir}[/yellow]")
        console.print("\nMake sure your content is in the correct location:")
        console.print("  - Java files: data/raw/java/")
        console.print("  - JSON templates: data/raw/templates/")
        console.print("  - Documents: data/raw/docs/")
        console.print("  - Other code: data/raw/")
        return

    # Show known classes for cross-referencing
    known_classes = chunker.get_known_classes()
    if known_classes:
        console.print(
            f"\n[dim]Found {len(known_classes)} Java classes for cross-referencing[/dim]"
        )

    # Show chunk statistics
    table = Table(title="Chunk Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="green")

    by_language = {}
    by_type = {}
    chunks_with_refs = 0
    for chunk in chunks:
        by_language[chunk.language] = by_language.get(chunk.language, 0) + 1
        by_type[chunk.chunk_type] = by_type.get(chunk.chunk_type, 0) + 1
        if chunk.references:
            chunks_with_refs += 1

    table.add_row("Total Chunks", str(len(chunks)))
    table.add_row("Chunks with Class References", str(chunks_with_refs))
    table.add_row("", "")
    table.add_row("[bold]By Language[/bold]", "")
    for lang, count in sorted(by_language.items()):
        table.add_row(f"  {lang}", str(count))
    table.add_row("", "")
    table.add_row("[bold]By Type[/bold]", "")
    for chunk_type, count in sorted(by_type.items()):
        table.add_row(f"  {chunk_type}", str(count))

    console.print(table)

    if dry_run:
        console.print("\n[yellow]DRY RUN - No indexing performed[/yellow]")
        console.print("\nSample chunks:")
        for chunk in chunks[:3]:
            console.print(f"\n  [cyan]{chunk.file_path}[/cyan]")
            console.print(
                f"  Type: {chunk.chunk_type}, Lines: {chunk.start_line}-{chunk.end_line}"
            )
            preview = chunk.content[:200].replace("\n", " ")
            console.print(f"  Preview: {preview}...")
        return

    # Step 2: Generate embeddings
    console.print("\n[bold]Step 2: Generating embeddings...[/bold]")

    embedder = VertexEmbedder(
        project_id=project_id,
        location=location,
        model=rag_config.get("embedding_model", "text-embedding-005"),
    )

    chunk_embeddings, skipped_chunks = embedder.embed_chunks(chunks, batch_size=batch_size)
    
    # Extract chunks and embeddings (already filtered - None embeddings removed)
    filtered_chunks = [chunk for chunk, _ in chunk_embeddings]
    embeddings = [emb for _, emb in chunk_embeddings]

    console.print(f"[green]Generated {len(embeddings)} embeddings[/green]")
    
    # Display skipped chunks statistics
    if skipped_chunks:
        console.print(f"\n[yellow]⚠ Skipped {len(skipped_chunks)} chunks:[/yellow]")
        
        # Group by reason
        by_reason = {}
        by_type = {}
        total_tokens_skipped = 0
        
        for skipped in skipped_chunks:
            reason = skipped['reason']
            chunk_type = skipped['chunk_type']
            
            by_reason[reason] = by_reason.get(reason, 0) + 1
            by_type[chunk_type] = by_type.get(chunk_type, 0) + 1
            total_tokens_skipped += skipped['token_count']
        
        # Show summary table
        skip_table = Table(title="Skipped Chunks Summary")
        skip_table.add_column("Reason", style="yellow")
        skip_table.add_column("Count", style="red")
        
        for reason, count in sorted(by_reason.items(), key=lambda x: x[1], reverse=True):
            skip_table.add_row(reason, str(count))
        
        console.print(skip_table)
        
        # Show breakdown by type
        if len(by_type) > 1:
            type_table = Table(title="Skipped by Chunk Type")
            type_table.add_column("Type", style="cyan")
            type_table.add_column("Count", style="red")
            
            for chunk_type, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
                type_table.add_row(chunk_type, str(count))
            
            console.print(type_table)
        
        # Show largest skipped chunks
        largest_skipped = sorted(skipped_chunks, key=lambda x: x['token_count'], reverse=True)[:5]
        console.print(f"\n[bold yellow]Top 5 Largest Skipped Chunks:[/bold yellow]")
        for i, skipped in enumerate(largest_skipped, 1):
            chunk = skipped['chunk']
            console.print(
                f"  {i}. {chunk.file_path}:{chunk.start_line}-{chunk.end_line} "
                f"({skipped['chunk_type']}) - {skipped['token_count']:,} tokens "
                f"({skipped['size_chars']:,} chars)"
            )
        
        console.print(f"\n[dim]Total tokens skipped: {total_tokens_skipped:,}[/dim]")
        console.print(
            "[dim]Tip: Large JSON templates or very long code files may exceed the 15,000 token limit. "
            "Consider splitting them into smaller chunks.[/dim]"
        )

    # Step 3: Store in vector database
    console.print("\n[bold]Step 3: Storing in vector database...[/bold]")

    store = PgVectorStore(
        host=pgvector_config.get("host", "localhost"),
        port=pgvector_config.get("port", 5432),
        database=pgvector_config.get("database", "codebase_rag"),
        user=pgvector_config.get("user", "postgres"),
        password=pgvector_config.get("password"),
        embedding_dimensions=embedder.dimensions,
    )

    try:
        store.connect()

        if reset:
            console.print("[yellow]Resetting table...[/yellow]")
            try:
                store.drop_table()
                console.print("[green]Table dropped[/green]")
            except Exception as e:
                console.print(f"[yellow]Warning during table drop: {e}[/yellow]")
                console.print("[yellow]Continuing anyway...[/yellow]")

        console.print("[dim]Creating table...[/dim]")
        store.create_table()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"Inserting {len(filtered_chunks)} chunks...", 
                total=len(filtered_chunks)
            )
            count = store.upsert(filtered_chunks, embeddings, batch_size=500)
            progress.update(task, completed=len(filtered_chunks))

        # Create vector index after data is inserted (better performance)
        console.print("[dim]Creating vector index...[/dim]")
        try:
            store.create_vector_index()
            console.print("[green]Vector index created[/green]")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not create vector index: {e}[/yellow]")
            console.print("[yellow]Search will still work but may be slower[/yellow]")

        console.print(f"[green]Indexed {count} chunks[/green]")

        # Show final stats
        stats = store.get_stats()
        console.print(f"\n[bold]Database Statistics:[/bold]")
        console.print(f"  Total chunks: {stats['total_chunks']}")
        console.print(f"  Files indexed: {stats['file_count']}")

    except Exception as e:
        console.print(f"[red]Database error: {e}[/red]")
        console.print("\nMake sure PostgreSQL is running with pgvector extension:")
        console.print("  1. Install pgvector: https://github.com/pgvector/pgvector")
        console.print(
            f"  2. Create database: createdb {pgvector_config.get('database', 'codebase_rag')}"
        )
        console.print("  3. Enable extension: CREATE EXTENSION vector;")
        return

    finally:
        store.close()

    console.print("\n[bold green]Indexing complete![/bold green]")
    console.print("\nNext steps:")
    console.print("  Query: python scripts/query_codebase.py -q 'your question'")
    console.print("  Interactive: python scripts/query_codebase.py -i")


if __name__ == "__main__":
    main()

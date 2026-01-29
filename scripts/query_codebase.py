#!/usr/bin/env python3
"""Query codebase using RAG."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import click
import yaml
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.table import Table

from src.rag.embedder import VertexEmbedder
from src.rag.retriever import CodeRetriever, InteractiveRetriever
from src.rag.vector_store import PgVectorStore

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
    "--query",
    "-q",
    type=str,
    default=None,
    help="Single query to run",
)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Start interactive query session",
)
@click.option(
    "--top-k",
    "-k",
    type=int,
    default=5,
    help="Number of code chunks to retrieve",
)
@click.option(
    "--language",
    "-l",
    type=str,
    default=None,
    help="Filter by language (e.g., java, python)",
)
@click.option(
    "--show-sources",
    is_flag=True,
    default=True,
    help="Show source code snippets",
)
@click.option(
    "--retrieve-only",
    is_flag=True,
    help="Only retrieve chunks, don't generate answer",
)
@click.option(
    "--model",
    "-m",
    type=str,
    default=None,
    help="LLM model for generation (overrides config)",
)
@click.option(
    "--with-deps",
    "-d",
    is_flag=True,
    help="Include dependency context (referenced classes, templates)",
)
@click.option(
    "--class-lookup",
    type=str,
    default=None,
    help="Look up a specific class with full dependency context",
)
@click.option(
    "--template-deps",
    type=str,
    default=None,
    help="Find Java dependencies for a specific template",
)
def main(
    config: Path,
    query: str,
    interactive: bool,
    top_k: int,
    language: str,
    show_sources: bool,
    retrieve_only: bool,
    model: str,
    with_deps: bool,
    class_lookup: str,
    template_deps: str,
):
    """Query your codebase using natural language.

    Examples:
        # Single query
        python scripts/query_codebase.py -q "Is user authentication implemented?"

        # Interactive mode
        python scripts/query_codebase.py -i

        # Retrieve only (no LLM generation)
        python scripts/query_codebase.py -q "database connection" --retrieve-only

        # Filter by language
        python scripts/query_codebase.py -q "error handling" -l java

        # Query with dependency context (includes referenced classes)
        python scripts/query_codebase.py -q "UserService template" --with-deps

        # Look up a specific class with all its relationships
        python scripts/query_codebase.py --class-lookup UserService

        # Find Java classes referenced by a template
        python scripts/query_codebase.py --template-deps "config/user-template.json"
    """
    console.print(
        Panel.fit(
            "[bold blue]Codebase RAG Query[/bold blue]\nAsk questions about your code",
            border_style="blue",
        )
    )

    # Load configuration
    with open(config) as f:
        cfg = yaml.safe_load(f)

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

    # Initialize components
    try:
        embedder = VertexEmbedder(
            project_id=project_id,
            location=location,
            model=rag_config.get("embedding_model", "text-embedding-005"),
        )

        store = PgVectorStore(
            host=pgvector_config.get("host", "localhost"),
            port=pgvector_config.get("port", 5432),
            database=pgvector_config.get("database", "codebase_rag"),
            user=pgvector_config.get("user", "postgres"),
            password=pgvector_config.get("password"),
            embedding_dimensions=embedder.dimensions,
        )
        store.connect()

        # Check if database has chunks
        chunk_count = store.count()
        if chunk_count == 0:
            console.print("[yellow]No code indexed yet.[/yellow]")
            console.print("Run: python scripts/index_codebase.py -s data/raw")
            return

        console.print(
            f"[dim]Connected to database with {chunk_count} code chunks[/dim]\n"
        )

        llm_model = model or rag_config.get("llm_model", "gemini-2.5-pro")

        retriever = CodeRetriever(
            embedder=embedder,
            store=store,
            llm_model=llm_model,
            system_prompt=rag_config.get("system_prompt"),
        )

    except Exception as e:
        console.print(f"[red]Connection error: {e}[/red]")
        console.print("\nMake sure:")
        console.print("  1. PostgreSQL is running")
        console.print("  2. Database exists and has been indexed")
        console.print("  3. Run: python scripts/index_codebase.py first")
        return

    # Class lookup mode
    if class_lookup:
        run_class_lookup(retriever, class_lookup, show_sources)
        store.close()
        return

    # Template dependencies mode
    if template_deps:
        run_template_deps(retriever, template_deps, show_sources)
        store.close()
        return

    # Single query mode
    if query and not interactive:
        run_single_query(
            retriever=retriever,
            query=query,
            top_k=top_k,
            language=language,
            show_sources=show_sources,
            retrieve_only=retrieve_only,
            with_deps=with_deps,
        )
        store.close()
        return

    # Interactive mode
    if interactive:
        run_interactive_session(
            retriever=retriever,
            top_k=top_k,
            language=language,
            show_sources=show_sources,
        )
        store.close()
        return

    # No mode specified
    console.print("[bold]Usage:[/bold]")
    console.print(
        "  Single query:  python scripts/query_codebase.py -q 'your question'"
    )
    console.print("  Interactive:   python scripts/query_codebase.py -i")
    store.close()


def run_single_query(
    retriever: CodeRetriever,
    query: str,
    top_k: int,
    language: str,
    show_sources: bool,
    retrieve_only: bool,
    with_deps: bool = False,
):
    """Run a single query."""
    console.print(f"[bold]Query:[/bold] {query}\n")

    if retrieve_only:
        # Just retrieve and display chunks
        results = retriever.retrieve_only(query, top_k=top_k, language=language)
        display_chunks(results, show_code=show_sources)
    else:
        # Full RAG: retrieve + generate
        if with_deps:
            response = retriever.query_with_dependencies(query, top_k=top_k)
        else:
            response = retriever.query(query, top_k=top_k, language=language)

        console.print("[bold]Answer:[/bold]")
        console.print(Panel(Markdown(response.answer)))

        if show_sources and response.sources:
            console.print("\n[bold]Sources:[/bold]")
            display_chunks(
                list(zip(response.sources, response.scores)),
                show_code=True,
            )

        if show_sources and response.dependencies:
            console.print("\n[bold]Dependencies:[/bold]")
            for i, chunk in enumerate(response.dependencies, 1):
                location = f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line}"
                name = chunk.class_name or chunk.file_path
                console.print(f"  [cyan]{i}. {name}[/cyan] [dim]({location})[/dim]")


def run_class_lookup(retriever: CodeRetriever, class_name: str, show_sources: bool):
    """Look up a class with full dependency context."""
    console.print(f"[bold]Looking up class:[/bold] {class_name}\n")

    response = retriever.query_class_with_context(class_name)

    console.print("[bold]Analysis:[/bold]")
    console.print(Panel(Markdown(response.answer)))

    if show_sources and response.sources:
        console.print("\n[bold]Class Code:[/bold]")
        for chunk in response.sources:
            location = f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line}"
            console.print(f"[dim]{location}[/dim]")
            syntax = Syntax(
                chunk.content[:1000] + ("..." if len(chunk.content) > 1000 else ""),
                chunk.language,
                theme="monokai",
                line_numbers=True,
                start_line=chunk.start_line,
            )
            console.print(Panel(syntax, border_style="green"))

    if response.dependencies:
        console.print("\n[bold]Related Code (Dependencies & References):[/bold]")
        for i, chunk in enumerate(response.dependencies, 1):
            location = f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line}"
            name = chunk.class_name or chunk.file_path
            chunk_type = chunk.chunk_type or "code"
            console.print(f"\n[cyan]{i}. {name}[/cyan] ({chunk_type})")
            console.print(f"   [dim]{location}[/dim]")

            if show_sources:
                preview = chunk.content[:500] + (
                    "..." if len(chunk.content) > 500 else ""
                )
                syntax = Syntax(
                    preview,
                    chunk.language,
                    theme="monokai",
                    line_numbers=True,
                    start_line=chunk.start_line,
                )
                console.print(Panel(syntax, border_style="dim"))


def run_template_deps(retriever: CodeRetriever, template_path: str, show_sources: bool):
    """Find Java dependencies for a template."""
    console.print(f"[bold]Finding dependencies for template:[/bold] {template_path}\n")

    response = retriever.find_template_dependencies(template_path)

    console.print("[bold]Analysis:[/bold]")
    console.print(Panel(Markdown(response.answer)))

    if show_sources and response.sources:
        console.print("\n[bold]Template:[/bold]")
        for chunk in response.sources:
            location = f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line}"
            console.print(f"[dim]{location}[/dim]")
            if chunk.references:
                console.print(
                    f"[yellow]References: {', '.join(chunk.references)}[/yellow]"
                )
            syntax = Syntax(
                chunk.content[:1500] + ("..." if len(chunk.content) > 1500 else ""),
                chunk.language,
                theme="monokai",
                line_numbers=True,
                start_line=chunk.start_line,
            )
            console.print(Panel(syntax, border_style="blue"))

    if response.dependencies:
        console.print("\n[bold]Java Class Dependencies:[/bold]")
        for i, chunk in enumerate(response.dependencies, 1):
            location = f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line}"
            console.print(f"\n[cyan]{i}. {chunk.class_name}[/cyan]")
            console.print(f"   [dim]{location}[/dim]")

            if show_sources:
                preview = chunk.content[:500] + (
                    "..." if len(chunk.content) > 500 else ""
                )
                syntax = Syntax(
                    preview,
                    chunk.language,
                    theme="monokai",
                    line_numbers=True,
                    start_line=chunk.start_line,
                )
                console.print(Panel(syntax, border_style="green"))


def display_chunks(results: list, show_code: bool = True):
    """Display retrieved code chunks."""
    for i, (chunk, score) in enumerate(results, 1):
        location = f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line}"
        name = chunk.method_name or chunk.class_name or chunk.file_path

        console.print(f"\n[cyan]{i}. {name}[/cyan]")
        console.print(f"   [dim]{location} (score: {score:.3f})[/dim]")

        if chunk.documentation:
            doc_preview = chunk.documentation[:150].replace("\n", " ")
            console.print(f"   [italic]{doc_preview}...[/italic]")

        if show_code:
            # Show code with syntax highlighting
            code_preview = chunk.content
            if len(code_preview) > 500:
                code_preview = code_preview[:500] + "\n// ... truncated"

            syntax = Syntax(
                code_preview,
                chunk.language,
                theme="monokai",
                line_numbers=True,
                start_line=chunk.start_line,
            )
            console.print(Panel(syntax, border_style="dim"))


def run_interactive_session(
    retriever: CodeRetriever,
    top_k: int,
    language: str,
    show_sources: bool,
):
    """Run interactive query session."""
    console.print("[bold green]Interactive Session Started[/bold green]")
    console.print(
        "[dim]Commands: 'exit' to quit, 'clear' to reset, 'sources' to toggle source display[/dim]"
    )
    console.print()

    interactive = InteractiveRetriever(retriever)
    show_src = show_sources

    while True:
        try:
            user_input = Prompt.ask("[bold cyan]You[/bold cyan]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Session ended[/yellow]")
            break

        if user_input.lower() in ("exit", "quit"):
            console.print("[yellow]Session ended[/yellow]")
            break

        if user_input.lower() == "clear":
            interactive.clear_history()
            console.print("[dim]Conversation cleared[/dim]")
            continue

        if user_input.lower() == "sources":
            show_src = not show_src
            console.print(f"[dim]Source display: {'on' if show_src else 'off'}[/dim]")
            continue

        if not user_input.strip():
            continue

        # Query
        response = interactive.query(user_input, top_k=top_k)

        console.print()
        console.print("[bold green]Assistant:[/bold green]")
        console.print(Panel(Markdown(response.answer)))

        if show_src and response.sources:
            console.print("\n[dim]Sources:[/dim]")
            for i, (chunk, score) in enumerate(
                zip(response.sources[:3], response.scores[:3]), 1
            ):
                location = f"{chunk.file_path}:{chunk.start_line}"
                console.print(f"  [dim]{i}. {location} (score: {score:.3f})[/dim]")

        console.print()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Query codebase using RAG."""

import sys
from pathlib import Path
from typing import Optional

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
    type=str,
    default=None,
    help="Configuration file path (default: config/config.yaml)",
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
@click.option(
    "--list-classes",
    is_flag=True,
    help="List all indexed Java classes",
)
def main(
    config: str | None,
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
    list_classes: bool,
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
            store=store,  # Pass store for list queries
        )
        store.close()
        return

    # Interactive mode
    if interactive:
        run_interactive_session(
            retriever=retriever,
            store=store,
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


def run_list_classes(store: PgVectorStore, language: Optional[str] = None):
    """List all indexed classes."""
    classes = store.list_classes(language=language)
    
    if not classes:
        console.print("[yellow]No classes found in the database.[/yellow]")
        return
    
    # Group by language
    by_language = {}
    for cls in classes:
        lang = cls.language
        if lang not in by_language:
            by_language[lang] = []
        by_language[lang].append(cls)
    
    console.print(f"\n[bold]Found {len(classes)} indexed classes:[/bold]\n")
    
    for lang in sorted(by_language.keys()):
        lang_classes = by_language[lang]
        console.print(f"[bold cyan]{lang.upper()} Classes ({len(lang_classes)}):[/bold cyan]")
        
        # Sort by class name
        lang_classes.sort(key=lambda c: c.class_name or c.file_path)
        
        for cls in lang_classes:
            class_name = cls.class_name or Path(cls.file_path).stem
            location = f"{cls.file_path}:{cls.start_line}-{cls.end_line}"
            console.print(f"  • {class_name} ({location})")
        
        console.print()


def run_single_query(
    retriever: CodeRetriever,
    query: str,
    top_k: int,
    language: str,
    show_sources: bool,
    retrieve_only: bool,
    with_deps: bool = False,
    store: Optional[PgVectorStore] = None,
):
    """Run a single query."""
    console.print(f"[bold]Query:[/bold] {query}\n")

    # Check if query is asking to list classes
    query_lower = query.lower()
    list_classes_patterns = [
        "list all",
        "list the",
        "show all",
        "show the",
        "which are",
        "what are",
        "how many",
        "count",
    ]
    class_keywords = ["class", "classes", "java class", "java classes"]
    
    is_list_query = any(pattern in query_lower for pattern in list_classes_patterns)
    has_class_keyword = any(keyword in query_lower for keyword in class_keywords)
    
    # If asking to list classes and we have store access, use direct query
    if is_list_query and has_class_keyword and store:
        # Extract language if specified
        detected_language = language
        if not detected_language:
            if "java" in query_lower:
                detected_language = "java"
            elif "python" in query_lower:
                detected_language = "python"
            elif "javascript" in query_lower or "typescript" in query_lower:
                detected_language = "javascript" if "javascript" in query_lower else "typescript"
        
        classes = store.list_classes(language=detected_language)
        
        if classes:
            console.print(f"[bold green]Found {len(classes)} indexed classes:[/bold green]\n")
            
            # Group by language
            by_language = {}
            for cls in classes:
                lang = cls.language
                if lang not in by_language:
                    by_language[lang] = []
                by_language[lang].append(cls)
            
            for lang in sorted(by_language.keys()):
                lang_classes = by_language[lang]
                console.print(f"[bold cyan]{lang.upper()} Classes ({len(lang_classes)}):[/bold cyan]")
                
                # Sort by class name
                lang_classes.sort(key=lambda c: c.class_name or c.file_path)
                
                for cls in lang_classes:
                    class_name = cls.class_name or Path(cls.file_path).stem
                    location = f"{cls.file_path}:{cls.start_line}-{cls.end_line}"
                    console.print(f"  • {class_name} ({location})")
                
                console.print()
            
            # Also generate a natural language answer using RAG
            # Use a query that will trigger the list detection in the retriever
            console.print("\n[bold]Summary:[/bold]")
            # Use "list" and "indexed" keywords to trigger complete list detection
            summary_query = f"List all {len(classes)} classes indexed in the codebase"
            if with_deps:
                response = retriever.query_with_dependencies(
                    summary_query,
                    top_k=min(20, len(classes))
                )
            else:
                response = retriever.query(
                    summary_query,
                    top_k=min(20, len(classes)),
                    language=detected_language,
                    chunk_type="class"  # Force class chunk type to trigger list detection
                )
            console.print(Panel(Markdown(response.answer)))
            return

    # Determine chunk_type and adjust top_k for class queries
    chunk_type = None
    adjusted_top_k = top_k
    
    query_lower = query.lower()
    if "class" in query_lower or "classes" in query_lower:
        chunk_type = "class"
        # Increase top_k for class queries to get more context
        adjusted_top_k = max(top_k * 3, 20)

    if retrieve_only:
        # Just retrieve and display chunks
        results = retriever.retrieve_only(query, top_k=adjusted_top_k, language=language)
        display_chunks(results, show_code=show_sources)
    else:
        # Full RAG: retrieve + generate
        if with_deps:
            response = retriever.query_with_dependencies(query, top_k=adjusted_top_k)
        else:
            # Use chunk_type filter for class queries
            response = retriever.query(
                query, 
                top_k=adjusted_top_k, 
                language=language,
                chunk_type=chunk_type
            )

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
    store: PgVectorStore,
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
        
        # Detect if query is about classes and adjust retrieval
        query_lower = user_input.lower()
        class_keywords = ["class", "classes"]
        is_class_query = any(keyword in query_lower for keyword in class_keywords)
        
        chunk_type = None
        adjusted_top_k = top_k
        detected_language = language
        
        if is_class_query:
            chunk_type = "class"
            adjusted_top_k = max(top_k * 3, 20)  # Get more classes
            
            # Extract language from query if not specified
            if not detected_language:
                if "java" in query_lower:
                    detected_language = "java"
                elif "python" in query_lower:
                    detected_language = "python"
                elif "javascript" in query_lower:
                    detected_language = "javascript"
                elif "typescript" in query_lower:
                    detected_language = "typescript"

        if user_input.lower() == "sources":
            show_src = not show_src
            console.print(f"[dim]Source display: {'on' if show_src else 'off'}[/dim]")
            continue

        if not user_input.strip():
            continue

        # Query with appropriate filters for class queries
        if is_class_query:
            response = retriever.query(
                user_input, 
                top_k=adjusted_top_k, 
                language=detected_language,
                chunk_type=chunk_type
            )
        else:
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

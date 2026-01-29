#!/usr/bin/env python3
"""Test and interact with fine-tuned models."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import click
import yaml
from google import genai
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

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
    "--model",
    "-m",
    type=str,
    default=None,
    help="Tuned model name (overrides config)",
)
@click.option(
    "--prompt",
    "-p",
    type=str,
    default=None,
    help="Single prompt to test",
)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Start interactive chat session",
)
@click.option(
    "--compare",
    is_flag=True,
    help="Compare with base model",
)
@click.option(
    "--base-model",
    type=str,
    default="gemini-2.5-flash",
    help="Base model for comparison",
)
def main(
    config: Path,
    model: str,
    prompt: str,
    interactive: bool,
    compare: bool,
    base_model: str,
):
    """Test fine-tuned models with prompts.

    Examples:
        # Single prompt
        python scripts/test_model.py -m "models/your-tuned-model" -p "Explain the UserService class"

        # Interactive mode
        python scripts/test_model.py -m "models/your-tuned-model" -i

        # Compare with base model
        python scripts/test_model.py -m "models/your-tuned-model" -p "..." --compare
    """
    console.print(
        Panel.fit(
            "[bold blue]Google Vertex AI Fine-Tuning[/bold blue]\nModel Testing",
            border_style="blue",
        )
    )

    # Load configuration
    with open(config) as f:
        cfg = yaml.safe_load(f)

    gcp_config = cfg.get("gcp", {})
    project_id = gcp_config.get("project_id")
    location = gcp_config.get("location", "us-central1")

    if project_id == "YOUR_PROJECT_ID":
        console.print(
            "[red]Error: Please update config/config.yaml with your GCP project ID[/red]"
        )
        return

    # Initialize client
    client = genai.Client(
        vertexai=True,
        project=project_id,
        location=location,
    )

    # Get model name
    if not model:
        console.print(
            "[yellow]No model specified. Use --model to specify your tuned model.[/yellow]"
        )
        console.print("\nTo find your tuned model name:")
        console.print("  1. Check the output of your training job")
        console.print(
            "  2. Or visit: https://console.cloud.google.com/vertex-ai/tuning"
        )
        return

    console.print(f"\n[bold]Model:[/bold] {model}")

    # Get system instruction from config
    strategy_config = cfg.get("strategy", {})
    system_instruction = strategy_config.get("system_instruction")

    if system_instruction:
        console.print(f"[dim]System instruction loaded from config[/dim]")

    # Single prompt mode
    if prompt and not interactive:
        console.print(f"\n[bold]Prompt:[/bold] {prompt}\n")

        response = generate_response(client, model, prompt, system_instruction)

        console.print("[bold]Response:[/bold]")
        console.print(Panel(Markdown(response)))

        if compare:
            console.print(f"\n[bold]Base Model ({base_model}) Response:[/bold]")
            base_response = generate_response(
                client, base_model, prompt, system_instruction
            )
            console.print(Panel(Markdown(base_response)))

        return

    # Interactive mode
    if interactive:
        interactive_session(client, model, system_instruction, compare, base_model)
        return

    # Default: show usage
    console.print("\n[bold]Usage:[/bold]")
    console.print(
        "  Single prompt:  python scripts/test_model.py -m MODEL -p 'your prompt'"
    )
    console.print("  Interactive:    python scripts/test_model.py -m MODEL -i")
    console.print(
        "  Compare:        python scripts/test_model.py -m MODEL -p 'prompt' --compare"
    )


def generate_response(
    client,
    model: str,
    prompt: str,
    system_instruction: str = None,
) -> str:
    """Generate a response from the model."""
    try:
        config = {
            "temperature": 0.7,
            "max_output_tokens": 2048,
        }
        if system_instruction:
            config["system_instruction"] = system_instruction

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )
        return response.text
    except Exception as e:
        return f"Error: {e}"


def interactive_session(
    client,
    model: str,
    system_instruction: str = None,
    compare: bool = False,
    base_model: str = "gemini-2.5-flash",
):
    """Run an interactive chat session."""
    console.print("\n[bold green]Interactive Session Started[/bold green]")
    console.print("[dim]Type 'exit' or 'quit' to end the session[/dim]")
    console.print("[dim]Type 'clear' to clear conversation history[/dim]")

    if compare:
        console.print(f"[dim]Comparing with base model: {base_model}[/dim]")

    console.print()

    history = []

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
            history = []
            console.print("[dim]Conversation cleared[/dim]")
            continue

        if not user_input.strip():
            continue

        # Generate response
        history.append({"role": "user", "parts": [{"text": user_input}]})

        console.print()

        try:
            config = {
                "temperature": 0.7,
                "max_output_tokens": 2048,
            }
            if system_instruction:
                config["system_instruction"] = system_instruction

            response = client.models.generate_content(
                model=model,
                contents=history,
                config=config,
            )

            assistant_message = response.text
            history.append({"role": "model", "parts": [{"text": assistant_message}]})

            console.print("[bold green]Tuned Model:[/bold green]")
            console.print(Panel(Markdown(assistant_message)))

            if compare:
                # Also get base model response
                base_response = client.models.generate_content(
                    model=base_model,
                    contents=history[:-1],  # Exclude the model response we just added
                    config=config,
                )
                console.print(f"\n[bold blue]Base Model ({base_model}):[/bold blue]")
                console.print(Panel(Markdown(base_response.text)))

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

        console.print()


if __name__ == "__main__":
    main()

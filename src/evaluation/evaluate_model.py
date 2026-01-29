"""Evaluate fine-tuned models."""

import json
from typing import Optional

from google import genai
from google.cloud import aiplatform
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def evaluate_tuned_model(
    project_id: str,
    location: str,
    model_name: str,
    test_prompts: list[dict],
    system_instruction: Optional[str] = None,
) -> list[dict]:
    """Evaluate a fine-tuned model with test prompts.

    Args:
        project_id: GCP project ID
        location: GCP region
        model_name: The tuned model resource name
        test_prompts: List of test prompts with expected outputs
        system_instruction: Optional system instruction

    Returns:
        List of evaluation results
    """
    # Initialize the Gemini client
    client = genai.Client(
        vertexai=True,
        project=project_id,
        location=location,
    )

    results = []

    console.print(f"\n[bold]Evaluating Model: {model_name}[/bold]\n")

    for i, test in enumerate(test_prompts):
        prompt = test["prompt"]
        expected = test.get("expected")

        console.print(f"[cyan]Test {i + 1}:[/cyan] {prompt[:100]}...")

        try:
            # Generate response
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={
                    "system_instruction": system_instruction,
                    "temperature": 0.1,  # Low temp for consistency
                    "max_output_tokens": 2048,
                },
            )

            actual = response.text

            result = {
                "prompt": prompt,
                "expected": expected,
                "actual": actual,
                "success": True,
            }

            # Simple similarity check if expected is provided
            if expected:
                similarity = _calculate_similarity(expected, actual)
                result["similarity"] = similarity
                console.print(f"  Similarity: {similarity:.2%}")

            console.print(Panel(actual[:500] + "..." if len(actual) > 500 else actual))

        except Exception as e:
            result = {
                "prompt": prompt,
                "expected": expected,
                "actual": None,
                "success": False,
                "error": str(e),
            }
            console.print(f"  [red]Error: {e}[/red]")

        results.append(result)

    # Summary
    _display_summary(results)

    return results


def compare_models(
    project_id: str,
    location: str,
    base_model: str,
    tuned_model: str,
    test_prompts: list[dict],
    system_instruction: Optional[str] = None,
) -> dict:
    """Compare base model vs tuned model responses.

    Args:
        project_id: GCP project ID
        location: GCP region
        base_model: The base model name
        tuned_model: The tuned model resource name
        test_prompts: List of test prompts
        system_instruction: Optional system instruction

    Returns:
        Comparison results
    """
    client = genai.Client(
        vertexai=True,
        project=project_id,
        location=location,
    )

    results = []

    console.print(f"\n[bold]Comparing Models[/bold]")
    console.print(f"  Base: {base_model}")
    console.print(f"  Tuned: {tuned_model}\n")

    for i, test in enumerate(test_prompts):
        prompt = test["prompt"]

        console.print(f"[cyan]Test {i + 1}:[/cyan] {prompt[:80]}...")

        comparison = {"prompt": prompt}

        for model_type, model_name in [("base", base_model), ("tuned", tuned_model)]:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={
                        "system_instruction": system_instruction,
                        "temperature": 0.1,
                        "max_output_tokens": 2048,
                    },
                )
                comparison[f"{model_type}_response"] = response.text
            except Exception as e:
                comparison[f"{model_type}_response"] = f"Error: {e}"

        results.append(comparison)

        # Display side by side
        table = Table(title=f"Test {i + 1}")
        table.add_column("Base Model", width=50)
        table.add_column("Tuned Model", width=50)

        base_resp = comparison.get("base_response", "")[:200]
        tuned_resp = comparison.get("tuned_response", "")[:200]
        table.add_row(base_resp, tuned_resp)
        console.print(table)
        console.print()

    return {"comparisons": results}


def _calculate_similarity(expected: str, actual: str) -> float:
    """Calculate simple text similarity.

    Uses Jaccard similarity on word sets.
    """
    expected_words = set(expected.lower().split())
    actual_words = set(actual.lower().split())

    if not expected_words and not actual_words:
        return 1.0
    if not expected_words or not actual_words:
        return 0.0

    intersection = expected_words & actual_words
    union = expected_words | actual_words

    return len(intersection) / len(union)


def _display_summary(results: list[dict]) -> None:
    """Display evaluation summary."""
    total = len(results)
    successful = sum(1 for r in results if r["success"])
    failed = total - successful

    similarities = [r["similarity"] for r in results if "similarity" in r]
    avg_similarity = sum(similarities) / len(similarities) if similarities else 0

    console.print("\n[bold]Evaluation Summary[/bold]")

    table = Table()
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Tests", str(total))
    table.add_row("Successful", str(successful))
    table.add_row("Failed", str(failed))
    if similarities:
        table.add_row("Avg Similarity", f"{avg_similarity:.2%}")

    console.print(table)


def generate_test_prompts(examples_file: str, num_tests: int = 10) -> list[dict]:
    """Generate test prompts from training examples.

    Args:
        examples_file: Path to JSONL training file
        num_tests: Number of test prompts to generate

    Returns:
        List of test prompts
    """
    import random

    test_prompts = []

    with open(examples_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Sample random examples
    samples = random.sample(lines, min(num_tests, len(lines)))

    for line in samples:
        example = json.loads(line)
        contents = example.get("contents", [])

        if len(contents) >= 2:
            user_content = contents[0]
            model_content = contents[1]

            if (
                user_content.get("role") == "user"
                and model_content.get("role") == "model"
            ):
                prompt = user_content["parts"][0]["text"]
                expected = model_content["parts"][0]["text"]

                test_prompts.append(
                    {
                        "prompt": prompt,
                        "expected": expected,
                    }
                )

    return test_prompts

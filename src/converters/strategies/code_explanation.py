"""Strategy for generating code explanation training examples."""

import random
from dataclasses import dataclass
from typing import Optional

from ...extractors.java_extractor import JavaClass, JavaMethod


@dataclass
class TrainingExample:
    """A single training example for fine-tuning."""

    system_instruction: str
    user_prompt: str
    model_response: str


class CodeExplanationStrategy:
    """Generate training examples for code explanation tasks.

    This strategy creates examples where:
    - User asks about what code does
    - Model explains the code in detail

    This is ideal for building a code assistant that understands your codebase.
    """

    DEFAULT_SYSTEM_INSTRUCTION = """You are an expert software developer with deep knowledge of Java, design patterns, and software architecture. You understand code thoroughly and can explain complex implementations clearly and concisely.

When analyzing code:
- Explain the purpose and responsibility of each class/method
- Identify design patterns used
- Describe key algorithms and data structures
- Note integration points with other components
- Highlight important implementation details"""

    USER_PROMPT_TEMPLATES = [
        "Explain what this Java class does:\n\n```java\n{code}\n```",
        "What is the purpose of the `{class_name}` class?\n\n```java\n{code}\n```",
        "Describe the main functionality implemented in this code:\n\n```java\n{code}\n```",
        "How does the `{class_name}` class work? Explain its design.\n\n```java\n{code}\n```",
        "Analyze this Java code and explain its structure:\n\n```java\n{code}\n```",
        "What does this code do and how is it organized?\n\n```java\n{code}\n```",
    ]

    METHOD_PROMPT_TEMPLATES = [
        "Explain what the `{method_name}` method does:\n\n```java\n{code}\n```",
        "What is the purpose of this method?\n\n```java\n{code}\n```",
        "Describe the logic in the `{method_name}` method:\n\n```java\n{code}\n```",
        "How does this method work?\n\n```java\n{code}\n```",
    ]

    def __init__(
        self,
        system_instruction: Optional[str] = None,
        prompt_templates: Optional[list[str]] = None,
    ):
        self.system_instruction = system_instruction or self.DEFAULT_SYSTEM_INSTRUCTION
        self.prompt_templates = prompt_templates or self.USER_PROMPT_TEMPLATES

    def generate_class_examples(self, java_class: JavaClass) -> list[TrainingExample]:
        """Generate training examples for a Java class."""
        examples = []

        # Generate class-level explanation
        class_example = self._generate_class_explanation(java_class)
        if class_example:
            examples.append(class_example)

        # Generate method-level explanations for significant methods
        for method in java_class.methods:
            if self._is_significant_method(method):
                method_example = self._generate_method_explanation(java_class, method)
                if method_example:
                    examples.append(method_example)

        return examples

    def _generate_class_explanation(
        self, java_class: JavaClass
    ) -> Optional[TrainingExample]:
        """Generate a training example explaining a class."""
        # Build the code context
        code = java_class.source_code

        # Select a random prompt template
        template = random.choice(self.prompt_templates)
        user_prompt = template.format(code=code, class_name=java_class.name)

        # Generate the model response (explanation)
        model_response = self._create_class_explanation(java_class)

        return TrainingExample(
            system_instruction=self.system_instruction,
            user_prompt=user_prompt,
            model_response=model_response,
        )

    def _generate_method_explanation(
        self, java_class: JavaClass, method: JavaMethod
    ) -> Optional[TrainingExample]:
        """Generate a training example explaining a method."""
        template = random.choice(self.METHOD_PROMPT_TEMPLATES)
        user_prompt = template.format(method_name=method.name, code=method.body)

        model_response = self._create_method_explanation(java_class, method)

        return TrainingExample(
            system_instruction=self.system_instruction,
            user_prompt=user_prompt,
            model_response=model_response,
        )

    def _create_class_explanation(self, java_class: JavaClass) -> str:
        """Create a detailed explanation of a Java class.

        NOTE: In production, you should either:
        1. Use an LLM to generate these explanations from your code
        2. Manually write high-quality explanations
        3. Use existing documentation/comments

        This template provides structure for the explanation.
        """
        parts = []

        # Class overview
        parts.append(f"The `{java_class.name}` class is a {java_class.class_type}")

        if java_class.extends:
            parts.append(f" that extends `{java_class.extends}`")

        if java_class.implements:
            parts.append(
                f" and implements {', '.join(f'`{i}`' for i in java_class.implements)}"
            )

        parts.append(".\n\n")

        # Documentation if available
        if java_class.documentation:
            parts.append(
                f"**Purpose:** {self._clean_javadoc(java_class.documentation)}\n\n"
            )

        # Fields summary
        if java_class.fields:
            parts.append("**Key Fields:**\n")
            for field in java_class.fields[:5]:  # Limit to 5
                parts.append(f"- `{field['name']}` ({field['type']}): ")
                parts.append(f"{'private ' if 'private' in field['modifiers'] else ''}")
                parts.append("field for internal state\n")
            parts.append("\n")

        # Methods summary
        if java_class.methods:
            parts.append("**Key Methods:**\n")
            for method in java_class.methods[:7]:  # Limit to 7
                params = ", ".join([f"{t} {n}" for t, n in method.parameters])
                parts.append(f"- `{method.name}({params})`: ")
                if method.documentation:
                    parts.append(f"{self._clean_javadoc(method.documentation)[:100]}\n")
                else:
                    parts.append(f"handles {method.name} logic\n")
            parts.append("\n")

        # Design patterns if detectable
        patterns = self._detect_patterns(java_class)
        if patterns:
            parts.append(
                f"**Design Patterns:** This class uses {', '.join(patterns)}.\n\n"
            )

        # Package context
        if java_class.package:
            parts.append(f"**Package:** Located in `{java_class.package}`")

        return "".join(parts)

    def _create_method_explanation(
        self, java_class: JavaClass, method: JavaMethod
    ) -> str:
        """Create an explanation for a method."""
        parts = []

        parts.append(f"The `{method.name}` method in `{java_class.name}` ")

        # Return type
        if method.return_type and method.return_type != "void":
            parts.append(f"returns a `{method.return_type}` ")
        else:
            parts.append("performs an operation ")

        # Parameters
        if method.parameters:
            param_desc = ", ".join([f"`{n}` ({t})" for t, n in method.parameters])
            parts.append(f"taking parameters: {param_desc}.\n\n")
        else:
            parts.append("with no parameters.\n\n")

        # Documentation
        if method.documentation:
            parts.append(
                f"**Description:** {self._clean_javadoc(method.documentation)}\n\n"
            )

        # Modifiers
        if method.modifiers:
            parts.append(f"**Modifiers:** {', '.join(method.modifiers)}\n")

        return "".join(parts)

    def _is_significant_method(self, method: JavaMethod) -> bool:
        """Check if a method is significant enough for training."""
        # Skip trivial methods
        trivial_prefixes = ["get", "set", "is", "has", "toString", "hashCode", "equals"]

        for prefix in trivial_prefixes:
            if method.name.startswith(prefix) and len(method.name) <= len(prefix) + 10:
                return False

        # Skip very short methods
        if len(method.body.strip()) < 50:
            return False

        return True

    def _clean_javadoc(self, javadoc: str) -> str:
        """Clean up Javadoc text."""
        # Remove Javadoc markers
        text = javadoc.replace("/**", "").replace("*/", "").replace("*", "")
        # Remove common tags
        import re

        text = re.sub(r"@\w+\s+\S+", "", text)
        # Clean whitespace
        text = " ".join(text.split())
        return text.strip()

    def _detect_patterns(self, java_class: JavaClass) -> list[str]:
        """Detect common design patterns in the class."""
        patterns = []

        # Singleton detection
        for method in java_class.methods:
            if method.name == "getInstance" and "static" in method.modifiers:
                patterns.append("Singleton pattern")
                break

        # Factory detection
        if "Factory" in java_class.name:
            patterns.append("Factory pattern")

        # Builder detection
        if "Builder" in java_class.name:
            patterns.append("Builder pattern")

        # Observer detection
        for impl in java_class.implements:
            if "Listener" in impl or "Observer" in impl:
                patterns.append("Observer pattern")
                break

        # Repository/DAO detection
        if any(x in java_class.name for x in ["Repository", "Dao", "DAO"]):
            patterns.append("Repository pattern")

        # Service detection
        if "Service" in java_class.name:
            patterns.append("Service layer pattern")

        return patterns

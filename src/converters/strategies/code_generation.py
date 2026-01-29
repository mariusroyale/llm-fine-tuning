"""Strategy for generating code generation training examples."""

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


class CodeGenerationStrategy:
    """Generate training examples for code generation tasks.

    This strategy creates examples where:
    - User describes what they want
    - Model generates code matching your project's style

    This teaches the model to write code like YOUR codebase.
    """

    DEFAULT_SYSTEM_INSTRUCTION = """You are an expert Java developer. Generate clean, well-structured code that follows best practices and established patterns. Your code should be:
- Well-organized and readable
- Properly documented with Javadoc
- Following Java naming conventions
- Using appropriate design patterns
- Handling errors gracefully"""

    USER_PROMPT_TEMPLATES = [
        "Create a Java class that {description}",
        "Write a {class_type} called `{class_name}` that {description}",
        "Implement a method that {description}",
        "Generate code for {description}",
        "Write a Java implementation for {description}",
    ]

    def __init__(
        self,
        system_instruction: Optional[str] = None,
    ):
        self.system_instruction = system_instruction or self.DEFAULT_SYSTEM_INSTRUCTION

    def generate_class_examples(self, java_class: JavaClass) -> list[TrainingExample]:
        """Generate training examples from a Java class."""
        examples = []

        # Generate class creation example
        class_example = self._generate_class_creation_example(java_class)
        if class_example:
            examples.append(class_example)

        # Generate method implementation examples
        for method in java_class.methods:
            if self._is_interesting_method(method):
                method_example = self._generate_method_example(java_class, method)
                if method_example:
                    examples.append(method_example)

        return examples

    def _generate_class_creation_example(
        self, java_class: JavaClass
    ) -> Optional[TrainingExample]:
        """Generate an example for creating a class like this one."""
        # Create a description based on the class
        description = self._describe_class_purpose(java_class)

        user_prompt = random.choice(
            [
                f"Create a Java {java_class.class_type} called `{java_class.name}` that {description}",
                f"Write a {java_class.class_type} named `{java_class.name}` for {description}",
                f"Implement a Java {java_class.class_type} `{java_class.name}`: {description}",
            ]
        )

        # The model response is the actual class code
        model_response = self._format_class_code(java_class)

        return TrainingExample(
            system_instruction=self.system_instruction,
            user_prompt=user_prompt,
            model_response=model_response,
        )

    def _generate_method_example(
        self, java_class: JavaClass, method: JavaMethod
    ) -> Optional[TrainingExample]:
        """Generate an example for implementing a method."""
        description = self._describe_method_purpose(method)

        params_desc = ""
        if method.parameters:
            params_desc = (
                f" It takes {', '.join([f'{t} {n}' for t, n in method.parameters])}."
            )

        return_desc = ""
        if method.return_type and method.return_type != "void":
            return_desc = f" It should return a {method.return_type}."

        user_prompt = f"Write a Java method `{method.name}` that {description}.{params_desc}{return_desc}"

        model_response = f"```java\n{method.body}\n```"

        return TrainingExample(
            system_instruction=self.system_instruction,
            user_prompt=user_prompt,
            model_response=model_response,
        )

    def _describe_class_purpose(self, java_class: JavaClass) -> str:
        """Generate a natural language description of what the class does."""
        parts = []

        # Use Javadoc if available
        if java_class.documentation:
            doc = self._clean_javadoc(java_class.documentation)
            if len(doc) > 20:
                return doc[:200]

        # Otherwise infer from class name and structure
        if java_class.implements:
            parts.append(f"implements {', '.join(java_class.implements)}")

        if java_class.extends:
            parts.append(f"extends {java_class.extends}")

        # Infer from naming patterns
        name = java_class.name
        if "Service" in name:
            parts.append("provides business logic services")
        elif "Controller" in name:
            parts.append("handles HTTP requests")
        elif "Repository" in name or "Dao" in name:
            parts.append("manages data persistence")
        elif "Factory" in name:
            parts.append("creates instances of objects")
        elif "Handler" in name:
            parts.append("handles specific events or requests")
        elif "Manager" in name:
            parts.append("manages lifecycle and operations")
        elif "Util" in name or "Helper" in name:
            parts.append("provides utility functions")
        elif "Config" in name:
            parts.append("manages configuration")

        if not parts:
            parts.append("handles domain logic")

        return " and ".join(parts)

    def _describe_method_purpose(self, method: JavaMethod) -> str:
        """Generate a description of what a method does."""
        if method.documentation:
            doc = self._clean_javadoc(method.documentation)
            if len(doc) > 20:
                return doc[:150]

        # Infer from method name
        name = method.name
        if name.startswith("create"):
            return f"creates a new {name[6:] or 'instance'}"
        elif name.startswith("find"):
            return f"finds {name[4:] or 'items'}"
        elif name.startswith("delete") or name.startswith("remove"):
            return f"removes {name[6:] or name[6:]}"
        elif name.startswith("update"):
            return f"updates {name[6:] or 'the record'}"
        elif name.startswith("save"):
            return f"saves {name[4:] or 'the data'}"
        elif name.startswith("process"):
            return f"processes {name[7:] or 'the input'}"
        elif name.startswith("validate"):
            return f"validates {name[8:] or 'the input'}"
        elif name.startswith("convert") or name.startswith("transform"):
            return f"converts {name[7:] or name[9:]} to the target format"
        elif name.startswith("calculate") or name.startswith("compute"):
            return f"calculates {name[9:] or name[7:]}"

        return f"performs the {self._split_camel_case(name)} operation"

    def _is_interesting_method(self, method: JavaMethod) -> bool:
        """Check if a method is worth creating an example for."""
        # Skip getters/setters
        if method.name.startswith(("get", "set", "is", "has")):
            if len(method.body.strip().splitlines()) <= 3:
                return False

        # Skip standard Object methods
        if method.name in ("toString", "hashCode", "equals", "clone"):
            return False

        # Skip very short methods
        if len(method.body.strip()) < 100:
            return False

        return True

    def _format_class_code(self, java_class: JavaClass) -> str:
        """Format the class code as a response."""
        return f"```java\n{java_class.source_code}\n```"

    def _clean_javadoc(self, javadoc: str) -> str:
        """Clean up Javadoc text."""
        import re

        text = javadoc.replace("/**", "").replace("*/", "").replace("*", "")
        text = re.sub(r"@\w+\s+\S+", "", text)
        text = " ".join(text.split())
        return text.strip()

    def _split_camel_case(self, name: str) -> str:
        """Split camelCase into words."""
        import re

        words = re.sub("([A-Z])", r" \1", name).split()
        return " ".join(words).lower()

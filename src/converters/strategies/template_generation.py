"""Strategy for generating JSON template training examples from Java code."""

import json
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ...extractors.java_extractor import JavaClass, JavaMethod


@dataclass
class TrainingExample:
    """A single training example for fine-tuning."""

    system_instruction: str
    user_prompt: str
    model_response: str


@dataclass
class TemplateExample:
    """A paired Java class and its corresponding JSON template."""

    java_class: JavaClass
    template_path: Path
    template_content: dict


class TemplateGenerationStrategy:
    """Generate training examples for JSON template generation from Java classes.

    This strategy creates examples where:
    - User provides a Java class
    - Model generates a corresponding JSON template in your format

    This teaches the model to create JSON templates that match your
    project's template conventions based on Java class structure.
    """

    DEFAULT_SYSTEM_INSTRUCTION = """You are an expert at analyzing Java code and generating corresponding JSON templates. You understand:
- Java class structure, fields, methods, and inheritance
- How to map Java types to JSON schema representations
- The project's JSON template conventions and patterns
- Dependencies between classes and how they should be reflected in templates

When generating JSON templates:
- Analyze the Java class's fields and their types
- Include appropriate metadata and type mappings
- Reference related classes by their names
- Follow the established template structure used in this project
- Preserve relationships and dependencies between components"""

    USER_PROMPT_TEMPLATES = [
        "Generate a JSON template for this Java class:\n\n```java\n{code}\n```",
        "Create a template configuration for the `{class_name}` class:\n\n```java\n{code}\n```",
        "Based on this Java class, generate the corresponding JSON template:\n\n```java\n{code}\n```",
        "Write a JSON template that represents the `{class_name}` class structure:\n\n```java\n{code}\n```",
        "Convert this Java class to a JSON template format:\n\n```java\n{code}\n```",
        "I need a JSON template for this class. Analyze its structure and generate the appropriate template:\n\n```java\n{code}\n```",
    ]

    def __init__(
        self,
        system_instruction: Optional[str] = None,
        template_dir: Optional[Path] = None,
        template_examples: Optional[list[TemplateExample]] = None,
    ):
        """Initialize the strategy.

        Args:
            system_instruction: Custom system instruction (optional)
            template_dir: Directory containing existing JSON templates
            template_examples: Pre-loaded template examples for training
        """
        self.system_instruction = system_instruction or self.DEFAULT_SYSTEM_INSTRUCTION
        self.template_dir = template_dir
        self.template_examples = template_examples or []
        self._class_template_map: dict[str, dict] = {}

        if template_dir:
            self._load_templates(template_dir)

    def _load_templates(self, template_dir: Path) -> None:
        """Load existing JSON templates for pairing with Java classes."""
        if not template_dir.exists():
            return

        for template_file in template_dir.rglob("*.json"):
            try:
                with open(template_file, "r", encoding="utf-8") as f:
                    template = json.load(f)

                # Try to identify which class this template corresponds to
                class_names = self._extract_class_references(template)
                for class_name in class_names:
                    if class_name not in self._class_template_map:
                        self._class_template_map[class_name] = {
                            "path": template_file,
                            "content": template,
                        }
            except (json.JSONDecodeError, IOError):
                continue

    def _extract_class_references(self, obj: any, found: set = None) -> set[str]:
        """Extract Java class names referenced in a JSON structure."""
        if found is None:
            found = set()

        # PascalCase class name pattern
        class_pattern = re.compile(r"^[A-Z][a-zA-Z0-9]+(?:[A-Z][a-zA-Z0-9]+)*$")

        if isinstance(obj, dict):
            for key, value in obj.items():
                # Check if key or value looks like a class name
                if isinstance(key, str) and class_pattern.match(key):
                    found.add(key)
                if isinstance(value, str) and class_pattern.match(value):
                    found.add(value)
                # Recurse into nested structures
                self._extract_class_references(value, found)
        elif isinstance(obj, list):
            for item in obj:
                self._extract_class_references(item, found)

        return found

    def add_template_example(
        self, java_class: JavaClass, template_path: Path, template_content: dict
    ) -> None:
        """Add a paired example of Java class and its template."""
        self.template_examples.append(
            TemplateExample(
                java_class=java_class,
                template_path=template_path,
                template_content=template_content,
            )
        )

    def generate_class_examples(self, java_class: JavaClass) -> list[TrainingExample]:
        """Generate training examples for a Java class.

        If we have a corresponding template, use it as the ground truth.
        Otherwise, generate a template based on the class structure.
        """
        examples = []

        # Check if we have a real template for this class
        if java_class.name in self._class_template_map:
            template_data = self._class_template_map[java_class.name]
            example = self._generate_from_real_template(
                java_class, template_data["content"]
            )
            if example:
                examples.append(example)
        else:
            # Generate a template based on class structure
            # This is useful for bootstrap training
            example = self._generate_from_class_structure(java_class)
            if example:
                examples.append(example)

        return examples

    def generate_paired_examples(self) -> list[TrainingExample]:
        """Generate examples from pre-loaded template pairs.

        Use this when you have explicit Java class + template pairs.
        """
        examples = []
        for template_example in self.template_examples:
            example = self._generate_from_real_template(
                template_example.java_class,
                template_example.template_content,
            )
            if example:
                examples.append(example)
        return examples

    def _generate_from_real_template(
        self, java_class: JavaClass, template: dict
    ) -> Optional[TrainingExample]:
        """Generate a training example using a real template as ground truth."""
        template_str = random.choice(self.USER_PROMPT_TEMPLATES)
        user_prompt = template_str.format(
            code=java_class.source_code,
            class_name=java_class.name,
        )

        # Format the template nicely
        model_response = self._format_template_response(java_class, template)

        return TrainingExample(
            system_instruction=self.system_instruction,
            user_prompt=user_prompt,
            model_response=model_response,
        )

    def _generate_from_class_structure(
        self, java_class: JavaClass
    ) -> Optional[TrainingExample]:
        """Generate a training example by inferring a template from class structure.

        This creates synthetic templates based on class analysis,
        useful when you don't have existing templates.
        """
        # Skip simple classes
        if not java_class.fields and len(java_class.methods) < 2:
            return None

        template_str = random.choice(self.USER_PROMPT_TEMPLATES)
        user_prompt = template_str.format(
            code=java_class.source_code,
            class_name=java_class.name,
        )

        # Generate a template based on class analysis
        inferred_template = self._infer_template(java_class)
        model_response = self._format_template_response(java_class, inferred_template)

        return TrainingExample(
            system_instruction=self.system_instruction,
            user_prompt=user_prompt,
            model_response=model_response,
        )

    def _infer_template(self, java_class: JavaClass) -> dict:
        """Infer a JSON template structure from a Java class."""
        template = {
            "name": java_class.name,
            "type": java_class.class_type,
            "package": java_class.package,
        }

        # Add parent class info
        if java_class.extends:
            template["extends"] = java_class.extends

        # Add interface implementations
        if java_class.implements:
            template["implements"] = java_class.implements

        # Map fields to schema properties
        if java_class.fields:
            template["properties"] = {}
            for field_info in java_class.fields:
                field_name = field_info["name"]
                field_type = field_info["type"]
                template["properties"][field_name] = {
                    "type": self._java_type_to_json_type(field_type),
                    "javaType": field_type,
                }

                # Check if field type is a class reference
                if self._is_class_reference(field_type):
                    template["properties"][field_name]["$ref"] = field_type

        # Add method signatures
        if java_class.methods:
            template["methods"] = []
            for method in java_class.methods:
                if not self._is_trivial_method(method):
                    method_info = {
                        "name": method.name,
                        "returnType": method.return_type,
                        "parameters": [
                            {"name": name, "type": ptype}
                            for ptype, name in method.parameters
                        ],
                    }
                    if method.modifiers:
                        method_info["modifiers"] = method.modifiers
                    template["methods"].append(method_info)

        # Detect dependencies (referenced classes)
        dependencies = self._find_dependencies(java_class)
        if dependencies:
            template["dependencies"] = list(dependencies)

        return template

    def _java_type_to_json_type(self, java_type: str) -> str:
        """Map Java types to JSON schema types."""
        type_map = {
            "String": "string",
            "int": "integer",
            "Integer": "integer",
            "long": "integer",
            "Long": "integer",
            "double": "number",
            "Double": "number",
            "float": "number",
            "Float": "number",
            "boolean": "boolean",
            "Boolean": "boolean",
            "void": "null",
        }

        # Handle generics like List<String>
        base_type = java_type.split("<")[0].strip()

        if base_type in type_map:
            return type_map[base_type]

        if base_type in ("List", "ArrayList", "Set", "HashSet", "Collection"):
            return "array"

        if base_type in ("Map", "HashMap", "TreeMap"):
            return "object"

        # Default to object for complex types
        return "object"

    def _is_class_reference(self, java_type: str) -> bool:
        """Check if a type is likely a class reference (not primitive)."""
        primitives = {
            "String",
            "int",
            "Integer",
            "long",
            "Long",
            "double",
            "Double",
            "float",
            "Float",
            "boolean",
            "Boolean",
            "void",
            "byte",
            "Byte",
            "short",
            "Short",
            "char",
            "Character",
            "Object",
        }
        base_type = java_type.split("<")[0].strip()
        return base_type not in primitives and base_type[0].isupper()

    def _is_trivial_method(self, method: JavaMethod) -> bool:
        """Check if a method is trivial (getter/setter/standard)."""
        trivial_names = {"get", "set", "is", "has", "toString", "hashCode", "equals"}
        for prefix in trivial_names:
            if method.name.startswith(prefix) or method.name == prefix:
                return True
        return False

    def _find_dependencies(self, java_class: JavaClass) -> set[str]:
        """Find class references in the Java class."""
        dependencies = set()
        class_pattern = re.compile(r"\b([A-Z][a-zA-Z0-9]+)\b")

        # Check source code for class references
        for match in class_pattern.finditer(java_class.source_code):
            potential_class = match.group(1)
            # Filter out common Java classes and the class itself
            if potential_class not in {
                java_class.name,
                "String",
                "Integer",
                "Long",
                "Double",
                "Float",
                "Boolean",
                "List",
                "Map",
                "Set",
                "Object",
                "Class",
                "Override",
                "Deprecated",
                "SuppressWarnings",
                "FunctionalInterface",
                "Nullable",
                "NonNull",
                "NotNull",
                "Autowired",
                "Component",
                "Service",
                "Repository",
                "Controller",
                "Entity",
                "Table",
                "Column",
            }:
                dependencies.add(potential_class)

        return dependencies

    def _format_template_response(self, java_class: JavaClass, template: dict) -> str:
        """Format the template as a model response."""
        explanation = self._generate_explanation(java_class, template)
        template_json = json.dumps(template, indent=2)

        return f"""{explanation}

```json
{template_json}
```

This template captures the structure of `{java_class.name}` including its fields, methods, and dependencies."""

    def _generate_explanation(self, java_class: JavaClass, template: dict) -> str:
        """Generate an explanation to accompany the template."""
        parts = [f"Here's the JSON template for the `{java_class.name}` class:"]

        if java_class.extends:
            parts.append(f"\nIt extends `{java_class.extends}`.")

        if java_class.implements:
            parts.append(
                f"\nIt implements {', '.join(f'`{i}`' for i in java_class.implements)}."
            )

        if "dependencies" in template and template["dependencies"]:
            parts.append(
                f"\nThe class depends on: {', '.join(f'`{d}`' for d in template['dependencies'][:5])}."
            )

        return " ".join(parts)

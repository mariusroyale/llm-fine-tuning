"""Strategy for generating code review training examples."""

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


class CodeReviewStrategy:
    """Generate training examples for code review tasks.

    This strategy creates examples where:
    - User submits code for review
    - Model provides constructive feedback

    Ideal for building a code review assistant that understands your standards.
    """

    DEFAULT_SYSTEM_INSTRUCTION = """You are a senior software engineer conducting code reviews. Provide constructive, specific feedback focusing on:
- Code quality and readability
- Design patterns and architecture
- Performance considerations
- Error handling and edge cases
- Testing implications
- Security concerns if applicable

Be specific, cite line numbers when relevant, and suggest concrete improvements."""

    def __init__(
        self,
        system_instruction: Optional[str] = None,
        review_aspects: Optional[list[str]] = None,
    ):
        self.system_instruction = system_instruction or self.DEFAULT_SYSTEM_INSTRUCTION
        self.review_aspects = review_aspects or [
            "code quality",
            "design patterns",
            "performance",
            "error handling",
            "naming conventions",
            "documentation",
        ]

    def generate_class_examples(self, java_class: JavaClass) -> list[TrainingExample]:
        """Generate code review training examples from a Java class."""
        examples = []

        # Generate full class review
        class_review = self._generate_class_review(java_class)
        if class_review:
            examples.append(class_review)

        # Generate focused reviews on specific aspects
        aspect = random.choice(self.review_aspects)
        focused_review = self._generate_focused_review(java_class, aspect)
        if focused_review:
            examples.append(focused_review)

        return examples

    def _generate_class_review(
        self, java_class: JavaClass
    ) -> Optional[TrainingExample]:
        """Generate a comprehensive class review example."""
        user_prompt = random.choice(
            [
                f"Please review this Java class:\n\n```java\n{java_class.source_code}\n```",
                f"Code review for `{java_class.name}`:\n\n```java\n{java_class.source_code}\n```",
                f"Review this code and provide feedback:\n\n```java\n{java_class.source_code}\n```",
            ]
        )

        # Generate the review based on class analysis
        model_response = self._create_class_review(java_class)

        return TrainingExample(
            system_instruction=self.system_instruction,
            user_prompt=user_prompt,
            model_response=model_response,
        )

    def _generate_focused_review(
        self, java_class: JavaClass, aspect: str
    ) -> Optional[TrainingExample]:
        """Generate a review focused on a specific aspect."""
        user_prompt = f"Review this code focusing on {aspect}:\n\n```java\n{java_class.source_code}\n```"

        model_response = self._create_focused_review(java_class, aspect)

        return TrainingExample(
            system_instruction=self.system_instruction,
            user_prompt=user_prompt,
            model_response=model_response,
        )

    def _create_class_review(self, java_class: JavaClass) -> str:
        """Create a comprehensive code review.

        NOTE: For production training data, you should:
        1. Use actual code review comments from your team
        2. Have an LLM generate detailed reviews
        3. Manually write high-quality review feedback

        This generates a template-based review as a starting point.
        """
        parts = []

        parts.append(f"## Code Review: `{java_class.name}`\n\n")

        # Overall assessment
        parts.append("### Overall Assessment\n")
        parts.append(self._assess_overall(java_class))
        parts.append("\n\n")

        # Structure analysis
        parts.append("### Structure & Design\n")
        parts.append(self._analyze_structure(java_class))
        parts.append("\n\n")

        # Method analysis
        if java_class.methods:
            parts.append("### Methods Review\n")
            for method in java_class.methods[:5]:
                parts.append(self._review_method(method))
            parts.append("\n")

        # Suggestions
        suggestions = self._generate_suggestions(java_class)
        if suggestions:
            parts.append("### Recommendations\n")
            for i, suggestion in enumerate(suggestions, 1):
                parts.append(f"{i}. {suggestion}\n")

        return "".join(parts)

    def _assess_overall(self, java_class: JavaClass) -> str:
        """Generate overall assessment."""
        assessments = []

        # Check documentation
        if java_class.documentation:
            assessments.append(
                "The class has documentation, which is good for maintainability."
            )
        else:
            assessments.append(
                "Consider adding class-level Javadoc to explain the purpose and usage."
            )

        # Check class size
        method_count = len(java_class.methods)
        if method_count > 15:
            assessments.append(
                f"With {method_count} methods, consider splitting into smaller, focused classes."
            )
        elif method_count < 3:
            assessments.append(
                "The class is small and focused, which is good for single responsibility."
            )

        # Check inheritance
        if java_class.extends and java_class.implements:
            assessments.append(
                "The class uses both inheritance and interfaces, review if composition might be simpler."
            )

        return " ".join(assessments)

    def _analyze_structure(self, java_class: JavaClass) -> str:
        """Analyze class structure."""
        parts = []

        # Fields analysis
        if java_class.fields:
            private_fields = [
                f for f in java_class.fields if "private" in f.get("modifiers", [])
            ]
            public_fields = [
                f for f in java_class.fields if "public" in f.get("modifiers", [])
            ]

            if public_fields:
                parts.append(
                    f"- Consider making the {len(public_fields)} public field(s) private with accessors for better encapsulation.\n"
                )
            if private_fields:
                parts.append(
                    f"- Good use of encapsulation with {len(private_fields)} private field(s).\n"
                )

        # Check for patterns
        patterns = self._detect_patterns(java_class)
        if patterns:
            parts.append(f"- Implements: {', '.join(patterns)}\n")

        if not parts:
            parts.append("- Structure follows standard Java conventions.\n")

        return "".join(parts)

    def _review_method(self, method: JavaMethod) -> str:
        """Review a single method."""
        issues = []

        # Check documentation
        if not method.documentation:
            issues.append("missing Javadoc")

        # Check parameter count
        if len(method.parameters) > 5:
            issues.append(f"high parameter count ({len(method.parameters)})")

        # Check method length
        lines = len(method.body.strip().splitlines())
        if lines > 30:
            issues.append(f"long method ({lines} lines)")

        if issues:
            return f"- `{method.name}`: {', '.join(issues)}\n"
        else:
            return f"- `{method.name}`: looks good\n"

    def _generate_suggestions(self, java_class: JavaClass) -> list[str]:
        """Generate improvement suggestions."""
        suggestions = []

        # Documentation suggestions
        undocumented_methods = [m for m in java_class.methods if not m.documentation]
        if len(undocumented_methods) > 3:
            suggestions.append(
                f"Add Javadoc to {len(undocumented_methods)} undocumented public methods"
            )

        # Consider builder pattern
        if len(java_class.fields) > 5:
            suggestions.append(
                "With many fields, consider implementing a Builder pattern for construction"
            )

        # Interface extraction
        if len(java_class.methods) > 10 and not java_class.implements:
            suggestions.append(
                "Consider extracting an interface for improved testability and flexibility"
            )

        return suggestions

    def _create_focused_review(self, java_class: JavaClass, aspect: str) -> str:
        """Create a review focused on a specific aspect."""
        parts = [f"## {aspect.title()} Review: `{java_class.name}`\n\n"]

        if aspect == "code quality":
            parts.append(self._review_code_quality(java_class))
        elif aspect == "design patterns":
            parts.append(self._review_design_patterns(java_class))
        elif aspect == "performance":
            parts.append(self._review_performance(java_class))
        elif aspect == "error handling":
            parts.append(self._review_error_handling(java_class))
        elif aspect == "naming conventions":
            parts.append(self._review_naming(java_class))
        elif aspect == "documentation":
            parts.append(self._review_documentation(java_class))
        else:
            parts.append(f"Review of {aspect} aspects...\n")

        return "".join(parts)

    def _review_code_quality(self, java_class: JavaClass) -> str:
        return """**Code Quality Assessment:**

- Check for code duplication across methods
- Verify proper separation of concerns
- Ensure methods have single responsibility
- Look for magic numbers that should be constants
"""

    def _review_design_patterns(self, java_class: JavaClass) -> str:
        patterns = self._detect_patterns(java_class)
        if patterns:
            return f"**Detected Patterns:** {', '.join(patterns)}\n\nPatterns are correctly implemented."
        return "**No common design patterns detected.** Consider if any patterns would improve the design."

    def _review_performance(self, java_class: JavaClass) -> str:
        return """**Performance Considerations:**

- Review loops for potential optimization
- Check for unnecessary object creation
- Consider lazy initialization for expensive operations
- Verify efficient collection usage
"""

    def _review_error_handling(self, java_class: JavaClass) -> str:
        return """**Error Handling Review:**

- Verify exceptions are caught at appropriate levels
- Check that error messages are informative
- Ensure resources are properly closed (try-with-resources)
- Consider using custom exceptions for domain errors
"""

    def _review_naming(self, java_class: JavaClass) -> str:
        parts = [f"**Naming Conventions Review:**\n\n"]
        parts.append(f"- Class name `{java_class.name}`: ")
        if java_class.name[0].isupper():
            parts.append("follows PascalCase convention ✓\n")
        else:
            parts.append("should use PascalCase\n")

        for method in java_class.methods[:3]:
            parts.append(f"- Method `{method.name}`: ")
            if method.name[0].islower():
                parts.append("follows camelCase convention ✓\n")
            else:
                parts.append("should use camelCase\n")

        return "".join(parts)

    def _review_documentation(self, java_class: JavaClass) -> str:
        parts = ["**Documentation Review:**\n\n"]

        if java_class.documentation:
            parts.append("- Class has documentation ✓\n")
        else:
            parts.append("- Missing class-level documentation\n")

        documented = sum(1 for m in java_class.methods if m.documentation)
        total = len(java_class.methods)
        parts.append(f"- {documented}/{total} methods have Javadoc\n")

        return "".join(parts)

    def _detect_patterns(self, java_class: JavaClass) -> list[str]:
        """Detect design patterns."""
        patterns = []

        for method in java_class.methods:
            if method.name == "getInstance" and "static" in method.modifiers:
                patterns.append("Singleton")

        if "Factory" in java_class.name:
            patterns.append("Factory")
        if "Builder" in java_class.name:
            patterns.append("Builder")

        for impl in java_class.implements:
            if "Listener" in impl:
                patterns.append("Observer")

        return patterns

"""Code chunking for RAG pipeline."""

import hashlib
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..extractors.generic_extractor import GenericExtractor
from ..extractors.java_extractor import JavaExtractor


@dataclass
class CodeChunk:
    """Represents a chunk of code for embedding and retrieval."""

    id: str
    content: str
    language: str
    chunk_type: str  # class, method, function, module
    file_path: str
    start_line: int
    end_line: int
    class_name: Optional[str] = None
    method_name: Optional[str] = None
    documentation: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "content": self.content,
            "language": self.language,
            "chunk_type": self.chunk_type,
            "file_path": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "class_name": self.class_name,
            "method_name": self.method_name,
            "documentation": self.documentation,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CodeChunk":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            content=data["content"],
            language=data["language"],
            chunk_type=data["chunk_type"],
            file_path=data["file_path"],
            start_line=data["start_line"],
            end_line=data["end_line"],
            class_name=data.get("class_name"),
            method_name=data.get("method_name"),
            documentation=data.get("documentation"),
            metadata=data.get("metadata", {}),
        )


class CodeChunker:
    """Chunk source code into semantic units for embedding."""

    def __init__(
        self,
        include_methods: bool = True,
        include_classes: bool = True,
        include_documentation: bool = True,
        max_chunk_lines: int = 200,
        min_chunk_lines: int = 3,
    ):
        """Initialize the chunker.

        Args:
            include_methods: Include individual methods as chunks
            include_classes: Include full classes as chunks
            include_documentation: Include docstrings/Javadoc in chunks
            max_chunk_lines: Maximum lines per chunk
            min_chunk_lines: Minimum lines per chunk (skip tiny chunks)
        """
        self.include_methods = include_methods
        self.include_classes = include_classes
        self.include_documentation = include_documentation
        self.max_chunk_lines = max_chunk_lines
        self.min_chunk_lines = min_chunk_lines

        self.java_extractor = JavaExtractor(
            include_private=True,
            include_comments=include_documentation,
        )
        self.generic_extractor = GenericExtractor()

    def chunk_directory(
        self,
        source_dir: Path,
        base_path: Optional[Path] = None,
    ) -> list[CodeChunk]:
        """Chunk all source files in a directory.

        Args:
            source_dir: Directory containing source code
            base_path: Base path for relative file paths (defaults to source_dir)

        Returns:
            List of code chunks
        """
        if base_path is None:
            base_path = source_dir

        chunks = []

        # Process Java files
        java_dir = source_dir / "java"
        if java_dir.exists():
            java_classes = self.java_extractor.extract_directory(java_dir)
            for java_class in java_classes:
                class_chunks = self._chunk_java_class(java_class, base_path)
                chunks.extend(class_chunks)

        # Process other language files
        for ext in self.generic_extractor.LANGUAGE_EXTENSIONS:
            for file_path in source_dir.rglob(f"*{ext}"):
                # Skip Java files (already processed)
                if file_path.suffix == ".java":
                    continue
                file_chunks = self._chunk_generic_file(file_path, base_path)
                chunks.extend(file_chunks)

        return chunks

    def chunk_file(
        self, file_path: Path, base_path: Optional[Path] = None
    ) -> list[CodeChunk]:
        """Chunk a single source file.

        Args:
            file_path: Path to the source file
            base_path: Base path for relative file paths

        Returns:
            List of code chunks
        """
        if base_path is None:
            base_path = file_path.parent

        if file_path.suffix == ".java":
            java_classes = self.java_extractor.extract_file(file_path)
            chunks = []
            for java_class in java_classes:
                class_chunks = self._chunk_java_class(java_class, base_path)
                chunks.extend(class_chunks)
            return chunks
        else:
            return self._chunk_generic_file(file_path, base_path)

    def _chunk_java_class(self, java_class, base_path: Path) -> list[CodeChunk]:
        """Create chunks from a Java class."""
        chunks = []
        relative_path = self._get_relative_path(java_class.file_path, base_path)

        # Create class-level chunk
        if self.include_classes:
            class_content = self._build_java_class_content(java_class)
            lines = class_content.splitlines()

            if len(lines) >= self.min_chunk_lines:
                # If class is too large, just include signature + doc
                if len(lines) > self.max_chunk_lines:
                    class_content = self._build_java_class_summary(java_class)

                chunks.append(
                    CodeChunk(
                        id=self._generate_id(relative_path, java_class.name, "class"),
                        content=class_content,
                        language="java",
                        chunk_type="class",
                        file_path=relative_path,
                        start_line=1,
                        end_line=len(java_class.source_code.splitlines()),
                        class_name=java_class.name,
                        documentation=java_class.documentation,
                        metadata={
                            "package": java_class.package,
                            "class_type": java_class.class_type,
                            "extends": java_class.extends,
                            "implements": java_class.implements,
                        },
                    )
                )

        # Create method-level chunks
        if self.include_methods:
            for method in java_class.methods:
                method_content = self._build_method_content(method, java_class)
                lines = method_content.splitlines()

                if len(lines) < self.min_chunk_lines:
                    continue
                if len(lines) > self.max_chunk_lines:
                    # Truncate very long methods
                    method_content = (
                        "\n".join(lines[: self.max_chunk_lines]) + "\n// ... truncated"
                    )

                chunks.append(
                    CodeChunk(
                        id=self._generate_id(
                            relative_path, f"{java_class.name}.{method.name}", "method"
                        ),
                        content=method_content,
                        language="java",
                        chunk_type="method",
                        file_path=relative_path,
                        start_line=method.start_line,
                        end_line=method.end_line or method.start_line + len(lines),
                        class_name=java_class.name,
                        method_name=method.name,
                        documentation=method.documentation,
                        metadata={
                            "return_type": method.return_type,
                            "parameters": method.parameters,
                            "modifiers": method.modifiers,
                        },
                    )
                )

        return chunks

    def _chunk_generic_file(self, file_path: Path, base_path: Path) -> list[CodeChunk]:
        """Create chunks from a non-Java source file."""
        chunks = []
        blocks = self.generic_extractor.extract_file(file_path)
        relative_path = self._get_relative_path(str(file_path), base_path)

        for block in blocks:
            lines = block.source_code.splitlines()

            if len(lines) < self.min_chunk_lines:
                continue

            content = block.source_code
            if len(lines) > self.max_chunk_lines:
                content = "\n".join(lines[: self.max_chunk_lines]) + "\n# ... truncated"

            chunk_type = block.code_type
            if chunk_type == "module" and not self.include_classes:
                continue

            chunks.append(
                CodeChunk(
                    id=self._generate_id(relative_path, block.name, chunk_type),
                    content=content,
                    language=block.language,
                    chunk_type=chunk_type,
                    file_path=relative_path,
                    start_line=block.start_line,
                    end_line=block.end_line,
                    class_name=block.name if chunk_type == "class" else None,
                    method_name=block.name
                    if chunk_type in ("function", "method")
                    else None,
                    documentation=block.documentation,
                )
            )

        return chunks

    def _build_java_class_content(self, java_class) -> str:
        """Build the full content for a Java class chunk."""
        parts = []

        # Add documentation
        if java_class.documentation and self.include_documentation:
            parts.append(java_class.documentation)

        # Add class signature
        annotations = (
            "\n".join(java_class.annotations) if java_class.annotations else ""
        )
        if annotations:
            parts.append(annotations)

        modifiers = " ".join(java_class.modifiers)
        signature = f"{modifiers} {java_class.class_type} {java_class.name}"

        if java_class.extends:
            signature += f" extends {java_class.extends}"
        if java_class.implements:
            signature += f" implements {', '.join(java_class.implements)}"

        parts.append(signature + " {")

        # Add fields
        for field in java_class.fields:
            field_mods = " ".join(field.get("modifiers", []))
            parts.append(f"    {field_mods} {field['type']} {field['name']};")

        # Add method signatures
        for method in java_class.methods:
            method_sig = self._get_method_signature(method)
            parts.append(f"\n    {method_sig}")

        parts.append("}")

        return "\n".join(parts)

    def _build_java_class_summary(self, java_class) -> str:
        """Build a summary for large Java classes."""
        parts = []

        if java_class.documentation and self.include_documentation:
            parts.append(java_class.documentation)

        modifiers = " ".join(java_class.modifiers)
        signature = f"{modifiers} {java_class.class_type} {java_class.name}"

        if java_class.extends:
            signature += f" extends {java_class.extends}"
        if java_class.implements:
            signature += f" implements {', '.join(java_class.implements)}"

        parts.append(signature + " {")
        parts.append(f"    // {len(java_class.fields)} fields")
        parts.append(f"    // {len(java_class.methods)} methods:")

        for method in java_class.methods:
            method_sig = self._get_method_signature(method)
            parts.append(f"    //   - {method_sig}")

        parts.append("}")

        return "\n".join(parts)

    def _build_method_content(self, method, java_class) -> str:
        """Build the content for a method chunk."""
        parts = []

        # Add context about the class
        parts.append(f"// From class: {java_class.name}")
        if java_class.package:
            parts.append(f"// Package: {java_class.package}")

        # Add documentation
        if method.documentation and self.include_documentation:
            parts.append(method.documentation)

        # Add method body
        parts.append(method.body)

        return "\n".join(parts)

    def _get_method_signature(self, method) -> str:
        """Get a method signature string."""
        modifiers = " ".join(method.modifiers)
        params = ", ".join([f"{ptype} {pname}" for ptype, pname in method.parameters])
        return f"{modifiers} {method.return_type} {method.name}({params})"

    def _get_relative_path(self, file_path: str, base_path: Path) -> str:
        """Get relative path from base."""
        try:
            return str(Path(file_path).relative_to(base_path))
        except ValueError:
            return file_path

    def _generate_id(self, file_path: str, name: str, chunk_type: str) -> str:
        """Generate a deterministic ID for a chunk."""
        content = f"{file_path}:{name}:{chunk_type}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

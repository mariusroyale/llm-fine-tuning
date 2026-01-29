"""Code and document chunking for RAG pipeline."""

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..extractors.generic_extractor import GenericExtractor
from ..extractors.java_extractor import JavaExtractor


@dataclass
class CodeChunk:
    """Represents a chunk of code or document for embedding and retrieval."""

    id: str
    content: str
    language: str  # java, python, json, markdown, text, etc.
    chunk_type: str  # class, method, function, module, template, document, section
    file_path: str
    start_line: int
    end_line: int
    class_name: Optional[str] = None
    method_name: Optional[str] = None
    documentation: Optional[str] = None
    references: list[str] = field(default_factory=list)  # Class names referenced
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
            "references": self.references,
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
            references=data.get("references", []),
            metadata=data.get("metadata", {}),
        )


class CodeChunker:
    """Chunk source code and documents into semantic units for embedding."""

    # File extensions for different content types
    DOCUMENT_EXTENSIONS = {".md", ".txt", ".rst"}
    TEMPLATE_EXTENSIONS = {".json"}

    # Pattern to detect Java class names (PascalCase identifiers)
    CLASS_NAME_PATTERN = re.compile(
        r"\b([A-Z][a-zA-Z0-9]*(?:Service|Controller|Repository|Manager|Handler|Factory|Builder|Processor|Validator|Mapper|Converter|Provider|Client|Config|Exception|Error|Request|Response|Dto|Entity|Model)?)\b"
    )

    def __init__(
        self,
        include_methods: bool = True,
        include_classes: bool = True,
        include_documentation: bool = True,
        include_templates: bool = True,
        include_documents: bool = True,
        max_chunk_lines: int = 200,
        min_chunk_lines: int = 3,
    ):
        """Initialize the chunker.

        Args:
            include_methods: Include individual methods as chunks
            include_classes: Include full classes as chunks
            include_documentation: Include docstrings/Javadoc in chunks
            include_templates: Include JSON templates
            include_documents: Include text/markdown documents
            max_chunk_lines: Maximum lines per chunk
            min_chunk_lines: Minimum lines per chunk (skip tiny chunks)
        """
        self.include_methods = include_methods
        self.include_classes = include_classes
        self.include_documentation = include_documentation
        self.include_templates = include_templates
        self.include_documents = include_documents
        self.max_chunk_lines = max_chunk_lines
        self.min_chunk_lines = min_chunk_lines

        self.java_extractor = JavaExtractor(
            include_private=True,
            include_comments=include_documentation,
        )
        self.generic_extractor = GenericExtractor()

        # Track known class names for cross-referencing
        self._known_classes: set[str] = set()

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
        self._known_classes = set()

        # Phase 1: Process Java files first to collect class names
        java_dir = source_dir / "java"
        if java_dir.exists():
            java_classes = self.java_extractor.extract_directory(java_dir)
            for java_class in java_classes:
                # Track class name for cross-referencing
                self._known_classes.add(java_class.name)
                class_chunks = self._chunk_java_class(java_class, base_path)
                chunks.extend(class_chunks)

        # Also scan for Java files outside java/ directory
        for file_path in source_dir.rglob("*.java"):
            if "java/" in str(file_path):
                continue  # Already processed
            java_classes = self.java_extractor.extract_file(file_path)
            for java_class in java_classes:
                self._known_classes.add(java_class.name)
                class_chunks = self._chunk_java_class(java_class, base_path)
                chunks.extend(class_chunks)

        # Phase 2: Process other language files
        for ext in self.generic_extractor.LANGUAGE_EXTENSIONS:
            for file_path in source_dir.rglob(f"*{ext}"):
                # Skip Java files (already processed)
                if file_path.suffix == ".java":
                    continue
                file_chunks = self._chunk_generic_file(file_path, base_path)
                chunks.extend(file_chunks)

        # Phase 3: Process JSON templates
        if self.include_templates:
            templates_dir = source_dir / "templates"
            if templates_dir.exists():
                for file_path in templates_dir.rglob("*.json"):
                    template_chunks = self._chunk_json_template(file_path, base_path)
                    chunks.extend(template_chunks)

            # Also scan for JSON files in root
            for file_path in source_dir.glob("*.json"):
                template_chunks = self._chunk_json_template(file_path, base_path)
                chunks.extend(template_chunks)

        # Phase 4: Process documents (markdown, text)
        if self.include_documents:
            docs_dir = source_dir / "docs"
            if docs_dir.exists():
                for ext in self.DOCUMENT_EXTENSIONS:
                    for file_path in docs_dir.rglob(f"*{ext}"):
                        doc_chunks = self._chunk_document(file_path, base_path)
                        chunks.extend(doc_chunks)

            # Also scan root for docs
            for ext in self.DOCUMENT_EXTENSIONS:
                for file_path in source_dir.glob(f"*{ext}"):
                    doc_chunks = self._chunk_document(file_path, base_path)
                    chunks.extend(doc_chunks)

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

        # Extract class dependencies from imports and source
        references = self._extract_java_dependencies(java_class)

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
                        references=references,
                        metadata={
                            "package": java_class.package,
                            "class_type": java_class.class_type,
                            "extends": java_class.extends,
                            "implements": java_class.implements,
                            "imports": java_class.imports,
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

    def _chunk_json_template(self, file_path: Path, base_path: Path) -> list[CodeChunk]:
        """Create chunks from a JSON template file.

        Detects class name references for cross-referencing.
        """
        chunks = []
        relative_path = self._get_relative_path(str(file_path), base_path)

        try:
            content = file_path.read_text(encoding="utf-8")
            data = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            return []

        lines = content.splitlines()
        if len(lines) < self.min_chunk_lines:
            return []

        # Detect class references in the JSON
        references = self._detect_class_references(content)

        # Create a chunk for the whole template
        template_name = file_path.stem

        # Build enriched content with context
        enriched_content = f"// Template: {template_name}\n"
        if references:
            enriched_content += f"// References classes: {', '.join(references)}\n"
        enriched_content += f"\n{content}"

        chunks.append(
            CodeChunk(
                id=self._generate_id(relative_path, template_name, "template"),
                content=enriched_content,
                language="json",
                chunk_type="template",
                file_path=relative_path,
                start_line=1,
                end_line=len(lines),
                references=references,
                metadata={
                    "template_name": template_name,
                    "keys": list(data.keys()) if isinstance(data, dict) else [],
                },
            )
        )

        # If template is large, also create chunks for top-level keys
        if isinstance(data, dict) and len(lines) > self.max_chunk_lines:
            for key, value in data.items():
                key_content = json.dumps({key: value}, indent=2)
                key_lines = key_content.splitlines()

                if len(key_lines) < self.min_chunk_lines:
                    continue

                key_refs = self._detect_class_references(key_content)

                chunks.append(
                    CodeChunk(
                        id=self._generate_id(
                            relative_path, f"{template_name}.{key}", "template_section"
                        ),
                        content=f"// Template: {template_name}, Section: {key}\n\n{key_content}",
                        language="json",
                        chunk_type="template_section",
                        file_path=relative_path,
                        start_line=1,
                        end_line=len(key_lines),
                        references=key_refs,
                        metadata={
                            "template_name": template_name,
                            "section": key,
                        },
                    )
                )

        return chunks

    def _chunk_document(self, file_path: Path, base_path: Path) -> list[CodeChunk]:
        """Create chunks from a text or markdown document.

        Splits by sections (headers) for markdown, or paragraphs for plain text.
        """
        chunks = []
        relative_path = self._get_relative_path(str(file_path), base_path)

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return []

        lines = content.splitlines()
        if len(lines) < self.min_chunk_lines:
            return []

        # Detect class references
        references = self._detect_class_references(content)

        # Determine language based on extension
        ext = file_path.suffix.lower()
        language = "markdown" if ext == ".md" else "text"

        # For markdown, split by headers
        if language == "markdown":
            sections = self._split_markdown_sections(content)
        else:
            # For plain text, treat whole file as one chunk
            sections = [(file_path.stem, content)]

        for section_name, section_content in sections:
            section_lines = section_content.splitlines()

            if len(section_lines) < self.min_chunk_lines:
                continue

            # Truncate if too large
            if len(section_lines) > self.max_chunk_lines:
                section_content = (
                    "\n".join(section_lines[: self.max_chunk_lines])
                    + "\n\n... (truncated)"
                )

            section_refs = self._detect_class_references(section_content)

            chunks.append(
                CodeChunk(
                    id=self._generate_id(relative_path, section_name, "document"),
                    content=section_content,
                    language=language,
                    chunk_type="document",
                    file_path=relative_path,
                    start_line=1,
                    end_line=len(section_lines),
                    references=section_refs,
                    metadata={
                        "document_name": file_path.stem,
                        "section": section_name,
                    },
                )
            )

        return chunks

    def _split_markdown_sections(self, content: str) -> list[tuple[str, str]]:
        """Split markdown content by headers into sections."""
        sections = []
        current_section = ""
        current_content = []

        for line in content.splitlines():
            # Check for header
            if line.startswith("#"):
                # Save previous section
                if current_content:
                    sections.append(
                        (current_section or "intro", "\n".join(current_content))
                    )

                # Start new section
                current_section = line.lstrip("#").strip()
                current_content = [line]
            else:
                current_content.append(line)

        # Don't forget the last section
        if current_content:
            sections.append((current_section or "content", "\n".join(current_content)))

        return sections

    def _detect_class_references(self, content: str) -> list[str]:
        """Detect Java class name references in content.

        Uses both pattern matching and known class names.
        """
        references = set()

        # Find all PascalCase identifiers that look like class names
        matches = self.CLASS_NAME_PATTERN.findall(content)
        for match in matches:
            # If we have known classes, only include those
            if self._known_classes:
                if match in self._known_classes:
                    references.add(match)
            else:
                # Otherwise include all matches
                references.add(match)

        return sorted(references)

    def _extract_java_dependencies(self, java_class) -> list[str]:
        """Extract class dependencies from a Java class.

        Sources of dependencies:
        1. Import statements (class names from same project)
        2. extends clause
        3. implements clause
        4. Field types
        5. Method parameter/return types
        """
        dependencies = set()

        # Common Java/library classes to exclude
        exclude_prefixes = {
            "java.",
            "javax.",
            "org.springframework.",
            "com.google.",
            "org.apache.",
            "org.slf4j.",
            "lombok.",
            "org.junit.",
        }

        # From imports - extract class names from project imports
        for imp in java_class.imports:
            # Skip common library imports
            if any(imp.startswith(prefix) for prefix in exclude_prefixes):
                continue
            # Extract class name (last part of import)
            class_name = imp.split(".")[-1]
            if class_name != "*":  # Skip wildcard imports
                dependencies.add(class_name)

        # From extends
        if java_class.extends:
            dependencies.add(java_class.extends)

        # From implements
        for interface in java_class.implements:
            dependencies.add(interface)

        # From field types
        for field in java_class.fields:
            field_type = self._extract_type_name(field.get("type", ""))
            if field_type and field_type[0].isupper():
                dependencies.add(field_type)

        # From method signatures
        for method in java_class.methods:
            # Return type
            return_type = self._extract_type_name(method.return_type)
            if return_type and return_type[0].isupper():
                dependencies.add(return_type)

            # Parameter types
            for param_type, _ in method.parameters:
                ptype = self._extract_type_name(param_type)
                if ptype and ptype[0].isupper():
                    dependencies.add(ptype)

        # Remove self-reference and common Java types
        common_types = {
            "String",
            "Integer",
            "Long",
            "Double",
            "Float",
            "Boolean",
            "Byte",
            "Short",
            "Character",
            "Object",
            "Class",
            "Void",
            "List",
            "ArrayList",
            "LinkedList",
            "Set",
            "HashSet",
            "TreeSet",
            "Map",
            "HashMap",
            "TreeMap",
            "LinkedHashMap",
            "Collection",
            "Optional",
            "Stream",
            "Collectors",
            "Arrays",
            "Collections",
            "Exception",
            "RuntimeException",
            "Throwable",
            "Error",
            java_class.name,  # Remove self
        }
        dependencies -= common_types

        # If we have known classes, filter to only include those
        if self._known_classes:
            dependencies &= self._known_classes

        return sorted(dependencies)

    def _extract_type_name(self, type_str: str) -> str:
        """Extract the base type name from a type string.

        Handles generics like List<String> -> List, Map<K,V> -> Map
        """
        if not type_str:
            return ""
        # Remove generics
        base = type_str.split("<")[0].strip()
        # Remove array notation
        base = base.replace("[]", "").strip()
        return base

    def get_known_classes(self) -> set[str]:
        """Return the set of known Java class names."""
        return self._known_classes.copy()

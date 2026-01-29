"""Java source code extractor using javalang parser."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import javalang


@dataclass
class JavaMethod:
    """Represents a Java method."""

    name: str
    return_type: str
    parameters: list[tuple[str, str]]  # [(type, name), ...]
    modifiers: list[str]
    body: str
    documentation: Optional[str] = None
    annotations: list[str] = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0


@dataclass
class JavaClass:
    """Represents a Java class or interface."""

    name: str
    package: str
    class_type: str  # class, interface, enum, record
    modifiers: list[str]
    extends: Optional[str]
    implements: list[str]
    fields: list[dict]
    methods: list[JavaMethod]
    inner_classes: list["JavaClass"]
    documentation: Optional[str]
    imports: list[str]
    source_code: str
    file_path: str
    annotations: list[str] = field(default_factory=list)


class JavaExtractor:
    """Extract structured information from Java source files."""

    def __init__(
        self,
        include_private: bool = True,
        include_comments: bool = True,
        include_imports: bool = True,
        max_lines: int = 500,
    ):
        self.include_private = include_private
        self.include_comments = include_comments
        self.include_imports = include_imports
        self.max_lines = max_lines

    def extract_file(self, file_path: Path) -> list[JavaClass]:
        """Extract all classes from a Java file."""
        source = file_path.read_text(encoding="utf-8")
        lines = source.splitlines()

        if len(lines) > self.max_lines:
            return []  # Skip very large files

        try:
            tree = javalang.parse.parse(source)
        except javalang.parser.JavaSyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
            return []

        classes = []
        package = tree.package.name if tree.package else ""
        imports = [imp.path for imp in tree.imports] if self.include_imports else []

        for type_decl in tree.types:
            java_class = self._extract_type(
                type_decl, package, imports, source, str(file_path)
            )
            if java_class:
                classes.append(java_class)

        return classes

    def _extract_type(
        self,
        type_decl,
        package: str,
        imports: list[str],
        source: str,
        file_path: str,
    ) -> Optional[JavaClass]:
        """Extract a single type declaration (class, interface, enum)."""
        if isinstance(type_decl, javalang.tree.ClassDeclaration):
            class_type = "class"
        elif isinstance(type_decl, javalang.tree.InterfaceDeclaration):
            class_type = "interface"
        elif isinstance(type_decl, javalang.tree.EnumDeclaration):
            class_type = "enum"
        else:
            return None

        # Extract modifiers
        modifiers = list(type_decl.modifiers) if type_decl.modifiers else []

        # Skip private classes if configured
        if not self.include_private and "private" in modifiers:
            return None

        # Extract extends/implements
        extends = None
        implements = []

        if hasattr(type_decl, "extends") and type_decl.extends:
            if isinstance(type_decl.extends, list):
                extends = type_decl.extends[0].name if type_decl.extends else None
            else:
                extends = type_decl.extends.name

        if hasattr(type_decl, "implements") and type_decl.implements:
            implements = [impl.name for impl in type_decl.implements]

        # Extract fields
        fields = self._extract_fields(type_decl)

        # Extract methods
        methods = self._extract_methods(type_decl, source)

        # Extract documentation
        documentation = self._extract_javadoc(type_decl, source)

        # Extract annotations
        annotations = []
        if type_decl.annotations:
            annotations = [f"@{ann.name}" for ann in type_decl.annotations]

        # Extract inner classes
        inner_classes = []
        if hasattr(type_decl, "body") and type_decl.body:
            for member in type_decl.body:
                if isinstance(
                    member,
                    (
                        javalang.tree.ClassDeclaration,
                        javalang.tree.InterfaceDeclaration,
                    ),
                ):
                    inner = self._extract_type(member, package, [], source, file_path)
                    if inner:
                        inner_classes.append(inner)

        return JavaClass(
            name=type_decl.name,
            package=package,
            class_type=class_type,
            modifiers=modifiers,
            extends=extends,
            implements=implements,
            fields=fields,
            methods=methods,
            inner_classes=inner_classes,
            documentation=documentation,
            imports=imports,
            source_code=source,
            file_path=file_path,
            annotations=annotations,
        )

    def _extract_fields(self, type_decl) -> list[dict]:
        """Extract field declarations."""
        fields = []
        if not hasattr(type_decl, "fields") or not type_decl.fields:
            return fields

        for field_decl in type_decl.fields:
            modifiers = list(field_decl.modifiers) if field_decl.modifiers else []

            if not self.include_private and "private" in modifiers:
                continue

            for declarator in field_decl.declarators:
                fields.append(
                    {
                        "name": declarator.name,
                        "type": field_decl.type.name
                        if hasattr(field_decl.type, "name")
                        else str(field_decl.type),
                        "modifiers": modifiers,
                    }
                )

        return fields

    def _extract_methods(self, type_decl, source: str) -> list[JavaMethod]:
        """Extract method declarations."""
        methods = []

        method_declarations = []
        if hasattr(type_decl, "methods") and type_decl.methods:
            method_declarations.extend(type_decl.methods)
        if hasattr(type_decl, "constructors") and type_decl.constructors:
            method_declarations.extend(type_decl.constructors)

        for method in method_declarations:
            modifiers = list(method.modifiers) if method.modifiers else []

            if not self.include_private and "private" in modifiers:
                continue

            # Get parameters
            parameters = []
            if method.parameters:
                for param in method.parameters:
                    param_type = (
                        param.type.name
                        if hasattr(param.type, "name")
                        else str(param.type)
                    )
                    parameters.append((param_type, param.name))

            # Get return type
            return_type = "void"
            if hasattr(method, "return_type") and method.return_type:
                return_type = (
                    method.return_type.name
                    if hasattr(method.return_type, "name")
                    else str(method.return_type)
                )

            # Get documentation
            documentation = self._extract_javadoc(method, source)

            # Get annotations
            annotations = []
            if method.annotations:
                annotations = [f"@{ann.name}" for ann in method.annotations]

            # Extract method body (approximate via source lines)
            body = self._extract_method_body(method, source)

            methods.append(
                JavaMethod(
                    name=method.name,
                    return_type=return_type,
                    parameters=parameters,
                    modifiers=modifiers,
                    body=body,
                    documentation=documentation,
                    annotations=annotations,
                    start_line=method.position.line if method.position else 0,
                )
            )

        return methods

    def _extract_javadoc(self, node, source: str) -> Optional[str]:
        """Extract Javadoc comment for a node."""
        if not self.include_comments:
            return None

        if not hasattr(node, "position") or not node.position:
            return None

        lines = source.splitlines()
        line_num = node.position.line - 1

        # Look backwards for Javadoc
        javadoc_lines = []
        i = line_num - 1

        while i >= 0:
            line = lines[i].strip()
            if line.endswith("*/"):
                javadoc_lines.insert(0, line)
                i -= 1
                while i >= 0:
                    line = lines[i].strip()
                    javadoc_lines.insert(0, line)
                    if line.startswith("/**"):
                        return "\n".join(javadoc_lines)
                    i -= 1
            elif line.startswith("@") or not line or line.startswith("//"):
                i -= 1
            else:
                break

        return None

    def _extract_method_body(self, method, source: str) -> str:
        """Extract the full method body from source."""
        if not hasattr(method, "position") or not method.position:
            return ""

        lines = source.splitlines()
        start_line = method.position.line - 1

        # Find method start and count braces to find end
        brace_count = 0
        in_method = False
        method_lines = []

        for i in range(start_line, len(lines)):
            line = lines[i]
            method_lines.append(line)

            for char in line:
                if char == "{":
                    brace_count += 1
                    in_method = True
                elif char == "}":
                    brace_count -= 1

            if in_method and brace_count == 0:
                break

        return "\n".join(method_lines)

    def extract_directory(
        self, dir_path: Path, recursive: bool = True
    ) -> list[JavaClass]:
        """Extract all Java classes from a directory."""
        classes = []
        pattern = "**/*.java" if recursive else "*.java"

        for java_file in dir_path.glob(pattern):
            file_classes = self.extract_file(java_file)
            classes.extend(file_classes)

        return classes


def get_class_signature(java_class: JavaClass) -> str:
    """Generate a class signature summary."""
    parts = []

    if java_class.annotations:
        parts.extend(java_class.annotations)

    modifiers = " ".join(java_class.modifiers)
    signature = f"{modifiers} {java_class.class_type} {java_class.name}"

    if java_class.extends:
        signature += f" extends {java_class.extends}"

    if java_class.implements:
        signature += f" implements {', '.join(java_class.implements)}"

    parts.append(signature)

    return "\n".join(parts)


def get_method_signature(method: JavaMethod) -> str:
    """Generate a method signature."""
    parts = []

    if method.annotations:
        parts.extend(method.annotations)

    modifiers = " ".join(method.modifiers)
    params = ", ".join([f"{ptype} {pname}" for ptype, pname in method.parameters])
    signature = f"{modifiers} {method.return_type} {method.name}({params})"

    parts.append(signature)

    return "\n".join(parts)

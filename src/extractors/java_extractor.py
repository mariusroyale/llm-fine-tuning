"""Java source code extractor using javalang parser."""

import re
import sys
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
            # Print detailed error information
            error_msg = str(e)
            error_at = getattr(e, 'at', None)
            error_line = getattr(e, 'line', None)
            error_column = getattr(e, 'column', None)
            
            print(f"\n❌ Syntax error in {file_path}:")
            print(f"   Error message: {error_msg}")
            if error_at:
                print(f"   Error at: {error_at}")
            if error_line:
                print(f"   Line number: {error_line}")
                if 0 < error_line <= len(lines):
                    error_line_idx = error_line - 1
                    print(f"   Line content: {lines[error_line_idx][:150]}")
                    # Show context around the error
                    if error_line_idx > 0:
                        print(f"   Previous line: {lines[error_line_idx - 1][:150]}")
                    if error_line_idx < len(lines) - 1:
                        print(f"   Next line: {lines[error_line_idx + 1][:150]}")
            if error_column:
                print(f"   Column: {error_column}")
            print(f"   File has {len(lines)} lines")
            print(f"   Attempting fallback extraction...\n")
            
            # Try to extract basic class info even if parsing fails
            return self._extract_fallback(file_path, source, lines)
        except Exception as e:
            import traceback
            print(f"Unexpected error parsing {file_path}: {type(e).__name__}: {e}")
            print(f"  Traceback: {traceback.format_exc()}")
            return self._extract_fallback(file_path, source, lines)

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

    def _extract_fallback(
        self, file_path: Path, source: str, lines: list[str]
    ) -> list[JavaClass]:
        """Fallback extraction using regex when javalang parser fails.
        
        This extracts basic class information using pattern matching.
        """
        classes = []
        
        # Extract package
        package = ""
        for line in lines[:20]:  # Check first 20 lines for package
            if line.strip().startswith("package "):
                package = line.strip().replace("package ", "").replace(";", "").strip()
                break
        
        # Extract imports
        imports = []
        for line in lines[:100]:  # Check first 100 lines for imports
            stripped = line.strip()
            if stripped.startswith("import "):
                imp = stripped.replace("import ", "").replace(";", "").strip()
                if imp:
                    imports.append(imp)
        
        # Find class declarations using regex
        # Prioritize public top-level classes (not inner classes with tabs/indentation)
        # Pattern 1: public class at start of line (top-level)
        top_level_pattern = re.compile(
            r"^public\s+(?:abstract\s+)?(?:final\s+)?(?:class|interface|enum)\s+(\w+)"
        )
        # Pattern 2: fallback for any class (including inner classes)
        any_class_pattern = re.compile(
            r"(?:public\s+)?(?:abstract\s+)?(?:final\s+)?(?:class|interface|enum)\s+(\w+)"
        )
        
        class_name = None
        class_line_idx = None
        
        # First, try to find public top-level class (most common case)
        for i, line in enumerate(lines):
            # Skip package and imports (first ~60 lines typically)
            if i < 60 and (line.strip().startswith("package ") or line.strip().startswith("import ")):
                continue
            
            stripped = line.strip()
            # Check for top-level public class (no leading whitespace/tabs)
            if not line.startswith(("\t", " ")) and top_level_pattern.match(stripped):
                match = top_level_pattern.match(stripped)
                class_name = match.group(1)
                class_line_idx = i
                break
        
        # Fallback: if no top-level class found, use any class
        if class_name is None:
            for i, line in enumerate(lines):
                if i < 60 and (line.strip().startswith("package ") or line.strip().startswith("import ")):
                    continue
                match = any_class_pattern.search(line)
                if match:
                    class_name = match.group(1)
                    class_line_idx = i
                    break
        
        if class_name and class_line_idx is not None:
            i = class_line_idx
            line = lines[i]
                
            # Try to find class documentation (Javadoc before class)
            documentation = None
            if self.include_comments:
                doc_lines = []
                j = i - 1
                while j >= 0 and j >= i - 10:  # Look back up to 10 lines
                    prev_line = lines[j].strip()
                    if prev_line.endswith("*/"):
                        doc_lines.insert(0, prev_line)
                        j -= 1
                        while j >= 0:
                            doc_line = lines[j].strip()
                            doc_lines.insert(0, doc_line)
                            if doc_line.startswith("/**"):
                                documentation = "\n".join(doc_lines)
                                break
                            j -= 1
                        break
                    elif prev_line.startswith("@") or not prev_line or prev_line.startswith("//"):
                        j -= 1
                    else:
                        break
            
            # Determine class type
            if "enum" in line:
                class_type = "enum"
            elif "interface" in line:
                class_type = "interface"
            else:
                class_type = "class"
            
            # Extract extends/implements
            extends = None
            implements = []
            if "extends" in line:
                parts = line.split("extends")
                if len(parts) > 1:
                    extends_part = parts[1].split()[0].replace("{", "").strip()
                    if extends_part:
                        extends = extends_part
            if "implements" in line:
                parts = line.split("implements")
                if len(parts) > 1:
                    impl_part = parts[1].split(",")[0].replace("{", "").strip()
                    if impl_part:
                        implements = [impl_part]
            
            # Extract inner classes/enums using regex
            inner_classes = self._extract_inner_types_fallback(source, lines, class_name, package)
            
            # Create a basic JavaClass with the source code
            java_class = JavaClass(
                name=class_name,
                package=package,
                class_type=class_type,
                modifiers=[],
                extends=extends,
                implements=implements,
                fields=[],
                methods=[],
                inner_classes=inner_classes,
                documentation=documentation,
                imports=imports if self.include_imports else [],
                source_code=source,
                file_path=str(file_path),
            )
            classes.append(java_class)
            # Only extract the first top-level class for fallback (already handled by finding first match)
        else:
            print(f"  [WARNING] Fallback extraction could not find main class in {file_path}", file=sys.stderr)
        
        if classes:
            print(f"  Fallback extraction found {len(classes)} class(es) in {file_path}")
            if classes[0].inner_classes:
                print(f"    With {len(classes[0].inner_classes)} inner type(s): {[t.name for t in classes[0].inner_classes]}")
        
        return classes

    def _extract_inner_types_fallback(
        self, source: str, lines: list[str], parent_class_name: str, package: str
    ) -> list[JavaClass]:
        """Extract inner enums and classes using regex when parser fails.
        
        Uses a simpler approach: find indented enum/class declarations
        between the class start and end.
        """
        inner_types = []
        
        # Pattern to match inner enum/class/interface declarations
        # Matches: \tpublic enum Type {, \tprivate static class Inner {, etc.
        # Must start with tab/space (indented) to be an inner type
        inner_pattern = re.compile(
            r"^\s+(?:public|private|protected)?\s*(?:static)?\s*(?:final)?\s*(enum|class|interface)\s+(\w+)"
        )
        
        # Find where the parent class starts and ends
        class_start = None
        class_end = None
        
        for i, line in enumerate(lines):
            # Find class declaration
            if class_start is None:
                if parent_class_name in line and ("class" in line or "interface" in line):
                    class_start = i
                    # Find opening brace
                    for j in range(i, min(i + 5, len(lines))):
                        if "{" in lines[j]:
                            class_start = j
                            break
            else:
                # Track braces to find class end
                if class_end is None:
                    open_braces = line.count("{")
                    close_braces = line.count("}")
                    if open_braces > 0 or close_braces > 0:
                        # Simple heuristic: if we see many closing braces, we might be at the end
                        # But this is approximate - we'll search until we find matching patterns
                        pass
        
        if class_start is None:
            print(f"    [DEBUG] Could not find parent class '{parent_class_name}'", file=sys.stderr)
            return inner_types
        
        # Simple approach: search for indented enum/class declarations
        # Inner types are typically indented with tabs or multiple spaces
        for i in range(class_start + 1, min(class_start + 2500, len(lines))):
            line = lines[i]
            
            # Skip if line doesn't start with whitespace (not indented = not inner type)
            if not line or not (line.startswith("\t") or line.startswith(" ")):
                # If we hit a non-indented line that looks like it might be end of class,
                # we could stop, but let's be conservative and search more
                continue
            
            stripped = line.strip()
            if not stripped or stripped.startswith("//"):
                continue
            
            # Check if this matches an inner type declaration
            match = inner_pattern.match(line)  # Use match() not search() to require start of line
            if match:
                inner_type_kind = match.group(1)  # enum, class, or interface
                inner_type_name = match.group(2)
                
                print(f"    [DEBUG] Found inner {inner_type_kind} '{inner_type_name}' at line {i+1}", file=sys.stderr)
                
                # Skip if this looks like a method (has parentheses before the name)
                if "(" in stripped and "(" in stripped[:stripped.find(inner_type_name)]:
                    continue
                
                # Try to find documentation before this inner type
                documentation = None
                if self.include_comments:
                    doc_lines = []
                    j = i - 1
                    while j >= 0 and j >= i - 10:
                        prev_line = lines[j].strip()
                        if prev_line.endswith("*/"):
                            doc_lines.insert(0, prev_line)
                            j -= 1
                            while j >= 0:
                                doc_line = lines[j].strip()
                                doc_lines.insert(0, doc_line)
                                if doc_line.startswith("/**"):
                                    documentation = "\n".join(doc_lines)
                                    break
                                j -= 1
                            break
                        elif prev_line.startswith("@") or not prev_line or prev_line.startswith("//"):
                            j -= 1
                        else:
                            break
                
                # Determine class type
                if inner_type_kind == "enum":
                    class_type = "enum"
                elif inner_type_kind == "interface":
                    class_type = "interface"
                else:
                    class_type = "class"
                
                # Extract the inner type's source code
                # Find the opening brace and extract until matching closing brace
                inner_start = i
                inner_end = i
                inner_brace_depth = 0
                found_opening = False
                
                for j in range(i, min(i + 1000, len(lines))):  # Limit search to 1000 lines
                    line_content = lines[j]
                    inner_brace_depth += line_content.count("{") - line_content.count("}")
                    if "{" in line_content:
                        found_opening = True
                    if found_opening and inner_brace_depth == 0:
                        inner_end = j
                        break
                
                inner_source = "\n".join(lines[inner_start:inner_end + 1])
                
                # Create JavaClass for inner type
                inner_class = JavaClass(
                    name=inner_type_name,
                    package=package,
                    class_type=class_type,
                    modifiers=[],
                    extends=None,
                    implements=[],
                    fields=[],
                    methods=[],
                    inner_classes=[],
                    documentation=documentation,
                    imports=[],
                    source_code=inner_source,
                    file_path="",  # Will be set by parent
                )
                inner_types.append(inner_class)
        
        if inner_types:
            print(f"    Found {len(inner_types)} inner type(s): {[t.name for t in inner_types]}", file=sys.stderr)
        else:
            searched_lines = min(class_start + 2500, len(lines)) - class_start if class_start else 0
            print(f"    [DEBUG] No inner types found for {parent_class_name} (searched {searched_lines} lines)", file=sys.stderr)
        
        return inner_types

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

        # Extract inner classes and enums
        inner_classes = []
        if hasattr(type_decl, "body") and type_decl.body:
            for member in type_decl.body:
                if isinstance(
                    member,
                    (
                        javalang.tree.ClassDeclaration,
                        javalang.tree.InterfaceDeclaration,
                        javalang.tree.EnumDeclaration,
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

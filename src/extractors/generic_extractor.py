"""Generic source code extractor for multiple languages."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class CodeBlock:
    """Represents a block of code (function, class, module)."""

    name: str
    language: str
    code_type: str  # function, class, module, method
    source_code: str
    file_path: str
    documentation: Optional[str] = None
    start_line: int = 0
    end_line: int = 0


class GenericExtractor:
    """Extract code blocks from various programming languages."""

    LANGUAGE_EXTENSIONS = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript",
        ".go": "go",
        ".rs": "rust",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c",
        ".hpp": "cpp",
        ".cs": "csharp",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
    }

    # Patterns for detecting code blocks by language
    PATTERNS = {
        "python": {
            "class": r"^class\s+(\w+).*?:",
            "function": r"^def\s+(\w+)\s*\(",
            "docstring": r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'',
        },
        "javascript": {
            "class": r"^(?:export\s+)?class\s+(\w+)",
            "function": r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)",
            "arrow": r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(",
        },
        "typescript": {
            "class": r"^(?:export\s+)?class\s+(\w+)",
            "function": r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)",
            "interface": r"^(?:export\s+)?interface\s+(\w+)",
            "type": r"^(?:export\s+)?type\s+(\w+)",
        },
        "go": {
            "function": r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(",
            "struct": r"^type\s+(\w+)\s+struct\s*{",
            "interface": r"^type\s+(\w+)\s+interface\s*{",
        },
    }

    def __init__(self, max_lines: int = 500):
        self.max_lines = max_lines

    def detect_language(self, file_path: Path) -> Optional[str]:
        """Detect programming language from file extension."""
        return self.LANGUAGE_EXTENSIONS.get(file_path.suffix.lower())

    def extract_file(self, file_path: Path) -> list[CodeBlock]:
        """Extract code blocks from a source file."""
        language = self.detect_language(file_path)
        if not language:
            return []

        try:
            source = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return []

        lines = source.splitlines()
        if len(lines) > self.max_lines:
            return []

        # For now, return the whole file as a single block
        # More sophisticated parsing can be added per language
        blocks = [
            CodeBlock(
                name=file_path.stem,
                language=language,
                code_type="module",
                source_code=source,
                file_path=str(file_path),
                documentation=self._extract_module_doc(source, language),
                start_line=1,
                end_line=len(lines),
            )
        ]

        # Extract individual functions/classes if patterns exist
        if language in self.PATTERNS:
            blocks.extend(self._extract_blocks(source, language, str(file_path)))

        return blocks

    def _extract_module_doc(self, source: str, language: str) -> Optional[str]:
        """Extract module-level documentation."""
        if language == "python":
            # Look for module docstring
            match = re.match(r'^[\s]*"""([\s\S]*?)"""', source)
            if match:
                return match.group(1).strip()
            match = re.match(r"^[\s]*'''([\s\S]*?)'''", source)
            if match:
                return match.group(1).strip()

        elif language in ("javascript", "typescript"):
            # Look for JSDoc at top
            match = re.match(r"^[\s]*/\*\*([\s\S]*?)\*/", source)
            if match:
                return match.group(1).strip()

        return None

    def _extract_blocks(
        self, source: str, language: str, file_path: str
    ) -> list[CodeBlock]:
        """Extract individual code blocks using regex patterns."""
        blocks = []
        lines = source.splitlines()
        patterns = self.PATTERNS.get(language, {})

        for code_type, pattern in patterns.items():
            for i, line in enumerate(lines):
                match = re.match(pattern, line)
                if match:
                    name = match.group(1)
                    # Extract the block (simplified - just get next N lines)
                    block_lines = self._get_block_lines(lines, i, language)
                    block_source = "\n".join(block_lines)

                    blocks.append(
                        CodeBlock(
                            name=name,
                            language=language,
                            code_type=code_type,
                            source_code=block_source,
                            file_path=file_path,
                            start_line=i + 1,
                            end_line=i + len(block_lines),
                        )
                    )

        return blocks

    def _get_block_lines(
        self, lines: list[str], start: int, language: str
    ) -> list[str]:
        """Get all lines belonging to a code block."""
        if language == "python":
            return self._get_python_block(lines, start)
        else:
            return self._get_brace_block(lines, start)

    def _get_python_block(self, lines: list[str], start: int) -> list[str]:
        """Extract a Python block based on indentation."""
        if start >= len(lines):
            return []

        block_lines = [lines[start]]
        base_indent = len(lines[start]) - len(lines[start].lstrip())

        for i in range(start + 1, len(lines)):
            line = lines[i]
            if not line.strip():  # Empty line
                block_lines.append(line)
                continue

            indent = len(line) - len(line.lstrip())
            if indent <= base_indent and line.strip():
                # Found a line at same or lower indentation
                break
            block_lines.append(line)

        return block_lines

    def _get_brace_block(self, lines: list[str], start: int) -> list[str]:
        """Extract a brace-delimited block."""
        block_lines = []
        brace_count = 0
        in_block = False

        for i in range(start, len(lines)):
            line = lines[i]
            block_lines.append(line)

            # Count braces (simplified - doesn't handle strings/comments)
            for char in line:
                if char == "{":
                    brace_count += 1
                    in_block = True
                elif char == "}":
                    brace_count -= 1

            if in_block and brace_count == 0:
                break

        return block_lines

    def extract_directory(
        self, dir_path: Path, recursive: bool = True
    ) -> list[CodeBlock]:
        """Extract code blocks from all supported files in a directory."""
        blocks = []

        for ext in self.LANGUAGE_EXTENSIONS:
            pattern = f"**/*{ext}" if recursive else f"*{ext}"
            for file_path in dir_path.glob(pattern):
                file_blocks = self.extract_file(file_path)
                blocks.extend(file_blocks)

        return blocks

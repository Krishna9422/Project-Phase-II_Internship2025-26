"""Java support helpers for parsing, comment generation, and file updates."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

try:
    from langchain_core.messages import HumanMessage
    from langchain_groq import ChatGroq
except Exception:  # pragma: no cover - optional dependency
    ChatGroq = None
    HumanMessage = None


load_dotenv()


_IGNORED_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", "build", "dist", "out", "target"}


def _read_file_with_encoding(file_path: str) -> str:
    """Read file content with a small encoding fallback chain."""
    encodings = ["utf-8", "utf-16", "utf-8-sig", "latin-1", "cp1252"]
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as handle:
                return handle.read()
        except (UnicodeDecodeError, UnicodeError):
            continue

    with open(file_path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read()


def list_java_files(root_dir: str) -> List[str]:
    """Return Java source files from a workspace root."""
    java_files: List[str] = []
    for dir_path, dir_names, file_names in os.walk(root_dir):
        dir_names[:] = [d for d in dir_names if d not in _IGNORED_DIRS and not d.startswith(".")]
        for file_name in file_names:
            if file_name.endswith(".java"):
                java_files.append(os.path.abspath(os.path.join(dir_path, file_name)))
    return sorted(java_files, key=lambda path: path.lower())


def _split_parameters(parameter_block: str) -> List[str]:
    """Split a Java parameter list while preserving generic/comma-bearing types."""
    if not parameter_block.strip():
        return []

    parameters: List[str] = []
    depth = 0
    token = []
    for character in parameter_block:
        if character == "," and depth == 0:
            item = "".join(token).strip()
            if item:
                parameters.append(item)
            token = []
            continue
        if character in "<[(":
            depth += 1
        elif character in ">])" and depth > 0:
            depth -= 1
        token.append(character)

    item = "".join(token).strip()
    if item:
        parameters.append(item)
    return parameters


def _parameter_name(parameter: str) -> str:
    """Return the Java parameter name from a declaration string."""
    cleaned = parameter.strip().split("=")[0].strip()
    parts = cleaned.split()
    if not parts:
        return "param"
    return parts[-1].replace("...", "")


def _indent_for_line(line: str) -> str:
    return line[: len(line) - len(line.lstrip())]


@dataclass
class JavaEntity:
    kind: str
    name: str
    line: int
    end_line: int
    indent: str
    signature: str
    return_type: str = "void"
    parameters: List[str] = None
    class_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "name": self.name,
            "line": self.line,
            "end_line": self.end_line,
            "indent": self.indent,
            "signature": self.signature,
            "return_type": self.return_type,
            "parameters": self.parameters or [],
            "class_name": self.class_name,
        }


_CLASS_PATTERN = re.compile(
    r"^(?P<indent>\s*)(?:public|protected|private)?\s*(?:abstract\s+|final\s+)?(?:(?:class|interface|enum|record)\s+)(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
)
_METHOD_PATTERN = re.compile(
    r"^(?P<indent>\s*)(?:@\w+(?:\([^)]*\))?\s*)*(?:(?:public|protected|private)\s+)?(?:(?:static|final|synchronized|native|abstract|default|strictfp)\s+)*"
    r"(?P<return>[A-Za-z_][\w<>,\[\].?\s]*)\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\((?P<params>[^)]*)\)"
    r"\s*(?:throws\s+[^{]+)?\s*(?:\{|;)?\s*$"
)
_CONSTRUCTOR_PATTERN = re.compile(
    r"^(?P<indent>\s*)(?:public|protected|private)?\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\((?P<params>[^)]*)\)"
    r"\s*(?:throws\s+[^{]+)?\s*(?:\{|;)?\s*$"
)


def _find_block_end(lines: List[str], start_index: int) -> int:
    """Find the end of a Java block by brace balancing."""
    brace_depth = 0
    started = False
    for index in range(start_index, len(lines)):
        line = lines[index]
        for character in line:
            if character == "{":
                brace_depth += 1
                started = True
            elif character == "}":
                brace_depth -= 1
                if started and brace_depth <= 0:
                    return index + 1
    return start_index + 1


def _find_brace_block_end(text: str, open_brace_index: int) -> int:
    """Return the index just after the matching closing brace in a text block."""
    brace_depth = 0
    started = False
    for index in range(open_brace_index, len(text)):
        character = text[index]
        if character == "{":
            brace_depth += 1
            started = True
        elif character == "}":
            brace_depth -= 1
            if started and brace_depth <= 0:
                return index + 1
    return len(text)


def extract_java_entities(source: str) -> Dict[str, Any]:
    """Extract a best-effort list of Java classes and methods."""
    lines = source.splitlines()
    entities: Dict[str, Any] = {
        "module": {"name": "Java Module", "line": 1, "docstring": None},
        "classes": [],
        "methods": [],
        "syntax_error": False,
    }

    class_stack: List[Dict[str, Any]] = []
    brace_depth = 0

    for line_number, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
            brace_depth += raw_line.count("{") - raw_line.count("}")
            continue

        while class_stack and brace_depth < class_stack[-1]["brace_depth"]:
            class_stack.pop()

        class_match = _CLASS_PATTERN.match(raw_line)
        if class_match:
            class_name = class_match.group("name")
            indent = _indent_for_line(raw_line)
            class_entity = {
                "kind": "class",
                "name": class_name,
                "line": line_number,
                "end_line": _find_block_end(lines, line_number - 1),
                "indent": indent,
                "signature": stripped,
                "methods": [],
                "brace_depth": brace_depth,
            }
            entities["classes"].append(class_entity)
            class_stack.append(class_entity)

        method_match = _METHOD_PATTERN.match(raw_line)
        constructor_match = None
        if not method_match and class_stack:
            constructor_match = _CONSTRUCTOR_PATTERN.match(raw_line)
            if constructor_match and constructor_match.group("name") != class_stack[-1]["name"]:
                constructor_match = None

        if method_match or constructor_match:
            match = method_match or constructor_match
            method_name = match.group("name")
            return_type = method_match.group("return").strip() if method_match else class_stack[-1]["name"]
            parameters = _split_parameters(match.group("params"))
            indent = _indent_for_line(raw_line)
            method_entity = {
                "kind": "constructor" if constructor_match else "method",
                "name": method_name,
                "line": line_number,
                "end_line": _find_block_end(lines, line_number - 1),
                "indent": indent,
                "signature": stripped,
                "return_type": return_type,
                "parameters": parameters,
                "class_name": class_stack[-1]["name"] if class_stack else None,
            }
            if class_stack:
                class_stack[-1]["methods"].append(method_entity)
            else:
                entities["methods"].append(method_entity)

        brace_depth += raw_line.count("{") - raw_line.count("}")

    return entities


def generate_javadoc_comment(entity: Dict[str, Any]) -> str:
    """Generate a conservative Javadoc block for a class or method."""
    indent = entity.get("indent", "")
    name = entity.get("name", "Item")
    kind = entity.get("kind", "method")
    parameters = entity.get("parameters") or []
    return_type = (entity.get("return_type") or "").strip()

    lines = [f"{indent}/**", f"{indent} * TODO: Describe {kind} {name}."]
    if kind == "class":
        lines.append(f"{indent} *")
        lines.append(f"{indent} * @author TODO")
    else:
        if parameters:
            lines.append(f"{indent} *")
            for parameter in parameters:
                lines.append(f"{indent} * @param {_parameter_name(parameter)} TODO")
        if return_type and return_type.lower() not in {"void", entity.get("class_name", "").lower()}:
            lines.append(f"{indent} * @return TODO")
    lines.append(f"{indent} */")
    return "\n".join(lines)


def generate_javadoc_comment_llm(entity: Dict[str, Any], source: str) -> str:
    """Generate a richer JavaDoc comment using the configured LLM when available."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or ChatGroq is None or HumanMessage is None:
        return generate_javadoc_comment(entity)

    model_name = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")
    prompt = f"""
You write concise, production-friendly JavaDoc comments.
Generate only the JavaDoc block, no prose, no markdown fences.

Requirements:
- Use standard JavaDoc syntax.
- Keep the first sentence short and specific.
- Mention parameters and return value only when relevant.
- Do not invent behavior that is not evident from the code.

Target kind: {entity.get('kind', 'method')}
Name: {entity.get('name', 'Item')}
Parameters: {entity.get('parameters') or []}
Return type: {entity.get('return_type', 'void')}

Source:
{source}

Return only a JavaDoc block.
"""

    try:
        model = ChatGroq(model=model_name, temperature=0.2, max_retries=1)
        response = model.invoke([HumanMessage(content=prompt)])
        content = (getattr(response, "content", "") or "").strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:java)?\s*|```$", "", content, flags=re.DOTALL).strip()
        if content.startswith("/**") and content.endswith("*/"):
            return content
    except Exception:
        pass

    return generate_javadoc_comment(entity)


def _write_file_content(file_path: str, content: str) -> None:
    with open(file_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def apply_javadoc_to_file(file_path: str, entity: Dict[str, Any], javadoc_text: Optional[str] = None) -> bool:
    """Insert a Javadoc block above a Java entity in place."""
    source = _read_file_with_encoding(file_path)
    lines = source.splitlines()
    insert_index = max(0, int(entity.get("line", 1)) - 1)
    comment = javadoc_text or generate_javadoc_comment(entity)

    if _java_has_javadoc_before(lines, int(entity.get("line", 1))):
        return False

    new_lines = lines[:insert_index] + [comment] + lines[insert_index:]
    new_source = "\n".join(new_lines)
    if source.endswith("\n") or new_source:
        new_source += "\n"

    _write_file_content(file_path, new_source)
    return True


def apply_javadocs_to_file(file_path: str, entities: List[Dict[str, Any]], use_llm: bool = True) -> int:
    """Insert Javadocs for multiple entities in reverse line order.
    
    Args:
        file_path: Path to the Java file.
        entities: List of Java entities (classes/methods) needing Javadocs.
        use_llm: If True, attempt LLM-backed generation; fallback to template.
    
    Returns:
        Number of Javadocs successfully inserted.
    """
    if not entities:
        return 0

    source = _read_file_with_encoding(file_path)
    lines = source.splitlines()
    inserts: List[tuple[int, str]] = []
    for entity in entities:
        insert_index = max(0, int(entity.get("line", 1)) - 1)
        if use_llm:
            comment = generate_javadoc_comment_llm(entity, source)
        else:
            comment = generate_javadoc_comment(entity)
        inserts.append((insert_index, comment))

    inserted = 0
    for insert_index, comment in sorted(inserts, key=lambda item: item[0], reverse=True):
        entity_line = insert_index + 1
        if _java_has_javadoc_before(lines, entity_line):
            continue
        lines[insert_index:insert_index] = [comment]
        inserted += 1

    if inserted:
        new_source = "\n".join(lines) + "\n"
        _write_file_content(file_path, new_source)
    return inserted


def _extract_source_segment(source: str, start_line: int, end_line: int) -> str:
    """Return a source slice for the given 1-based line range."""
    lines = source.splitlines()
    start_index = max(0, start_line - 1)
    end_index = min(len(lines), max(start_index, end_line))
    return "\n".join(lines[start_index:end_index])


def _flatten_java_methods(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return all top-level and class methods from a Java analysis payload."""
    methods: List[Dict[str, Any]] = list(analysis.get("methods", []))
    for class_item in analysis.get("classes", []):
        methods.extend(class_item.get("methods", []))
    return methods


def analyze_java_optimizations(source: str, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate conservative optimization suggestions for Java methods."""
    findings: List[Dict[str, Any]] = []

    for method in _flatten_java_methods(analysis):
        start_line = int(method.get("line", 1))
        end_line = int(method.get("end_line", start_line))
        method_source = _extract_source_segment(source, start_line, end_line)
        method_name = method.get("name", "method")
        body = method_source

        size_call_match = re.search(r"\b([A-Za-z_][A-Za-z0-9_]*)\.size\(\)", body)
        size_loop_match = None
        if size_call_match:
            collection_name = size_call_match.group(1)
            size_loop_match = re.search(rf"for\s*\([^\)]*{re.escape(collection_name)}\.size\(\)[^\)]*\)", body)
        if size_loop_match and size_call_match:
            collection_name = size_call_match.group(1)
            loop_header = size_loop_match.group(0)
            loop_start = size_loop_match.start()
            open_brace_index = body.find("{", size_loop_match.end() - 1)
            block_end = _find_brace_block_end(body, open_brace_index) if open_brace_index != -1 else size_loop_match.end()
            original_block = body[loop_start:block_end]
            size_var_name = f"{collection_name}Size"
            optimized_header = loop_header.replace(
                f"{collection_name}.size()",
                size_var_name,
                1,
            )
            optimized_block = original_block.replace(loop_header, f"int {size_var_name} = {collection_name}.size();\n{optimized_header}", 1)
            findings.append({
                "title": f"Cache {collection_name}.size() in loop",
                "line": start_line,
                "method_name": method_name,
                "pattern": "repeated-size-check",
                "auto_apply": True,
                "explanation": (
                    f"The method {method_name} checks {collection_name}.size() inside the loop condition. "
                    "If the collection size does not change, cache it in a local variable to reduce repeated calls."
                ),
                "original_code": original_block,
                "optimized_code": optimized_block,
            })

        string_loop_match = re.search(r"for\s*\([^)]*\)\s*\{(?:(?!for\s*\().)*\b(?:String\s+)?\w+\s*=\s*[^;]*\+[^;]*;", body, re.DOTALL)
        if string_loop_match:
            findings.append({
                "title": f"Use StringBuilder in {method_name}",
                "line": start_line,
                "method_name": method_name,
                "pattern": "string-concat-in-loop",
                "auto_apply": False,
                "explanation": (
                    f"The method {method_name} appears to build strings inside a loop using concatenation. "
                    "In Java, this creates many temporary String objects. Use StringBuilder for better performance."
                ),
                "original_code": string_loop_match.group(0),
                "optimized_code": (
                    "// Replace with:\n"
                    "StringBuilder builder = new StringBuilder();\n"
                    "for (...) {\n"
                    "    builder.append(...);\n"
                    "}\n"
                    "return builder.toString();"
                ),
            })

        line_count = len([line for line in method_source.splitlines() if line.strip()])
        nested_loop_count = len(re.findall(r"(?m)^\s*for\s*\(", method_source)) + len(re.findall(r"(?m)^\s*while\s*\(", method_source))
        if line_count >= 35 or nested_loop_count >= 2:
            findings.append({
                "title": f"Extract a helper method from {method_name}",
                "line": start_line,
                "method_name": method_name,
                "pattern": "long-method",
                "explanation": (
                    f"The method {method_name} is relatively large or contains multiple loops. "
                    "Breaking it into smaller helpers improves readability, testability, and change isolation."
                ),
                "original_code": method_source[:500].rstrip(),
                "optimized_code": (
                    "// Suggested refactor:\n"
                    f"private void {method_name}Helper(/* extracted inputs */) {{\n"
                    "    // move a focused portion of the logic here\n"
                    "}"
                ),
            })

        if re.search(r"\bSystem\.out\.(print|println|printf)\(", body):
            findings.append({
                "title": f"Replace console output in {method_name}",
                "line": start_line,
                "method_name": method_name,
                "pattern": "console-output",
                "auto_apply": False,
                "explanation": (
                    f"The method {method_name} writes directly to System.out. "
                    "If this is production code, a logger is usually easier to control and test."
                ),
                "original_code": "System.out.println(...)",
                "optimized_code": "logger.info(...);",
            })

    return findings


def apply_java_optimization_to_file(file_path: str, original_code: str, optimized_code: str) -> bool:
    """Apply a small Java refactor by replacing a matched snippet in place."""
    if not original_code or not optimized_code:
        return False

    source = _read_file_with_encoding(file_path)
    if original_code not in source:
        return False

    updated = source.replace(original_code, optimized_code, 1)
    _write_file_content(file_path, updated if updated.endswith("\n") else updated + "\n")
    return True


def _java_has_javadoc_before(lines: List[str], entity_line: int) -> bool:
    """Check whether a Javadoc block appears immediately above a Java entity."""
    index = entity_line - 2
    if index < 0 or index >= len(lines):
        return False
    return lines[index].strip().endswith("*/")


def _parse_javac_output(output: str) -> List[Dict[str, Any]]:
    """Parse javac error output into structured diagnostics."""
    diagnostics: List[Dict[str, Any]] = []
    if not output.strip():
        return diagnostics

    lines = output.splitlines()
    error_pattern = re.compile(r"^(?P<file>.+?\.java):(?P<line>\d+):\s*error:\s*(?P<message>.+)$")
    index = 0
    while index < len(lines):
        current_line = lines[index]
        match = error_pattern.match(current_line.strip())
        if not match:
            index += 1
            continue

        column = None
        source_line = ""
        if index + 1 < len(lines):
            source_line = lines[index + 1].rstrip()
        if index + 2 < len(lines):
            caret_line = lines[index + 2]
            caret_index = caret_line.find("^")
            if caret_index >= 0:
                column = caret_index + 1

        diagnostics.append({
            "line": int(match.group("line")),
            "column": column,
            "message": match.group("message").strip(),
            "source": source_line,
        })
        index += 1

    return diagnostics


def get_java_syntax_errors(file_path: str) -> List[Dict[str, Any]]:
    """Return javac diagnostics for a Java source file with line numbers."""
    if not os.path.exists(file_path):
        return []

    try:
        with tempfile.TemporaryDirectory(prefix="java-compile-") as output_dir:
            result = subprocess.run(
                ["javac", "-Xdiags:verbose", "-d", output_dir, file_path],
                capture_output=True,
                text=True,
                check=False,
            )
    except FileNotFoundError:
        return []
    except Exception:
        return []

    if result.returncode == 0:
        return []

    compiler_output = "\n".join(part for part in [result.stderr, result.stdout] if part)
    return _parse_javac_output(compiler_output)


def get_java_file_report(file_path: str) -> Dict[str, Any]:
    """Return a best-effort quality report for a Java source file."""
    source = _read_file_with_encoding(file_path)
    analysis = extract_java_entities(source)
    classes = analysis.get("classes", [])
    methods = _flatten_java_methods(analysis)
    lines = source.splitlines()

    missing_javadocs: List[Dict[str, Any]] = []
    for entity in classes + methods:
        entity_line = int(entity.get("line", 1))
        if not _java_has_javadoc_before(lines, entity_line):
            missing_javadocs.append({
                "name": entity.get("name"),
                "kind": entity.get("kind"),
                "line": entity_line,
                "signature": entity.get("signature", ""),
            })

    optimizations = analyze_java_optimizations(source, analysis)
    syntax_errors = get_java_syntax_errors(file_path)
    lines_count = len([line for line in lines if line.strip()])
    javadoc_count = len(classes) + len(methods) - len(missing_javadocs)

    return {
        "file_path": file_path,
        "file_name": os.path.basename(file_path),
        "classes": len(classes),
        "methods": len(methods),
        "non_empty_lines": lines_count,
        "missing_javadocs": missing_javadocs,
        "missing_javadocs_count": len(missing_javadocs),
        "documented_count": javadoc_count,
        "optimization_findings": optimizations,
        "optimization_count": len(optimizations),
        "syntax_errors": syntax_errors,
        "syntax_error_count": len(syntax_errors),
        "has_syntax_error": len(syntax_errors) > 0,
        "has_javascript_like_console_output": bool(re.search(r"\bSystem\.out\.(print|println|printf)\(", source)),
        "analysis": analysis,
    }


def get_java_workspace_report(file_paths: List[str]) -> Dict[str, Any]:
    """Aggregate Java quality metrics for a list of source files."""
    reports = [get_java_file_report(path) for path in file_paths if os.path.exists(path)]
    total_classes = sum(report["classes"] for report in reports)
    total_methods = sum(report["methods"] for report in reports)
    total_missing = sum(report["missing_javadocs_count"] for report in reports)
    total_findings = sum(report["optimization_count"] for report in reports)
    total_syntax_errors = sum(report.get("syntax_error_count", 0) for report in reports)
    files_with_syntax_errors = sum(1 for report in reports if report.get("has_syntax_error", False))
    return {
        "file_count": len(reports),
        "total_classes": total_classes,
        "total_methods": total_methods,
        "total_missing_javadocs": total_missing,
        "total_optimization_findings": total_findings,
        "total_syntax_errors": total_syntax_errors,
        "files_with_syntax_errors": files_with_syntax_errors,
        "file_reports": reports,
    }


def generate_java_optimization_summary_llm(source: str, analysis: Dict[str, Any]) -> str:
    """Generate a short optimization summary using the configured LLM when available."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or ChatGroq is None or HumanMessage is None:
        findings = analyze_java_optimizations(source, analysis)
        if not findings:
            return "No obvious Java optimization opportunities were detected."
        return "\n".join(f"- {finding['title']}: {finding['explanation']}" for finding in findings[:5])

    model_name = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")
    classes = [item.get("name") for item in analysis.get("classes", [])]
    methods = [item.get("name") for item in _flatten_java_methods(analysis)]

    prompt = f"""
You are reviewing Java code for safe, practical optimization opportunities.
Return a short markdown bullet list of at most 5 items.
Be conservative. Do not suggest risky rewrites.

Known classes: {classes}
Known methods: {methods}

Source:
{source}
"""

    try:
        model = ChatGroq(model=model_name, temperature=0.2, max_retries=1)
        response = model.invoke([HumanMessage(content=prompt)])
        content = (getattr(response, "content", "") or "").strip()
        if content:
            return content
    except Exception:
        pass

    findings = analyze_java_optimizations(source, analysis)
    if not findings:
        return "No obvious Java optimization opportunities were detected."
    return "\n".join(f"- {finding['title']}: {finding['explanation']}" for finding in findings[:5])


def summarize_java_entities(analysis: Dict[str, Any]) -> Dict[str, int]:
    """Summarize Java entity counts for the UI."""
    classes = analysis.get("classes", [])
    methods = analysis.get("methods", [])
    class_methods = sum(len(item.get("methods", [])) for item in classes)
    return {
        "classes": len(classes),
        "methods": len(methods) + class_methods,
    }
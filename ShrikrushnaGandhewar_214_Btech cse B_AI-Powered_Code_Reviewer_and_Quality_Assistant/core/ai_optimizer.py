"""AI optimizer for performance and readability improvements."""

import ast
import json
import os
import re
import subprocess
import tempfile
import textwrap
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

try:
    from langchain_core.messages import HumanMessage
    from langchain_groq import ChatGroq
except Exception:  # pragma: no cover - optional dependency
    ChatGroq = None
    HumanMessage = None


load_dotenv()


def _read_file_with_encoding(file_path: str) -> str:
    """Read a file using a small encoding fallback chain."""
    encodings = ["utf-8", "utf-16", "utf-8-sig", "latin-1", "cp1252"]
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as handle:
                return handle.read()
        except (UnicodeDecodeError, UnicodeError):
            continue

    with open(file_path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read()


def _is_python_file(file_path: Optional[str]) -> bool:
    """Return True when the path looks like a Python source file."""
    return bool(file_path) and file_path.lower().endswith(".py")


def _is_java_file(file_path: Optional[str]) -> bool:
    """Return True when the path looks like a Java source file."""
    return bool(file_path) and file_path.lower().endswith(".java")


def _is_valid_python_source(source: str) -> bool:
    """Return True when source parses as Python."""
    try:
        compile(source, "<optimizer-check>", "exec")
        return True
    except SyntaxError:
        return False


def _is_valid_java_file(file_path: str) -> bool:
    """Return True when a Java file compiles with javac diagnostics enabled."""
    if not file_path or not os.path.exists(file_path):
        return False

    try:
        with tempfile.TemporaryDirectory(prefix="java-optimizer-validate-") as out_dir:
            result = subprocess.run(
                ["javac", "-Xdiags:verbose", "-d", out_dir, file_path],
                capture_output=True,
                text=True,
                check=False,
            )
        return result.returncode == 0
    except Exception:
        return False


def _get_python_syntax_error(source: str, file_path: Optional[str] = None) -> Optional[SyntaxError]:
    """Return a SyntaxError (or subclass) for invalid Python source, else None."""
    filename = file_path or "<unknown>"
    try:
        compile(source, filename, "exec")
        return None
    except SyntaxError as exc:
        return exc


def _write_file_with_rollback(file_path: str, new_content: str, original_content: str) -> bool:
    """Write content, then restore the original if a Python syntax check fails."""
    try:
        with open(file_path, "w", encoding="utf-8") as handle:
            handle.write(new_content)
            handle.flush()
            os.fsync(handle.fileno())

        invalid_python = _is_python_file(file_path) and not _is_valid_python_source(new_content)
        invalid_java = _is_java_file(file_path) and not _is_valid_java_file(file_path)
        if invalid_python or invalid_java:
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write(original_content)
                handle.flush()
                os.fsync(handle.fileno())
            return False

        return True
    except Exception:
        return False


def _strip_code_fences(text: str) -> str:
    """Remove markdown fences and surrounding prose from LLM output."""
    if not text:
        return ""

    cleaned = text.strip()
    if "```" not in cleaned:
        return cleaned

    # Match any code block: ```[language] ... ```
    match = re.search(r"```(?:\w+)?\s*(.*?)```", cleaned, flags=re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Fallback: remove fences manually if regex fails for some reason
    lines = cleaned.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    
    return "\n".join(lines).strip()


def _normalize_indentation(source: str, replacement: str) -> str:
    """Reindent replacement text to match the original source block."""
    source_lines = [line for line in source.splitlines() if line.strip()]
    replacement = _strip_code_fences(replacement)
    if not replacement:
        return replacement

    indent_prefix = ""
    if source_lines:
        first_line = source_lines[0]
        indent_prefix = first_line[: len(first_line) - len(first_line.lstrip())]

    dedented = textwrap.dedent(replacement).strip("\n")
    rebuilt_lines = []
    for line in dedented.splitlines():
        if line.strip():
            rebuilt_lines.append(indent_prefix + line)
        else:
            rebuilt_lines.append("")

    return "\n".join(rebuilt_lines).rstrip() + "\n"


def _normalize_snippet_for_match(text: str) -> str:
    """Normalize a code snippet so it can be matched despite whitespace drift."""
    stripped = _strip_code_fences(text or "").strip("\n")
    if not stripped:
        return ""

    lines = [line.rstrip() for line in stripped.splitlines() if line.strip()]
    return "\n".join(lines).strip()


def _replace_snippet_whitespace_tolerant(content: str, original_code: str, optimized_code: str) -> Optional[str]:
    """Replace a snippet using a whitespace-tolerant fallback when exact matching fails."""
    normalized_original = _normalize_snippet_for_match(original_code)
    if not normalized_original:
        return None

    original_lines = [re.escape(line.strip()) for line in normalized_original.splitlines() if line.strip()]
    if not original_lines:
        return None

    pattern = r"\s+".join(original_lines)
    try:
        updated, count = re.subn(pattern, optimized_code, content, count=1, flags=re.DOTALL)
    except re.error:
        return None

    return updated if count else None


def _get_segment(source: str, node: ast.AST) -> str:
    """Return a source segment for a node."""
    segment = ast.get_source_segment(source, node)
    if segment:
        return segment

    start = getattr(node, "lineno", None)
    end = getattr(node, "end_lineno", None)
    if start is None or end is None:
        return ""

    lines = source.splitlines()
    return "\n".join(lines[start - 1:end])


def _get_name(node: ast.AST) -> Optional[str]:
    """Return the name for a simple AST name node."""
    if isinstance(node, ast.Name):
        return node.id
    return None


def _is_len_range_loop(node: ast.For) -> bool:
    """Check whether a for-loop iterates over range(len(...))."""
    if not isinstance(node.iter, ast.Call) or not isinstance(node.iter.func, ast.Name):
        return False
    if node.iter.func.id != "range" or len(node.iter.args) != 1:
        return False

    inner_call = node.iter.args[0]
    if not isinstance(inner_call, ast.Call) or not isinstance(inner_call.func, ast.Name):
        return False

    return inner_call.func.id == "len" and len(inner_call.args) == 1 and isinstance(inner_call.args[0], ast.Name)


def _extract_len_range_parts(node: ast.For) -> tuple[str, str, str]:
    """Extract index name, collection name, and a suggested item name."""
    index_name = _get_name(node.target) or "index"
    collection_name = "items"
    inner_call = node.iter.args[0]
    if isinstance(inner_call, ast.Call) and inner_call.args and isinstance(inner_call.args[0], ast.Name):
        collection_name = inner_call.args[0].id

    item_name = "item"
    if collection_name.endswith("s") and len(collection_name) > 1:
        item_name = collection_name[:-1]

    return index_name, collection_name, item_name


def _rewrite_len_range_loop(source_segment: str, index_name: str, collection_name: str, item_name: str) -> str:
    """Rewrite a len(range()) loop into direct iteration when safe."""
    lines = source_segment.splitlines()
    if not lines:
        return source_segment

    header = lines[0]
    indent = header[: len(header) - len(header.lstrip())]
    body = "\n".join(lines[1:])

    body = body.replace(f"{collection_name}[{index_name}]", item_name)
    body = re.sub(rf"\b{re.escape(index_name)}\b", item_name, body)

    rewritten = [f"{indent}for {item_name} in {collection_name}:"]
    if body.strip():
        rewritten.append(body)
    else:
        rewritten.append(f"{indent}    pass")

    return "\n".join(rewritten).rstrip() + "\n"


def _detect_range_len_candidate(tree: ast.AST, source: str) -> Optional[Dict[str, Any]]:
    """Detect the common range(len(...)) anti-pattern."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.For) or not _is_len_range_loop(node):
            continue

        index_name, collection_name, item_name = _extract_len_range_parts(node)
        source_segment = _get_segment(source, node)
        if not source_segment:
            continue

        rewritten = _rewrite_len_range_loop(source_segment, index_name, collection_name, item_name)
        if rewritten == source_segment:
            continue

        return {
            "pattern": "range_len_loop",
            "title": "Iterating by index through a list",
            "improvement_type": "Loop Optimization / Pythonic Refactor",
            "complexity_before": "O(n)",
            "complexity_after": "O(n)",
            "line": getattr(node, "lineno", 0),
            "end_line": getattr(node, "end_lineno", getattr(node, "lineno", 0)),
            "original_code": source_segment,
            "optimized_code": rewritten,
            "explanation": "Iterating directly over items removes unnecessary index lookups and makes the loop easier to read while preserving behavior.",
            "score": 90,
            "auto_apply": True,
        }

    return None


def _detect_nested_membership_candidate(tree: ast.AST, source: str) -> Optional[Dict[str, Any]]:
    """Detect nested loops that can be collapsed into set membership."""
    for outer in ast.walk(tree):
        if not isinstance(outer, ast.For) or not _is_len_range_loop(outer):
            continue

        outer_index, outer_collection, outer_item = _extract_len_range_parts(outer)
        for inner in outer.body:
            if not isinstance(inner, ast.For) or not _is_len_range_loop(inner):
                continue

            inner_index, inner_collection, _ = _extract_len_range_parts(inner)
            if not inner.body:
                continue

            compare_node = None
            for inner_stmt in inner.body:
                if isinstance(inner_stmt, ast.If) and isinstance(inner_stmt.test, ast.Compare):
                    compare_node = inner_stmt
                    break

            if compare_node is None:
                continue

            if len(compare_node.test.ops) != 1 or not isinstance(compare_node.test.ops[0], ast.Eq):
                continue

            left = compare_node.test.left
            right = compare_node.test.comparators[0]

            if not isinstance(left, ast.Subscript) or not isinstance(right, ast.Subscript):
                continue

            left_name = _get_name(left.value)
            right_name = _get_name(right.value)
            if left_name != outer_collection or right_name != inner_collection:
                continue

            if not isinstance(left.slice, ast.Name) or not isinstance(right.slice, ast.Name):
                continue

            if left.slice.id != outer_index or right.slice.id != inner_index:
                continue

            if not compare_node.body:
                continue

            action_source = _get_segment(source, compare_node)
            if not action_source:
                continue

            action_lines = []
            for stmt in compare_node.body:
                stmt_source = _get_segment(source, stmt)
                if stmt_source:
                    action_lines.append(stmt_source)

            if not action_lines:
                continue

            item_name = outer_item
            rewritten = [f"b_set = set({inner_collection})", f"for {item_name} in {outer_collection}:", f"    if {item_name} in b_set:"]
            for action_line in action_lines:
                cleaned = action_line.replace(f"{outer_collection}[{outer_index}]", item_name)
                cleaned = cleaned.replace(f"{inner_collection}[{inner_index}]", item_name)
                cleaned = re.sub(rf"\b{re.escape(outer_index)}\b", item_name, cleaned)
                cleaned = re.sub(rf"\b{re.escape(inner_index)}\b", item_name, cleaned)
                rewritten.append("        " + cleaned.strip())

            return {
                "pattern": "nested_loops_membership",
                "title": "Nested loops performing repeated membership checks",
                "improvement_type": "Loop Optimization / Reduce Complexity",
                "complexity_before": "O(n²)",
                "complexity_after": "O(n)",
                "line": getattr(outer, "lineno", 0),
                "end_line": getattr(inner, "end_lineno", getattr(inner, "lineno", 0)),
                "original_code": _get_segment(source, outer),
                "optimized_code": "\n".join(rewritten).rstrip() + "\n",
                "explanation": "Convert the inner scan into a set membership test so each lookup is constant-time instead of scanning the second collection repeatedly.",
                "score": 100,
                "auto_apply": True,
            }

    return None


def _detect_unnecessary_if_else_candidate(tree: ast.AST, source: str) -> Optional[Dict[str, Any]]:
    """Detect small if/else blocks that can be simplified."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.If) or len(node.body) != 1 or len(node.orelse) != 1:
            continue

        if not isinstance(node.body[0], ast.Return) or not isinstance(node.orelse[0], ast.Return):
            continue

        body_return = node.body[0].value
        else_return = node.orelse[0].value
        if body_return is None or else_return is None:
            continue

        if isinstance(body_return, ast.Constant) and isinstance(else_return, ast.Constant):
            if {body_return.value, else_return.value} <= {True, False}:
                optimized = f"return {ast.unparse(node.test)}"
            else:
                optimized = f"return {ast.unparse(node.test)} if {ast.unparse(node.test)} else {ast.unparse(else_return)}"
        else:
            optimized = f"return {ast.unparse(body_return)} if {ast.unparse(node.test)} else {ast.unparse(else_return)}"

        source_segment = _get_segment(source, node)
        if not source_segment:
            continue

        indent = source_segment.splitlines()[0][: len(source_segment.splitlines()[0]) - len(source_segment.splitlines()[0].lstrip())]
        optimized = textwrap.indent(optimized.strip(), indent) + "\n"

        return {
            "pattern": "unnecessary_if_else",
            "title": "Unnecessary if/else return block",
            "improvement_type": "Remove Redundancy / Pythonic Refactor",
            "complexity_before": "O(1)",
            "complexity_after": "O(1)",
            "line": getattr(node, "lineno", 0),
            "end_line": getattr(node, "end_lineno", getattr(node, "lineno", 0)),
            "original_code": source_segment,
            "optimized_code": optimized,
            "explanation": "A direct return expression removes branching noise and makes the intent easier to scan.",
            "score": 60,
            "auto_apply": True,
        }

    return None


def _detect_repeated_calculation_candidate(tree: ast.AST, source: str) -> Optional[Dict[str, Any]]:
    """Detect repeated pure expressions inside a loop."""
    for loop in ast.walk(tree):
        if not isinstance(loop, (ast.For, ast.While)):
            continue

        expressions: Dict[str, int] = {}
        expression_nodes: Dict[str, ast.AST] = {}
        for node in ast.walk(loop):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "len" and len(node.args) == 1:
                expr = ast.unparse(node)
                expressions[expr] = expressions.get(expr, 0) + 1
                expression_nodes[expr] = node

        repeated = [expr for expr, count in expressions.items() if count >= 2]
        if not repeated:
            continue

        expr = repeated[0]
        loop_source = _get_segment(source, loop)
        if not loop_source:
            continue

        if not isinstance(expression_nodes[expr].args[0], ast.Name):
            continue

        cached_name = f"{expression_nodes[expr].args[0].id}_len"
        indented_loop = loop_source.splitlines()
        first_line = indented_loop[0]
        indent = first_line[: len(first_line) - len(first_line.lstrip())]
        optimized = [f"{indent}{cached_name} = {expr}"]
        for line in indented_loop:
            optimized.append(line.replace(expr, cached_name))

        return {
            "pattern": "repeated_calculation",
            "title": "Repeated calculation inside a loop",
            "improvement_type": "Remove Redundancy / Reduce Complexity",
            "complexity_before": "O(n)",
            "complexity_after": "O(n)",
            "line": getattr(loop, "lineno", 0),
            "end_line": getattr(loop, "end_lineno", getattr(loop, "lineno", 0)),
            "original_code": loop_source,
            "optimized_code": "\n".join(optimized).rstrip() + "\n",
            "explanation": "Hoisting a repeated pure expression out of the loop prevents recomputing the same value on every iteration.",
            "score": 55,
            "auto_apply": True,
        }

    return None


def _detect_long_function_candidate(tree: ast.AST, source: str) -> Optional[Dict[str, Any]]:
    """Detect functions that are long enough to benefit from refactoring."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue

        end_line = getattr(node, "end_lineno", node.lineno)
        length = end_line - node.lineno + 1
        if length < 35:
            continue

        return {
            "pattern": "long_function",
            "title": "Long function that should be split or simplified",
            "improvement_type": "Reduce Complexity / Readability Refactor",
            "complexity_before": "Higher cognitive complexity",
            "complexity_after": "Lower cognitive complexity",
            "line": node.lineno,
            "end_line": end_line,
            "original_code": _get_segment(source, node),
            "optimized_code": None,
            "explanation": "Breaking a long function into focused helpers improves readability, testability, and future maintenance.",
            "score": 20,
            "auto_apply": False,
        }

    return None


def _remove_docstrings_from_source(source: str) -> str:
    """Remove all docstrings from the source code, keeping only executable code."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source

    # Collect line numbers that belong to docstrings
    docstring_lines = set()

    for node in ast.walk(tree):
        # Check if this node has a docstring
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            # Docstring is the first statement and must be an Expr with a Constant string
            if (node.body and 
                isinstance(node.body[0], ast.Expr) and 
                isinstance(node.body[0].value, ast.Constant) and 
                isinstance(node.body[0].value.value, str)):
                doc_node = node.body[0]
                start = getattr(doc_node, 'lineno', None)
                end = getattr(doc_node, 'end_lineno', None)
                if start and end:
                    for line_num in range(start, end + 1):
                        docstring_lines.add(line_num)

    # Rebuild source without docstring lines
    lines = source.splitlines()
    filtered_lines = [line for i, line in enumerate(lines, start=1) if i not in docstring_lines]
    return '\n'.join(filtered_lines)


def _detect_duplicate_code_candidate(source: str) -> Optional[Dict[str, Any]]:
    """Detect simple duplicated blocks of code (ignoring docstrings)."""
    # Remove docstrings to focus on actual code duplicates
    source_without_docs = _remove_docstrings_from_source(source)
    
    lines = [line.rstrip() for line in source_without_docs.splitlines()]
    normalized = [line.strip() for line in lines if line.strip()]
    seen = {}
    for index, line in enumerate(normalized):
        seen[line] = seen.get(line, 0) + 1

    repeated_line = next((line for line, count in seen.items() if count >= 3), None)
    if not repeated_line:
        return None

    return {
        "pattern": "duplicate_code",
        "title": "Duplicate code detected",
        "improvement_type": "Remove Redundancy",
        "complexity_before": "O(n)",
        "complexity_after": "O(n)",
        "line": 1,
        "end_line": len(lines),
        "original_code": repeated_line,
        "optimized_code": None,
        "explanation": "Repeated code should be consolidated into a helper, loop, or shared branch to avoid drift and reduce maintenance cost.",
        "score": 10,
        "auto_apply": False,
    }


def _build_llm_prompt(candidate: Dict[str, Any]) -> str:
    """Build a prompt for the LLM optimizer."""
    return (
        "You are a senior Python performance engineer.\n"
        "Rewrite the given code into a faster, cleaner, more Pythonic version while preserving behavior.\n"
        "Rules:\n"
        "- Return only valid Python code. No markdown, no explanation.\n"
        "- Preserve indentation and functionality.\n"
        "- Prefer direct iteration, set membership, early returns, and hoisted calculations when appropriate.\n"
        f"- Improvement type: {candidate.get('improvement_type')}\n"
        f"- Complexity before: {candidate.get('complexity_before')}\n"
        f"- Complexity after: {candidate.get('complexity_after')}\n\n"
        f"Original code:\n{candidate.get('original_code', '')}\n"
    )


def _call_groq_llm(prompt: str) -> Optional[str]:
    """Call Groq through LangChain when available."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or ChatGroq is None or HumanMessage is None:
        return None

    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    try:
        llm = ChatGroq(model=model, temperature=0.2, api_key=api_key)
        response = llm.invoke([HumanMessage(content=prompt)])
        return _strip_code_fences(getattr(response, "content", "").strip())
    except Exception:
        return None


def _call_openai_llm(prompt: str) -> Optional[str]:
    """Call OpenAI Chat Completions if configured."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "You rewrite Python code for performance and readability."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
            },
            timeout=45,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        return _strip_code_fences(content)
    except Exception:
        return None


def _get_llm_optimized_code(candidate: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    """Try Groq first, then OpenAI, to generate a rewritten code block."""
    prompt = _build_llm_prompt(candidate)
    groq_result = _call_groq_llm(prompt)
    if groq_result:
        return groq_result, "groq"

    openai_result = _call_openai_llm(prompt)
    if openai_result:
        return openai_result, "openai"

    return None, None


def _generate_local_rewrite(candidate: Dict[str, Any]) -> Optional[str]:
    """Generate a conservative local rewrite when no LLM provider is available."""
    optimized_code = candidate.get("optimized_code")
    if optimized_code:
        return _normalize_indentation(candidate.get("original_code") or "", optimized_code)

    original_code = candidate.get("original_code") or ""
    if not original_code.strip():
        return None

    try:
        parsed = ast.parse(original_code)
        rebuilt = ast.unparse(parsed)
    except Exception:
        rebuilt = original_code

    rebuilt = rebuilt.strip()
    if not rebuilt:
        return None

    return _normalize_indentation(original_code, rebuilt)


def generate_rewrite_for_finding(candidate: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    """Request an LLM-generated rewrite for a single finding.

    Returns a tuple (optimized_code, provider) or (None, None) on failure.
    This is a thin wrapper around the internal LLM helper so the UI can
    request on-demand rewrites for specific findings.
    """
    try:
        optimized_code, provider = _get_llm_optimized_code(candidate)
        if optimized_code:
            return optimized_code, provider

        local_rewrite = _generate_local_rewrite(candidate)
        if local_rewrite:
            return local_rewrite, "local"

        return None, None
    except Exception:
        local_rewrite = _generate_local_rewrite(candidate)
        if local_rewrite:
            return local_rewrite, "local"
        return None, None


def _attempt_syntax_fix(source: str) -> tuple[Optional[str], Optional[str]]:
    """Attempt a small set of safe, deterministic syntax fixes and re-parse.

    Returns a tuple (fixed_source, None) on success or (None, error_message) on failure.
    The heuristics are intentionally conservative: normalize line endings and
    indentation, remove non-printable control characters, fix common keyword typos,
    and retry parsing.
    """
    try:
        # Normalization heuristics
        fixed = source.replace("\r\n", "\n").replace("\r", "\n")
        fixed = fixed.replace("\t", "    ")

        # Strip common non-printable control characters except newline/tab
        fixed = "".join(ch for ch in fixed if (ch >= " " or ch in "\n\t"))

        # Quick whitespace cleanup: collapse trailing whitespace on each line
        fixed_lines = [line.rstrip() for line in fixed.splitlines()]
        fixed = "\n".join(fixed_lines) + ("\n" if fixed_lines and not fixed_lines[-1].endswith("\n") else "")

        # Try full compile first; this catches cases ast.parse can miss
        syntax_exc = _get_python_syntax_error(fixed)
        if syntax_exc is None:
            return fixed, None

        # Fix common indentation-driven case: return/break/continue/pass outside function/loop
        fixed_outside_stmt = _fix_outside_block_statement(fixed, syntax_exc)
        if fixed_outside_stmt is not None:
            second_exc = _get_python_syntax_error(fixed_outside_stmt)
            if second_exc is None:
                return fixed_outside_stmt, None
            fixed = fixed_outside_stmt
            syntax_exc = second_exc

        # still failing, try keyword fixes
        return _fix_common_keyword_errors(fixed, str(syntax_exc))
    except Exception as exc:  # unexpected
        return None, str(exc)


def _repair_syntax_with_llm(source: str, error_msg: str) -> Optional[str]:
    """Use an LLM to specifically repair syntax/indentation errors when heuristics fail."""
    prompt = f"""
The following Python code has a syntax or indentation error.
Error: {error_msg}

Repair the code to be syntactically correct while preserving its original logic.
Be extremely careful with indentation levels for functions and control blocks.
Return ONLY the corrected code without any explanations, conversational filler, or markdown fences.

CODE:
{source}
"""
    api_key = os.getenv("GROQ_API_KEY")
    if api_key and ChatGroq and HumanMessage:
        try:
            llm = ChatGroq(model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"), temperature=0.1, api_key=api_key)
            response = llm.invoke([HumanMessage(content=prompt)])
            content = _strip_code_fences(getattr(response, "content", "").strip())
            return content
        except Exception:
            pass
            
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    "messages": [
                        {"role": "system", "content": "You are a Python syntax repair assistant. Return only the fixed code."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1
                },
                timeout=30,
            )
            if response.status_code == 200:
                result = response.json()
                return _strip_code_fences(result["choices"][0]["message"]["content"].strip())
        except Exception:
            pass
            
    return None


def _fix_outside_block_statement(source: str, exc: SyntaxError) -> Optional[str]:
    """Indent a misaligned control statement when compiler reports it outside a block."""
    message = str(exc).lower()
    # Handle 'outside function/loop' and indentation mismatch errors
    if "outside" not in message and "unindent does not match" not in message:
        return None

    lineno = getattr(exc, "lineno", None)
    if not lineno or lineno < 1:
        return None

    lines = source.splitlines()
    target_index = lineno - 1
    if target_index >= len(lines):
        return None

    target = lines[target_index]
    stripped = target.lstrip()
    if not stripped:
        return None

    statement_prefixes = ("return", "break", "continue", "pass")
    if not stripped.startswith(statement_prefixes):
        return None

    # Find a nearby previous non-empty line and reuse its indentation.
    prev_index = target_index - 1
    while prev_index >= 0 and not lines[prev_index].strip():
        prev_index -= 1
    if prev_index < 0:
        return None

    prev_line = lines[prev_index]
    prev_indent = prev_line[: len(prev_line) - len(prev_line.lstrip())]
    if not prev_indent and prev_line.strip().endswith(":"):
        prev_indent = "    "
    if not prev_indent:
        return None

    lines[target_index] = prev_indent + stripped
    fixed = "\n".join(lines)
    if source.endswith("\n"):
        fixed += "\n"
    return fixed


def _fix_common_keyword_errors(source: str, error_msg: str) -> tuple[Optional[str], Optional[str]]:
    """Fix common keyword typos and syntax errors.
    
    Handles:
    - 'de ' -> 'def ' (missing 'f')
    - 'clas ' -> 'class ' (missing 's')
    - 'imort ' -> 'import ' (missing 'p')
    - 'for' without ':' at end of line
    - 'if'/'elif'/'else'/'while' without ':' at end of line
    """
    import re
    
    fixed = source
    changed = False
    
    # Fix misspelled 'def' keyword
    pattern = r'^\s*de\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
    if re.search(pattern, fixed, re.MULTILINE):
        fixed = re.sub(pattern, lambda m: m.group(0).replace('de ', 'def ', 1), fixed, flags=re.MULTILINE)
        changed = True
    
    # Fix misspelled 'class' keyword
    pattern = r'^\s*clas\s+([a-zA-Z_][a-zA-Z0-9_]*)'
    if re.search(pattern, fixed, re.MULTILINE):
        fixed = re.sub(pattern, lambda m: m.group(0).replace('clas ', 'class ', 1), fixed, flags=re.MULTILINE)
        changed = True
    
    # Fix misspelled 'import' keyword
    pattern = r'^\s*imort\s+'
    if re.search(pattern, fixed, re.MULTILINE):
        fixed = re.sub(pattern, lambda m: m.group(0).replace('imort', 'import'), fixed, flags=re.MULTILINE)
        changed = True
    
    # Fix 'from' without 'import'
    pattern = r'^\s*form\s+'
    if re.search(pattern, fixed, re.MULTILINE):
        fixed = re.sub(pattern, lambda m: m.group(0).replace('form', 'from'), fixed, flags=re.MULTILINE)
        changed = True
    
    # Fix missing colon after control flow keywords
    keywords = ['for', 'if', 'elif', 'else', 'while', 'try', 'except', 'finally', 'with']
    for keyword in keywords:
        # Match keyword at start of line (with indentation) and check if it's missing ':'
        pattern = rf'(^\s*{keyword}\b[^:\n]*)$'
        matches = re.findall(pattern, fixed, re.MULTILINE)
        if matches:
            # Only add colon if the line doesn't already have one
            for match in matches:
                if not match.rstrip().endswith(':'):
                    fixed = fixed.replace(match + '\n', match + ':\n', 1)
                    changed = True
    
    if changed:
        try:
            compile(fixed, "<optimizer-keyword-fix>", "exec")
            return fixed, None
        except SyntaxError:
            # Fixes didn't work, return original error
            return None, error_msg
    
    return None, error_msg


def _pick_best_candidate(findings: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Choose the highest-value finding that can be shown as the main optimization."""
    if not findings:
        return None

    candidates = sorted(findings, key=lambda item: item.get("score", 0), reverse=True)
    for candidate in candidates:
        if candidate.get("optimized_code"):
            return candidate
    return candidates[0]

def _analyze_java_with_llm(source: str, file_path: Optional[str]) -> List[Dict[str, Any]]:
    """Use LLM to find optimizations in Java code."""
    prompt = (
        "You are a senior Java performance engineer. Analyze the following Java code and suggest multiple clear optimizations "
        "to improve performance, reduce complexity, or improve readability.\n"
        "PRIORITY: Strongly prefer algorithmic improvements (like using HashSets instead of nested loops) over syntax sugar.\n"
        "Return the result ONLY as a valid JSON array of objects (no markdown wrapping). Each object must have these exact keys:\n"
        "[\n"
        "  {\n"
        '    "pattern": "short_pattern_name",\n'
        '    "title": "Short title describing the optimization",\n'
        '    "improvement_type": "Loop Optimization / Reduce Complexity etc",\n'
        '    "complexity_before": "O(?)",\n'
        '    "complexity_after": "O(?)",\n'
        '    "line": 1,\n'
        '    "end_line": 2,\n'
        '    "original_code": "exact literal string of the original code block to replace (must be exact match including whitespace)",\n'
        '    "optimized_code": "the replacement Java code",\n'
        '    "explanation": "Why this is better",\n'
        '    "score": 95,\n'
        '    "auto_apply": true\n'
        "  }\n"
        "]\n\n"
        "Java Code:\n"
        f"{source}\n"
    )
    
    api_key = os.getenv("GROQ_API_KEY")
    if api_key and ChatGroq and HumanMessage:
        model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        try:
            llm = ChatGroq(model=model, temperature=0.1, api_key=api_key)
            response = llm.invoke([HumanMessage(content=prompt)])
            content = _strip_code_fences(getattr(response, "content", "").strip())
            findings = json.loads(content.strip())
            if not isinstance(findings, list):
                findings = [findings]
            for f in findings:
                f["llm_provider"] = "groq"
            return findings
        except Exception as e:
            print(f"Java optimization failed: {e}")
            pass
            
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are a Java optimization expert that strictly returns JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"}
                },
                timeout=45,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            findings = json.loads(content.strip())
            if not isinstance(findings, list):
                findings = [findings]
            for f in findings:
                f["llm_provider"] = "openai"
            return findings
        except Exception as e:
            print(f"Java optimization OpenAI failed: {e}")
            pass
            
    return []

def analyze_and_optimize_code(code_text: str, file_path: Optional[str] = None) -> Dict[str, Any]:
    """Analyze code and generate a high-confidence optimization suggestion."""
    source = code_text or ""
    result: Dict[str, Any] = {
        "file_path": file_path,
        "has_issue": False,
        "syntax_error": None,
        "syntax_error_type": None,
        "indentation_error": False,
        "syntax_fixed": False,
        "syntax_fix_note": None,
        "syntax_fix_error": None,
        "fixed_source": None,
        "findings": [],
        "detected_patterns": [],
        "current_code": None,
        "optimized_code": None,
        "improvement_type": None,
        "complexity_before": None,
        "complexity_after": None,
        "explanation": None,
        "line": None,
        "end_line": None,
        "llm_provider": None,
        "auto_apply": False,
        "message": None,
    }

    if not source.strip():
        result["message"] = "No code provided for optimization."
        return result

    if file_path and file_path.lower().endswith(".java"):
        findings = _analyze_java_with_llm(source, file_path)
        result["findings"] = findings
        result["detected_patterns"] = [finding.get("pattern", "unknown") for finding in findings]
        if not findings:
            result["message"] = "No clear optimization opportunity was detected."
            return result
            
        primary = _pick_best_candidate(findings)
        if primary:
            result.update({
                "has_issue": True,
                "current_code": primary.get("original_code"),
                "optimized_code": primary.get("optimized_code"),
                "improvement_type": primary.get("improvement_type"),
                "complexity_before": primary.get("complexity_before"),
                "complexity_after": primary.get("complexity_after"),
                "explanation": primary.get("explanation"),
                "line": primary.get("line"),
                "end_line": primary.get("end_line"),
                "llm_provider": primary.get("llm_provider"),
                "auto_apply": bool(primary.get("auto_apply", False)),
                "message": None,
            })
        return result

    syntax_exc = _get_python_syntax_error(source, file_path=file_path)
    if syntax_exc is not None:
        # Try a conservative heuristic-based syntax fix before giving up
        fixed_source, fix_err = _attempt_syntax_fix(source)
        result["syntax_error"] = str(syntax_exc)
        result["syntax_error_type"] = type(syntax_exc).__name__
        result["indentation_error"] = isinstance(syntax_exc, (IndentationError, TabError)) or (
            "indent" in str(syntax_exc).lower()
            or "outside function" in str(syntax_exc).lower()
        )
        if fixed_source:
            result["syntax_fixed"] = True
            result["syntax_fix_note"] = "A conservative automatic syntax normalization was applied; proceeding with analysis on the fixed source."
            result["fixed_source"] = fixed_source
            # continue analysis using the fixed source but preserve original in the result
            source = fixed_source
            second_exc = _get_python_syntax_error(source, file_path=file_path)
            if second_exc is not None:
                result["message"] = f"Syntax issues remain after automatic fix: {second_exc}"
                return result
            tree = ast.parse(source)
        else:
            # Fallback to LLM-based syntax repair if heuristics fail
            repaired_source = _repair_syntax_with_llm(source, str(syntax_exc))
            if repaired_source and _get_python_syntax_error(repaired_source) is None:
                result["syntax_fixed"] = True
                result["syntax_fix_note"] = "AI-powered syntax repair was applied to resolve complex indentation or structure issues."
                result["fixed_source"] = repaired_source
                source = repaired_source
                tree = ast.parse(source)
            else:
                # No auto-fix succeeded — provide a friendly message with context
                snippet_lines = source.splitlines()
                lineno = getattr(syntax_exc, "lineno", None)
                context = []
                if lineno and 1 <= lineno <= len(snippet_lines):
                    start = max(0, lineno - 3)
                    end = min(len(snippet_lines), lineno + 2)
                    for i in range(start, end):
                        prefix = "> " if (i + 1) == lineno else "  "
                        context.append(f"{prefix}{i+1:4d}: {snippet_lines[i]}")

                result["message"] = (
                    (
                        "Indentation error prevents optimization.\n"
                        if result.get("indentation_error")
                        else "Syntax error prevents optimization.\n"
                    )
                    + f"Error ({result.get('syntax_error_type')}): {syntax_exc}.\n"
                    "Context around the error:\n"
                    + ("\n".join(context) if context else snippet_lines[0:6]).__str__()
                )
                result["syntax_fixed"] = False
                result["syntax_fix_error"] = fix_err
                return result
    else:
        tree = ast.parse(source)

    findings: List[Dict[str, Any]] = []
    for finder in (
        _detect_nested_membership_candidate,
        _detect_range_len_candidate,
        _detect_repeated_calculation_candidate,
        _detect_unnecessary_if_else_candidate,
        _detect_long_function_candidate,
    ):
        candidate = finder(tree, source)
        if candidate:
            findings.append(candidate)

    # Duplicate-code detection can cause the LLM to attempt broad rewrites
    # which sometimes produce invalid syntax. Allow disabling this check via
    # the `DISABLE_DUPLICATE_DETECTION` environment variable so users who
    # experience syntax regressions can turn it off without losing other
    # optimizer functionality.
    duplicate_candidate = _detect_duplicate_code_candidate(source)
    disable_dup = os.getenv("DISABLE_DUPLICATE_DETECTION", "0").lower() in ("1", "true", "yes")
    if duplicate_candidate and not disable_dup:
        findings.append(duplicate_candidate)

    # Prepare optimized code for all findings when possible. If a finding does not
    # have a deterministic rewrite, ask the LLM to generate one for the preview.
    for cand in findings:
        if cand.get("optimized_code") is None:
            llm_code, llm_provider = _get_llm_optimized_code(cand)
            if llm_code:
                cand["optimized_code"] = _normalize_indentation(cand["original_code"], llm_code)
                cand["llm_provider"] = llm_provider

    # Allow disabling suggestions that are purely "Remove Redundancy" because
    # these sometimes produce LLM-driven edits that break syntax after applying.
    disable_remove = os.getenv("DISABLE_REMOVE_REDUNDANCY", "0").lower() in ("1", "true", "yes")
    if disable_remove:
        filtered: List[Dict[str, Any]] = []
        for f in findings:
            imp = (f.get("improvement_type") or "").lower()
            if "remove redundancy" in imp:
                continue
            filtered.append(f)
        findings = filtered

    result["findings"] = findings
    result["detected_patterns"] = [finding["pattern"] for finding in findings]

    if not findings:
        result["message"] = "No clear optimization opportunity was detected."
        return result

    # Select a primary candidate for the single-panel preview (highest score with an optimized code)
    primary = _pick_best_candidate(findings)
    if primary:
        result.update(
            {
                "has_issue": True,
                "current_code": primary.get("original_code"),
                "optimized_code": primary.get("optimized_code"),
                "improvement_type": primary.get("improvement_type"),
                "complexity_before": primary.get("complexity_before"),
                "complexity_after": primary.get("complexity_after"),
                "explanation": primary.get("explanation"),
                "line": primary.get("line"),
                "end_line": primary.get("end_line"),
                "llm_provider": primary.get("llm_provider"),
                "auto_apply": bool(primary.get("auto_apply", False)),
                "message": None,
            }
        )

    return result


def apply_syntax_fix_to_file(file_path: str, fixed_source: str) -> bool:
    """Write a syntax-repaired source block back to the target file."""
    if not file_path or not fixed_source:
        return False

    if not os.path.exists(file_path):
        return False

    original_source = _read_file_with_encoding(file_path)
    return _write_file_with_rollback(file_path, fixed_source, original_source)


def apply_multiple_optimizations(file_path: str, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Apply multiple optimized code blocks to a file in-memory, create one backup.

    Returns a summary dict with per-finding results and overall status.
    The function is conservative: it only replaces exact original_code matches and
    reports which replacements succeeded. Replacements are attempted in order of
    descending original_code length to reduce partial-overlap issues.
    """
    summary: Dict[str, Any] = {"file_path": file_path, "applied": [], "failed": []}
    if not file_path or not os.path.exists(file_path):
        summary["error"] = "file_missing"
        return summary

    content = _read_file_with_encoding(file_path)
    if content is None:
        summary["error"] = "could_not_read"
        return summary

    # Make a backup once
    backup_path = file_path + ".bak.optimize"
    try:
        with open(backup_path, "w", encoding="utf-8") as b:
            b.write(content)
    except Exception as exc:
        summary["error"] = f"backup_failed: {exc}"
        return summary

    # Apply from bottom to top so line offsets stay stable while we edit.
    ordered = sorted(
        [f for f in findings if f.get("optimized_code")],
        key=lambda item: int(item.get("line", 0) or 0),
        reverse=True,
    )

    new_lines = content.splitlines()
    for f in ordered:
        start_line = int(f.get("line", 0) or 0)
        end_line = int(f.get("end_line", start_line) or start_line)
        orig = f.get("original_code") or ""
        opt = _normalize_indentation(orig, f.get("optimized_code") or "")

        if start_line <= 0 or end_line < start_line:
            if orig in "\n".join(new_lines):
                updated_text = "\n".join(new_lines).replace(orig, opt, 1)
                new_lines = updated_text.splitlines()
                summary["applied"].append({"pattern": f.get("pattern"), "line": f.get("line")})
            else:
                summary["failed"].append({"pattern": f.get("pattern"), "line": f.get("line"), "reason": "original_not_found"})
            continue

        start_index = max(0, start_line - 1)
        end_index = min(len(new_lines), end_line)
        current_block = "\n".join(new_lines[start_index:end_index])
        
        # Robust matching: try exact, then try normalized whitespace
        if orig and orig not in current_block:
            # Try to see if it exists elsewhere in the file if line numbers were wrong
            if orig in content:
                # If it's in the original content but not in the current window, 
                # we can't safely replace by lines. Try string replacement on whole content.
                content_str = "\n".join(new_lines)
                if orig in content_str:
                    updated_text = content_str.replace(orig, opt, 1)
                    new_lines = updated_text.splitlines()
                    summary["applied"].append({"pattern": f.get("pattern"), "line": f.get("line")})
                    continue

            # Final attempt: normalized check within the line range
            if orig.strip() != current_block.strip():
                summary["failed"].append({"pattern": f.get("pattern"), "line": f.get("line"), "reason": "original_not_found"})
                continue

        replacement_lines = opt.rstrip("\n").splitlines()
        if opt.endswith("\n"):
            replacement_lines.append("")
        new_lines[start_index:end_index] = replacement_lines
        summary["applied"].append({"pattern": f.get("pattern"), "line": f.get("line")})

    try:
        new_content = "\n".join(new_lines)
        if content.endswith("\n") or new_content:
            new_content += "\n"
        with open(file_path, "w", encoding="utf-8") as handle:
            handle.write(new_content)
            handle.flush()
            os.fsync(handle.fileno())
        summary["status"] = "ok"
    except Exception as exc:
        summary["error"] = f"write_failed: {exc}"
        summary["status"] = "failed"

    return summary


def apply_optimized_code_to_file(file_path: str, original_code: str, optimized_code: str) -> bool:
    """Replace the original code block in a file and create a backup."""
    if not file_path or not os.path.exists(file_path):
        return False

    if not original_code or not optimized_code:
        return False

    original_optimized = optimized_code
    optimized_code = _normalize_indentation(original_code, optimized_code)
    if "\n" not in original_code and not original_optimized.endswith("\n"):
        optimized_code = optimized_code.rstrip("\n")

    content = _read_file_with_encoding(file_path)
    new_content = None
    if original_code in content:
        new_content = content.replace(original_code, optimized_code, 1)
    else:
        new_content = _replace_snippet_whitespace_tolerant(content, original_code, optimized_code)

    if not new_content:
        return False

    backup_path = file_path + ".bak.optimize"
    with open(backup_path, "w", encoding="utf-8") as backup_handle:
        backup_handle.write(content)

    return _write_file_with_rollback(file_path, new_content, content)


def apply_optimized_code_to_file_by_lines(
    file_path: str,
    start_line: int,
    end_line: int,
    optimized_code: str,
) -> bool:
    """Replace a source range using line numbers when exact text matching is brittle."""
    if not file_path or not os.path.exists(file_path):
        return False
    if not optimized_code:
        return False

    source = _read_file_with_encoding(file_path)
    lines = source.splitlines()
    start_index = max(0, int(start_line or 0) - 1)
    end_index = min(len(lines), int(end_line or start_line or 0))
    if start_index < 0 or start_index >= len(lines) or end_index < start_index:
        return False

    backup_path = file_path + ".bak.optimize"
    with open(backup_path, "w", encoding="utf-8") as backup_handle:
        backup_handle.write(source)

    source_block = "\n".join(lines[start_index:end_index])
    optimized_code = _normalize_indentation(source_block, optimized_code)
    replacement_lines = optimized_code.rstrip("\n").splitlines()
    if optimized_code.endswith("\n"):
        replacement_lines.append("")
    lines[start_index:end_index] = replacement_lines

    new_content = "\n".join(lines)
    if source.endswith("\n") or new_content:
        new_content += "\n"
    return _write_file_with_rollback(file_path, new_content, source)
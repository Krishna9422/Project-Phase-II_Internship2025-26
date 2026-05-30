"""
Function explanation module using LLM integration.

Provides reusable functions to:
- Extract function code from Python files using AST
- Generate explanations using Groq/OpenAI LLM
- Handle errors gracefully
"""

import ast
import os
import re
from typing import Optional, Dict, Any

from dotenv import load_dotenv

try:
    from langchain_groq import ChatGroq
    from langchain_core.messages import HumanMessage
except ImportError:
    ChatGroq = None
    HumanMessage = None


load_dotenv()

DEFAULT_GROQ_MODELS = (
    os.environ.get("GROQ_MODEL_NAME", "").strip(),
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
)


def _read_file_with_encoding(file_path: str) -> str:
    """
    Read file content with automatic encoding detection.
    
    Args:
        file_path: Path to the Python file
        
    Returns:
        File content as string
        
    Raises:
        FileNotFoundError: If file does not exist
    """
    encodings = ['utf-8', 'utf-16', 'utf-8-sig', 'latin-1', 'cp1252']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    
    # Fallback with error replacement
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()


def _fallback_extract_functions(source_code: str) -> list[Dict[str, Any]]:
    """Extract a best-effort function list from source that still has syntax errors."""
    functions: list[Dict[str, Any]] = []
    class_stack: list[tuple[str, int]] = []
    lines = source_code.splitlines()

    for line_number, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip())
        while class_stack and indent <= class_stack[-1][1] and not stripped.startswith(("def ", "async def ", "@")):
            class_stack.pop()

        class_match = re.match(r"^class\s+([A-Za-z_][A-Za-z0-9_]*)", stripped)
        if class_match:
            class_stack.append((class_match.group(1), indent))
            continue

        func_match = re.match(r"^(async\s+def|def)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", stripped)
        if not func_match:
            continue

        class_name = class_stack[-1][0] if class_stack and indent > class_stack[-1][1] else None
        function_name = func_match.group(2)
        display_name = f"{class_name}.{function_name}" if class_name else function_name

        functions.append({
            'name': function_name,
            'type': 'method' if class_name else 'function',
            'is_async': func_match.group(1).startswith('async'),
            'class_name': class_name,
            'line': line_number,
            'display_name': display_name,
        })

    return sorted(functions, key=lambda x: x['line'])


def _fallback_extract_java_methods(source_code: str) -> list[Dict[str, Any]]:
    """Extract a best-effort Java method list from source code."""
    from core.java_support import extract_java_entities

    analysis = extract_java_entities(source_code)
    methods: list[Dict[str, Any]] = []

    for method in analysis.get("methods", []):
        methods.append({
            "name": method.get("name", ""),
            "type": "method",
            "is_async": False,
            "class_name": method.get("class_name"),
            "line": int(method.get("line", 0) or 0),
            "display_name": method.get("name", ""),
        })

    for cls in analysis.get("classes", []):
        class_name = cls.get("name", "")
        for method in cls.get("methods", []):
            method_name = method.get("name", "")
            methods.append({
                "name": method_name,
                "type": "method",
                "is_async": False,
                "class_name": class_name,
                "line": int(method.get("line", 0) or 0),
                "display_name": f"{class_name}.{method_name}" if class_name else method_name,
            })

    return sorted(methods, key=lambda x: x['line'])


def extract_java_functions_from_file(file_path: str) -> list[Dict[str, Any]]:
    """Extract Java methods from a Java file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    if not file_path.endswith('.java'):
        raise ValueError(f"Not a Java file: {file_path}")

    source_code = _read_file_with_encoding(file_path)
    return _fallback_extract_java_methods(source_code)


def get_function_code(file_path: str, function_name: str) -> Optional[str]:
    """
    Extract the full source code of a function from a Python file using AST.
    
    Args:
        file_path: Absolute path to the Python file
        function_name: Name of the function to extract
        
    Returns:
        The full source code of the function, or None if not found
        
    Raises:
        FileNotFoundError: If file does not exist
        SyntaxError: If file has invalid Python syntax
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if not file_path.endswith('.py'):
        raise ValueError(f"Not a Python file: {file_path}")
    
    try:
        source_code = _read_file_with_encoding(file_path)
    except Exception as e:
        raise IOError(f"Cannot read file {file_path}: {str(e)}")
    
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        lines = source_code.splitlines()
        pattern = re.compile(rf"^(\s*)(async\s+def|def)\s+{re.escape(function_name)}\s*\(")
        for index, line in enumerate(lines):
            match = pattern.match(line)
            if not match:
                continue

            base_indent = len(match.group(1))
            collected = [line]
            for next_line in lines[index + 1 :]:
                stripped = next_line.strip()
                if stripped and not stripped.startswith("#"):
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent <= base_indent and not stripped.startswith(("elif ", "else:", "except ", "finally:")):
                        break
                collected.append(next_line)
            return "\n".join(collected)

        raise SyntaxError(f"Invalid Python syntax in {file_path}: {str(e)}")
    
    # Find the function in the AST
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == function_name:
                # Extract source segment using AST
                try:
                    code = ast.get_source_segment(source_code, node)
                    if code:
                        return code
                except Exception:
                    pass
                
                # Fallback: use line numbers
                if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                    lines = source_code.splitlines()
                    start_line = node.lineno - 1
                    end_line = node.end_lineno
                    if 0 <= start_line < len(lines) and 0 < end_line <= len(lines):
                        return '\n'.join(lines[start_line:end_line])
    
    return None


def get_java_function_code(file_path: str, function_name: str, class_name: str | None = None) -> Optional[str]:
    """Extract the full source code of a Java method or constructor."""
    from core.java_support import _read_file_with_encoding as _read_java_source
    from core.java_support import extract_java_entities

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    if not file_path.endswith('.java'):
        raise ValueError(f"Not a Java file: {file_path}")

    source_code = _read_java_source(file_path)
    analysis = extract_java_entities(source_code)

    candidates: list[Dict[str, Any]] = list(analysis.get("methods", []))
    for cls in analysis.get("classes", []):
        candidates.extend(cls.get("methods", []))

    for method in candidates:
        if method.get("name") != function_name:
            continue
        if class_name and method.get("class_name") != class_name:
            continue

        start_line = int(method.get("line", 1)) - 1
        end_line = int(method.get("end_line", start_line + 1))
        lines = source_code.splitlines()
        if 0 <= start_line < len(lines) and 0 < end_line <= len(lines):
            return "\n".join(lines[start_line:end_line])

    return None


def explain_function_llm(
    function_code: str,
    model: str = "llama-3.3-70b-versatile",
    language: str = "python"
) -> Dict[str, Any]:
    """
    Generate a comprehensive explanation of a function using Groq LLM.
    
    Args:
        function_code: The source code of the function to explain
        model: Model to use (default: llama-3.3-70b-versatile)
        
    Returns:
        Dictionary with keys:
        - purpose: What the function does
        - inputs: Parameter descriptions
        - output: Return value description
        - logic: Step-by-step logic explanation
        - example: Example usage (if applicable)
        - full_text: Complete formatted explanation
        
    Raises:
        ValueError: If function_code is empty or API key is missing
        RuntimeError: If LLM call fails
    """
    if not function_code or not function_code.strip():
        raise ValueError("Function code cannot be empty")
    
    if ChatGroq is None or HumanMessage is None:
        raise RuntimeError(
            "LangChain and Groq dependencies not installed. "
            "Install with: pip install langchain-groq groq"
        )
    
    # Get API key from .env-loaded environment
    api_key = os.environ.get('GROQ_API_KEY')
    
    if not api_key:
        raise ValueError(
            "Groq API key not found in GROQ_API_KEY. Ensure it is set in your .env file."
        )
    
    # Create the prompt
    language_key = (language or "python").strip().lower()
    language_name = "Java" if language_key == "java" else "Python"

    prompt = f"""
You are an expert {language_name} code reviewer and educator. Analyze the following function or method and provide a detailed, clear explanation.

FUNCTION CODE:
```{language_key}
{function_code}
```

Provide your explanation in the following format:

**Purpose:**
[Brief description of what this function does in 1-2 sentences]

**Inputs (Parameters):**
[Describe each parameter, its type, and purpose]

**Output (Return Value):**
[Describe what the function returns]

**Step-by-Step Logic:**
[Break down the logic flow in numbered steps]

**Example:**
[Provide a practical usage example with expected output]

**Key Insights:**
[Any important notes about performance, edge cases, or best practices]

Be concise but thorough. Use clear language suitable for developers.
"""

    candidate_models = []
    if model:
        candidate_models.append(model.strip())
    for candidate in DEFAULT_GROQ_MODELS:
        if candidate and candidate not in candidate_models:
            candidate_models.append(candidate)

    last_error: Exception | None = None
    for candidate_model in candidate_models:
        try:
            llm = ChatGroq(
                temperature=0.3,
                model_name=candidate_model,
                api_key=api_key,
                timeout=30
            )
            response = llm.invoke([HumanMessage(content=prompt)])
            explanation_text = response.content
            break
        except Exception as e:
            last_error = e
            error_text = str(e).lower()
            if "decommission" in error_text or "not supported" in error_text:
                continue
    else:
        raise RuntimeError(f"LLM call failed: {str(last_error)}")
    
    # Parse the response into structured sections
    explanation_dict = _parse_explanation(explanation_text)
    explanation_dict['full_text'] = explanation_text
    
    return explanation_dict


def _parse_explanation(explanation_text: str) -> Dict[str, str]:
    """
    Parse LLM explanation text into structured sections.
    
    Args:
        explanation_text: Raw explanation from LLM
        
    Returns:
        Dictionary with sections: purpose, inputs, output, logic, example, key_insights
    """
    sections = {
        'purpose': '',
        'inputs': '',
        'output': '',
        'logic': '',
        'example': '',
        'key_insights': ''
    }
    
    # Simple parsing based on section headers
    current_section = None
    lines = explanation_text.split('\n')
    
    for line in lines:
        lower_line = line.lower()
        
        if '**purpose:**' in lower_line or 'purpose:' in lower_line:
            current_section = 'purpose'
        elif '**inputs' in lower_line or 'inputs' in lower_line or 'parameters' in lower_line:
            current_section = 'inputs'
        elif '**output' in lower_line or 'output' in lower_line or 'returns' in lower_line:
            current_section = 'output'
        elif '**step' in lower_line or 'logic' in lower_line:
            current_section = 'logic'
        elif '**example' in lower_line or 'example:' in lower_line:
            current_section = 'example'
        elif '**key' in lower_line or 'insights' in lower_line:
            current_section = 'key_insights'
        elif current_section and line.strip():
            # Add content to current section, skipping the header line
            if not line.startswith('**'):
                sections[current_section] += line + '\n'
    
    # Clean up sections
    for key in sections:
        sections[key] = sections[key].strip()
    
    return sections


def extract_functions_from_file(file_path: str) -> list[Dict[str, Any]]:
    """
    Extract all functions and methods from a Python file.
    
    Args:
        file_path: Path to the Python file
        
    Returns:
        List of dictionaries with function info:
        - name: Function name
        - type: 'function' or 'method'
        - is_async: Boolean
        - class_name: Name of parent class (if method)
        - line: Line number
        
    Raises:
        FileNotFoundError: If file does not exist
        SyntaxError: If file has invalid syntax
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    try:
        source_code = _read_file_with_encoding(file_path)
        tree = ast.parse(source_code)
    except SyntaxError as e:
        return _fallback_extract_functions(source_code)

    functions: list[Dict[str, Any]] = []

    class FunctionCollector(ast.NodeVisitor):
        def __init__(self) -> None:
            self.class_stack: list[str] = []

        def visit_ClassDef(self, node: ast.ClassDef):
            self.class_stack.append(node.name)
            self.generic_visit(node)
            self.class_stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef):
            self._record_function(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
            self._record_function(node)

        def _record_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
            is_method = bool(self.class_stack)
            class_name = self.class_stack[-1] if is_method else None
            display_name = f"{class_name}.{node.name}" if class_name else node.name

            functions.append({
                'name': node.name,
                'type': 'method' if is_method else 'function',
                'is_async': isinstance(node, ast.AsyncFunctionDef),
                'class_name': class_name,
                'line': node.lineno,
                'display_name': display_name,
            })

            # Prevent nested functions from being treated as top-level items.
            self.generic_visit(node)

    FunctionCollector().visit(tree)

    return sorted(functions, key=lambda x: x['line'])

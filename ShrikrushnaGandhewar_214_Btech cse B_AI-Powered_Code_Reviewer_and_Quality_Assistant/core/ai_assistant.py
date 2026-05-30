"""AI Assistant chat helper for the Streamlit chatbot UI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:
    from langchain_core.messages import HumanMessage
    from langchain_groq import ChatGroq
except Exception:  # pragma: no cover - optional dependency
    ChatGroq = None
    HumanMessage = None

load_dotenv()

DEFAULT_GROQ_MODELS = (
    os.environ.get("GROQ_MODEL_NAME", "").strip(),
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
)


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


def build_code_context(file_paths: list[str], max_files: int = 3, max_chars_per_file: int = 3000) -> str:
    """Build a compact code context block from selected files."""
    if not file_paths:
        return ""

    context_parts: list[str] = []
    for file_path in file_paths[:max_files]:
        path_obj = Path(file_path)
        if not path_obj.exists() or path_obj.suffix.lower() not in (".py", ".java"):
            continue

        try:
            file_text = _read_file_with_encoding(str(path_obj))
        except Exception:
            continue

        if len(file_text) > max_chars_per_file:
            file_text = file_text[:max_chars_per_file].rstrip() + "\n# ... truncated ..."

        lang = "python" if path_obj.suffix.lower() == ".py" else "java"
        context_parts.append(f"### {path_obj.name}\n```{lang}\n{file_text}\n```")

    return "\n\n".join(context_parts)


def _detect_question_topics(user_message: str) -> dict[str, list[str]]:
    """Detect question topics and suggest relevant pages."""
    message_lower = user_message.lower()
    
    topic_pages = {
        "docstring": ["Docstring", "Validation"],
        "documentation": ["Docstring", "Validation"],
        "doc": ["Docstring", "Validation"],
        "validate": ["Validation"],
        "validation": ["Validation"],
        "optimize": ["AI Optimizer"],
        "optimization": ["AI Optimizer"],
        "performance": ["AI Optimizer"],
        "improve": ["AI Optimizer"],
        "explain": ["Explain Function"],
        "understand": ["Explain Function"],
        "function": ["Explain Function", "Function Details"],
        "code": ["Explain Function", "Function Details"],
        "analyze": ["Function Details", "Dashboard"],
        "analysis": ["Function Details", "Dashboard"],
        "report": ["Home"],
        "coverage": ["Home"],
        "metrics": ["Dashboard"],
        "overview": ["Dashboard"],
    }
    
    detected_pages = set()
    for keyword, pages in topic_pages.items():
        if keyword in message_lower:
            detected_pages.update(pages)
    
    return {
        "topics": list(detected_pages) if detected_pages else [],
    }


def get_ai_assistant_response(
    user_message: str,
    code_context: str = "",
    chat_history: list[dict[str, str]] | None = None,
    model: str = "llama-3.3-70b-versatile",
) -> str:
    """Generate a response for the chatbot UI using Groq."""
    if not user_message or not user_message.strip():
        raise ValueError("User message cannot be empty")

    if ChatGroq is None or HumanMessage is None:
        raise RuntimeError(
            "LangChain and Groq dependencies not installed. Install with: pip install langchain-groq groq"
        )

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("Groq API key not found in GROQ_API_KEY. Ensure it is set in your .env file.")

    candidate_models: list[str] = []
    if model:
        candidate_models.append(model.strip())
    for candidate in DEFAULT_GROQ_MODELS:
        if candidate and candidate not in candidate_models:
            candidate_models.append(candidate)

    history_lines: list[str] = []
    for item in (chat_history or [])[-8:]:
        role = str(item.get("role", "user")).strip().lower()
        content = str(item.get("content", "")).strip()
        if content:
            history_lines.append(f"{role.upper()}: {content}")

    # Detect relevant pages based on question topics
    detected = _detect_question_topics(user_message)
    suggested_pages = detected["topics"]
    
    prompt_sections = [
        "You are AI Assistant, a helpful Streamlit chatbot for a Code reviewer project supporting Python and Java.",
        "Focus on code explanations, debugging, optimization, docstrings, and clear developer guidance.",
        "When users ask where to find things:",
        "- You can see the coverage report on the 'Home' page.",
        "- You can generate docstrings on the 'Docstring' page.",
    ]
    if code_context.strip():
        prompt_sections.append("CODE CONTEXT:")
        prompt_sections.append(code_context.strip())
    if history_lines:
        prompt_sections.append("CHAT HISTORY:")
        prompt_sections.extend(history_lines)
    prompt_sections.append(f"USER QUESTION: {user_message.strip()}")
    prompt_sections.append(
        "Answer clearly and concisely. When helpful, include code snippets or bullet points."
    )
    
    # Add navigation suggestions if relevant pages detected
    if suggested_pages:
        pages_str = " or ".join(suggested_pages)
        prompt_sections.append(
            f"\nIf helpful based on the question topic, suggest the user visit the {pages_str} page for related features."
        )

    prompt = "\n\n".join(prompt_sections)
    last_error: Exception | None = None

    for candidate_model in candidate_models:
        try:
            llm = ChatGroq(
                temperature=0.3,
                model_name=candidate_model,
                api_key=api_key,
                timeout=30,
            )
            response = llm.invoke([HumanMessage(content=prompt)])
            return str(response.content).strip()
        except Exception as exc:
            last_error = exc
            error_text = str(exc).lower()
            if "decommission" in error_text or "not supported" in error_text:
                continue

    raise RuntimeError(f"LLM call failed: {str(last_error)}")

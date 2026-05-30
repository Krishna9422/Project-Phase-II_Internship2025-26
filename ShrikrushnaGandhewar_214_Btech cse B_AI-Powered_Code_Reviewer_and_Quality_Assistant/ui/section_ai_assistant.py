"""Streamlit UI section for the AI Assistant chatbot."""

from __future__ import annotations

import streamlit as st

from core.ai_assistant import build_code_context, get_ai_assistant_response


def _inject_ai_assistant_styles() -> None:
    """Apply a polished visual style to the AI Assistant page."""
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(16, 185, 129, 0.14), transparent 30%),
                radial-gradient(circle at top right, rgba(59, 130, 246, 0.14), transparent 28%),
                linear-gradient(180deg, #08111f 0%, #0f172a 52%, #111827 100%);
        }

        .main .block-container {
            padding-top: 1.6rem;
            padding-bottom: 1.8rem;
            max-width: 1160px;
        }

        .assistant-hero {
            padding: 1.25rem 1.4rem;
            margin-bottom: 1rem;
            border-radius: 22px;
            border: 1px solid rgba(148, 163, 184, 0.2);
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.84));
            box-shadow: 0 20px 55px rgba(0, 0, 0, 0.22);
        }

        .assistant-hero h2 {
            margin: 0;
            color: #f8fafc;
            font-size: 1.95rem;
            letter-spacing: -0.03em;
        }

        .assistant-hero p {
            margin: 0.55rem 0 0 0;
            color: #cbd5e1;
            font-size: 0.98rem;
        }

        div[data-testid="stChatMessage"] {
            border-radius: 18px;
        }

        div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p {
            line-height: 1.55;
        }

        section[data-testid="stExpander"] {
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 16px;
            overflow: hidden;
            background: rgba(15, 23, 42, 0.65);
        }

        div[data-baseweb="input"] > div {
            background: rgba(15, 23, 42, 0.9) !important;
            border: 1px solid rgba(59, 130, 246, 0.2) !important;
            border-radius: 14px !important;
        }

        button[kind="primary"],
        .stButton > button {
            border: 0;
            border-radius: 14px;
            font-weight: 700;
            background: linear-gradient(135deg, #2563eb 0%, #14b8a6 100%);
            color: #ffffff;
            box-shadow: 0 12px 26px rgba(37, 99, 235, 0.25);
            transition: transform 140ms ease, box-shadow 140ms ease, filter 140ms ease;
        }

        button[kind="primary"]:hover,
        .stButton > button:hover {
            transform: translateY(-1px);
            filter: brightness(1.04);
            box-shadow: 0 16px 30px rgba(37, 99, 235, 0.34);
        }

        .stAlert {
            border-radius: 14px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _ensure_ai_assistant_state() -> None:
    """Initialize chatbot session state."""
    if "ai_assistant_messages" not in st.session_state:
        st.session_state.ai_assistant_messages = [
            {
                "role": "assistant",
                "content": "Hi, I’m AI Assistant. Ask about the selected code, debugging, optimizations, or docstrings.",
            }
        ]
    if "ai_assistant_input_nonce" not in st.session_state:
        st.session_state.ai_assistant_input_nonce = 0
    if "ai_assistant_error" not in st.session_state:
        st.session_state.ai_assistant_error = ""


def _clear_chat() -> None:
    """Reset the conversation to the initial greeting."""
    st.session_state.ai_assistant_messages = [
        {
            "role": "assistant",
            "content": "Hi, I’m AI Assistant. Ask about the selected code, debugging, optimizations, or docstrings.",
        }
    ]
    st.session_state.ai_assistant_input_nonce += 1
    st.session_state.ai_assistant_error = ""


def run_ai_assistant_section(view: str, uploaded_file_paths: list[str]) -> None:
    """Render the chatbot page."""
    if view != "AI Assistant":
        return

    _ensure_ai_assistant_state()
    _inject_ai_assistant_styles()

    st.markdown(
        """
        <div class="assistant-hero">
            <h2>🤖 AI Assistant</h2>
            <p>Chat with a Groq-powered assistant about your selected Python or Java code, logic, bugs, and improvements.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if uploaded_file_paths:
        code_context = build_code_context(uploaded_file_paths)
        st.caption(f"Using code context from {len(uploaded_file_paths)} selected file(s).")
    else:
        code_context = ""
        st.info("Select or upload Python or Java files first to give the assistant code context.")

    if st.session_state.get("ai_assistant_error"):
        st.error(st.session_state.ai_assistant_error)

    for message in st.session_state.ai_assistant_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    chat_col, clear_col = st.columns([5, 1])
    with chat_col:
        with st.form("ai_assistant_form", clear_on_submit=False):
            input_key = f"ai_assistant_input_{st.session_state.ai_assistant_input_nonce}"
            user_message = st.text_input(
                "Ask about this code...",
                key=input_key,
                placeholder="Ask about this code...",
            )
            send_pressed = st.form_submit_button("Send", use_container_width=True)

    with clear_col:
        st.write("")
        st.write("")
        clear_pressed = st.button("Clear Chat", use_container_width=True)

    if clear_pressed:
        _clear_chat()
        st.rerun()

    if send_pressed:
        prompt = (user_message or "").strip()
        if not prompt:
            st.warning("Type a question before sending.")
        else:
            st.session_state.ai_assistant_messages.append({"role": "user", "content": prompt})
            try:
                response_text = get_ai_assistant_response(
                    prompt,
                    code_context=code_context,
                    chat_history=st.session_state.ai_assistant_messages,
                )
                st.session_state.ai_assistant_messages.append({"role": "assistant", "content": response_text})
                st.session_state.ai_assistant_error = ""
                st.session_state.ai_assistant_input_nonce += 1
            except Exception as exc:
                st.session_state.ai_assistant_error = f"LLM error: {exc}"
            st.rerun()

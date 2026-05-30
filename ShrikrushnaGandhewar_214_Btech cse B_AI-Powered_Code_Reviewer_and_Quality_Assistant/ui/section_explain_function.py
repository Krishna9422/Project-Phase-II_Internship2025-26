"""
Streamlit UI section for the "Explain this Function" feature.

Provides an interactive interface to:
- Select a Python file
- Choose a function from that file
- Display the function code
- Generate and display LLM-powered explanations
"""

import streamlit as st
from pathlib import Path

from core.function_explainer import (
    extract_functions_from_file,
    extract_java_functions_from_file,
    get_function_code,
    get_java_function_code,
    explain_function_llm
)


def _inject_explain_function_styles() -> None:
    """Apply a polished visual style to the explain-function page."""
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(59, 130, 246, 0.16), transparent 32%),
                radial-gradient(circle at top right, rgba(14, 165, 233, 0.12), transparent 28%),
                linear-gradient(180deg, #0b1020 0%, #0f172a 48%, #111827 100%);
        }

        .main .block-container {
            padding-top: 1.6rem;
            padding-bottom: 2rem;
            max-width: 1180px;
        }

        .explain-hero {
            padding: 1.25rem 1.4rem;
            margin: 0 0 1.25rem 0;
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 20px;
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.92), rgba(30, 41, 59, 0.82));
            box-shadow: 0 20px 55px rgba(0, 0, 0, 0.22);
        }

        .explain-hero h2 {
            margin: 0;
            font-size: 1.9rem;
            line-height: 1.15;
            letter-spacing: -0.03em;
            color: #f8fafc;
        }

        .explain-hero p {
            margin: 0.55rem 0 0 0;
            color: #cbd5e1;
            font-size: 0.98rem;
        }

        section[data-testid="stExpander"] {
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 18px;
            overflow: hidden;
            background: rgba(15, 23, 42, 0.7);
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.16);
        }

        section[data-testid="stExpander"] summary {
            background: linear-gradient(90deg, rgba(30, 41, 59, 0.96), rgba(15, 23, 42, 0.96));
            color: #e2e8f0;
            font-weight: 700;
            border-bottom: 1px solid rgba(148, 163, 184, 0.16);
        }

        div[data-baseweb="select"] > div {
            background: rgba(15, 23, 42, 0.92) !important;
            border: 1px solid rgba(59, 130, 246, 0.22) !important;
            border-radius: 14px !important;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
        }

        button[kind="primary"],
        .stButton > button {
            border: 0;
            border-radius: 14px;
            padding: 0.8rem 1rem;
            font-weight: 700;
            letter-spacing: 0.01em;
            background: linear-gradient(135deg, #2563eb 0%, #0ea5e9 100%);
            color: #ffffff;
            box-shadow: 0 12px 26px rgba(37, 99, 235, 0.28);
            transition: transform 140ms ease, box-shadow 140ms ease, filter 140ms ease;
        }

        button[kind="primary"]:hover,
        .stButton > button:hover {
            transform: translateY(-1px);
            filter: brightness(1.04);
            box-shadow: 0 16px 30px rgba(37, 99, 235, 0.35);
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0.35rem;
            background: rgba(15, 23, 42, 0.45);
            padding: 0.35rem;
            border-radius: 16px;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 12px;
            padding: 0.55rem 0.9rem;
            background: transparent;
            color: #cbd5e1;
            font-weight: 600;
        }

        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, rgba(37, 99, 235, 0.22), rgba(14, 165, 233, 0.22));
            color: #f8fafc;
        }

        div[data-testid="stCodeBlock"] {
            border-radius: 18px;
            overflow: hidden;
            border: 1px solid rgba(148, 163, 184, 0.18);
            box-shadow: 0 16px 36px rgba(0, 0, 0, 0.18);
        }

        .stAlert {
            border-radius: 14px;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


def run_explain_function_section(uploaded_file_paths: list[str]):
    """
    Main UI section for the "Explain this Function" feature.
    
    Args:
        uploaded_file_paths: List of selected Python file paths
    """
    _inject_explain_function_styles()

    selected_language = st.session_state.get("selected_language", "Python")
    target_ext = ".java" if selected_language == "Java" else ".py"
    language_label = "Java" if selected_language == "Java" else "Python"

    st.markdown(
        """
        <div class="explain-hero">
            <h2>🧠 Explain This Function</h2>
            <p>Select a Python file or Java file, inspect the function or method code, and generate a clear AI explanation of its purpose, inputs, outputs, logic, and examples.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Check if files are selected
    selected_paths = [path for path in uploaded_file_paths if path.lower().endswith(target_ext)]
    if not selected_paths:
        st.warning(f"📁 Please select one or more {language_label} files first (in the sidebar)")
        return
    
    # Step 1: Select file
    st.markdown(f"### 1️⃣ Select a {language_label} File")
    file_options = {Path(path).name: path for path in selected_paths}
    selected_file = st.selectbox(
        "Choose a file:",
        options=list(file_options.keys()),
        key="explain_file_select"
    )
    
    if not selected_file:
        return
    
    selected_file_path = file_options[selected_file]
    
    # Step 2: Extract and select function
    st.markdown("### 2️⃣ Select a Function")
    
    try:
        if selected_language == "Java":
            functions = extract_java_functions_from_file(selected_file_path)
        else:
            functions = extract_functions_from_file(selected_file_path)
        if not functions:
            st.info(f"No {language_label.lower()} methods/functions found in this file.")
            return
    except SyntaxError as e:
        st.error(f"❌ Syntax error in file: {str(e)}")
        return
    except Exception as e:
        st.error(f"❌ Error reading file: {str(e)}")
        return
    
    # Format function options with type info
    function_options = []
    for func in functions:
        display_name = func['display_name']
        type_label = "☕" if selected_language == "Java" else ("🔧" if func['type'] == 'method' else "ƒ")
        async_label = "⚡" if func['is_async'] else ""
        option_text = f"{type_label} {display_name} {async_label}".strip()
        function_options.append((option_text, func))
    
    selected_option = st.selectbox(
        "Choose a function:",
        options=function_options,
        format_func=lambda x: x[0],
        key="explain_function_select"
    )
    
    if not selected_option:
        return
    
    selected_function = selected_option[1]
    function_name = selected_function['name']
    class_name = selected_function.get('class_name')
    
    # Step 3: Display function code
    st.markdown("### 3️⃣ Function Code")
    
    try:
        if selected_language == "Java":
            function_code = get_java_function_code(selected_file_path, function_name, class_name=class_name)
        else:
            function_code = get_function_code(selected_file_path, function_name)
        if not function_code:
            st.error(f"❌ Could not extract code for function: {function_name}")
            return
    except Exception as e:
        st.error(f"❌ Error extracting function code: {str(e)}")
        return
    
    with st.expander("📄 View Function Code", expanded=True):
        st.code(function_code, language="java" if selected_language == "Java" else "python", line_numbers=True)
    
    # Step 4: Explain button
    st.markdown("### 4️⃣ Generate Explanation")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        explain_button = st.button(
            "🧠 Explain Function",
            use_container_width=True,
            key="explain_button"
        )
    
    # Generate explanation when button is clicked
    if explain_button:
        with st.spinner("🤔 Analyzing function and generating explanation..."):
            try:
                explanation = explain_function_llm(function_code, language=selected_language)
                
                # Store in session state to persist across reruns
                st.session_state.last_explanation = explanation
                st.session_state.last_function_name = function_name
                
            except ValueError as e:
                st.error(f"❌ Validation error: {str(e)}")
            except RuntimeError as e:
                st.error(f"❌ LLM error: {str(e)}")
            except Exception as e:
                st.error(f"❌ Unexpected error: {str(e)}")
    
    # Display explanation if available
    if hasattr(st.session_state, 'last_explanation'):
        explanation = st.session_state.last_explanation
        displayed_func = st.session_state.get('last_function_name', function_name)
        
        st.markdown("---")
        st.markdown("## 📋 Explanation")
        st.markdown(f"**{language_label} Function:** `{displayed_func}`")
        
        # Use tabs to organize explanation sections
        tabs = st.tabs([
            "📝 Full",
            "🎯 Purpose",
            "📥 Inputs",
            "📤 Output",
            "🔄 Logic",
            "💡 Example"
        ])
        
        with tabs[0]:  # Full text
            st.markdown(explanation.get('full_text', 'No explanation available'))
        
        with tabs[1]:  # Purpose
            purpose = explanation.get('purpose', 'Not available')
            if purpose:
                st.markdown(purpose)
            else:
                st.info("Purpose information not available in explanation")
        
        with tabs[2]:  # Inputs
            inputs_text = explanation.get('inputs', 'Not available')
            if inputs_text:
                st.markdown(inputs_text)
            else:
                st.info("Input information not available")
        
        with tabs[3]:  # Output
            output_text = explanation.get('output', 'Not available')
            if output_text:
                st.markdown(output_text)
            else:
                st.info("Output information not available")
        
        with tabs[4]:  # Logic
            logic_text = explanation.get('logic', 'Not available')
            if logic_text:
                st.markdown(logic_text)
            else:
                st.info("Logic information not available")
        
        with tabs[5]:  # Example
            example_text = explanation.get('example', 'Not available')
            if example_text:
                st.markdown(example_text)
            else:
                st.info("Example not available in explanation")
        
        # Key insights (bonus)
        if explanation.get('key_insights'):
            st.markdown("---")
            with st.expander("🔑 Key Insights", expanded=False):
                st.markdown(explanation['key_insights'])
        
        # Copy explanation button
        st.markdown("---")
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("📋 Copy Explanation", key="copy_explanation"):
                st.toast("✓ Copied to clipboard (in your browser)")


def show_explain_function_tab():
    """
    Simplified wrapper to integrate into existing tabs structure.
    Uses session state for file selection.
    """
    uploaded_file_paths = st.session_state.get("uploaded_file_paths", [])
    selected_language = st.session_state.get("selected_language", "Python")
    target_ext = ".java" if selected_language == "Java" else ".py"
    filtered_paths = [path for path in uploaded_file_paths if path.lower().endswith(target_ext)]
    run_explain_function_section(filtered_paths)

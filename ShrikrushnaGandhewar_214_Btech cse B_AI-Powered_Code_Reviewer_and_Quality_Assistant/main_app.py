"""Main_app.py module."""

import streamlit as st
import os
import re
import importlib

# Import enhanced UI modules
from ui import enhanced_ui, dashboard
from ui.dashboard_metrics import calculate_aggregate_metrics as _calculate_aggregate_metrics
from ui.section_docstring import run_docstring_section
from ui.section_ai_optimizer import run_ai_optimizer_section
from ui.section_java_assistant import run_java_assistant_section
from ui.section_java_validation import run_java_validation_section
from ui.section_home import run_home_section
from ui.section_reports import run_report_section
from ui.section_validation import run_validation_section
from ui.section_explain_function import show_explain_function_tab
from ui.section_ai_assistant import run_ai_assistant_section
from ui.section_analytics_dashboard import run_analytics_dashboard_section
from ui.ui import apply_global_ui_style as _apply_global_ui_style
from ui.ui import show_empty_state as _show_empty_state

from core import doc_steward
importlib.reload(doc_steward)

st.set_page_config(
    page_title="AI Code Reviewer - Advanced Analytics",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)


def apply_global_ui_style():
    """Compatibility wrapper for shared UI styling."""
    _apply_global_ui_style()

def show_empty_state():
    """Compatibility wrapper for shared empty-state component."""
    _show_empty_state()


def _go_to_ai_assistant() -> None:
    """Navigate to the AI Assistant page."""
    st.session_state.current_page = "AI Assistant"


def _go_to_java_assistant() -> None:
    """Navigate to the Java Assistant page."""
    st.session_state.current_page = "Java Assistant"


def _list_workspace_source_files(root_dir: str):
    """Return absolute paths for Python and Java source files in the workspace."""
    source_files = []
    ignored_dirs = {".git", "__pycache__", ".venv", "venv", "node_modules", "build", "dist", "out", "target"}

    for dir_path, dir_names, file_names in os.walk(root_dir):
        dir_names[:] = [d for d in dir_names if d not in ignored_dirs and not d.startswith(".")]
        for file_name in file_names:
            if file_name.endswith((".py", ".java")):
                source_files.append(os.path.abspath(os.path.join(dir_path, file_name)))

    return sorted(source_files, key=lambda p: p.lower())

# Initialize session state for tracking uploaded files
if "uploaded_file_paths" not in st.session_state:
    st.session_state.uploaded_file_paths = []
if "fixes_applied" not in st.session_state:
    st.session_state.fixes_applied = False

def calculate_aggregate_metrics(file_list):
    """Compatibility wrapper for shared aggregate metrics helper."""
    return _calculate_aggregate_metrics(file_list)


def _collect_callable_nodes(analysis: dict) -> list:
    """Return flat list of functions and methods from analyze_file output."""
    callables = list(analysis.get("functions", []))
    for cls in analysis.get("classes", []):
        callables.extend(cls.get("methods", []))
    return callables


def _get_docstring_issue(func_info: dict, style: str) -> str | None:
    """Return issue code for a callable docstring: missing/style/None."""
    doc = func_info.get("docstring")
    if not doc or not str(doc).strip():
        return "missing"

    normalized = str(doc)
    style_key = (style or "google").strip().lower()

    needs_args = bool(func_info.get("args"))
    needs_yields = bool(func_info.get("has_yield"))
    needs_returns = bool(func_info.get("has_return")) and not needs_yields
    needs_raises = bool(func_info.get("has_raises"))

    # Summary-only docstrings can be style-agnostic when no section is needed.
    if not any([needs_args, needs_yields, needs_returns, needs_raises]):
        return None

    def has_google_section(name: str) -> bool:
        return re.search(rf"(?m)^\s*{re.escape(name)}:\s*$", normalized) is not None

    def has_numpy_section(name: str) -> bool:
        return re.search(rf"(?ms)^\s*{re.escape(name)}\s*$\n\s*-{{3,}}\s*$", normalized) is not None

    if style_key == "google":
        if needs_args and not has_google_section("Args"):
            return "style"
        if needs_yields and not has_google_section("Yields"):
            return "style"
        if needs_returns and not has_google_section("Returns"):
            return "style"
        if needs_raises and not has_google_section("Raises"):
            return "style"
        return None

    if style_key == "numpy":
        if needs_args and not has_numpy_section("Parameters"):
            return "style"
        if needs_yields and not has_numpy_section("Yields"):
            return "style"
        if needs_returns and not has_numpy_section("Returns"):
            return "style"
        if needs_raises and not has_numpy_section("Raises"):
            return "style"
        return None

    # reST checks
    if needs_args and re.search(r"(?m):param\s+\w+\s*:", normalized) is None:
        return "style"
    if needs_yields and re.search(r"(?m):yields?\s*:", normalized) is None:
        return "style"
    if needs_returns and re.search(r"(?m):returns?\s*:", normalized) is None:
        return "style"
    if needs_raises and re.search(r"(?m):raises\s+", normalized) is None:
        return "style"
    return None

def main():
    """Main function for AI Code Reviewer."""
    # Apply enhanced UI theme
    enhanced_ui.apply_enhanced_theme()

    if "current_page" not in st.session_state:
        st.session_state.current_page = "Home"
    elif st.session_state.current_page == "Coverage Report":
        # Migrate removed standalone page to Home.
        st.session_state.current_page = "Home"
    elif st.session_state.current_page == "Docstring Coverage":
        # Migrate removed standalone page to Validation.
        st.session_state.current_page = "Validation"
    elif st.session_state.current_page == "Analytics":
        # Migrate renamed page key.
        st.session_state.current_page = "Dashboard"
    elif st.session_state.current_page == "📊 Analytics":
        # Migrate old decorated label to renamed page key.
        st.session_state.current_page = "Dashboard"
    elif st.session_state.current_page == "Source Code":
        # Migrate removed page key to Function Details.
        st.session_state.current_page = "Function Details"

    st.sidebar.title("🧠 AI Code Reviewer")
    st.sidebar.caption("Smart code analysis with advanced analytics")

    # Language selector (Python / Java)
    if "selected_language" not in st.session_state:
        st.session_state.selected_language = "Python"

    st.session_state.selected_language = st.sidebar.selectbox(
        "Language",
        ["Python", "Java"],
        index=0 if st.session_state.selected_language == "Python" else 1,
        key="selected_language_control",
        format_func=lambda v: ("🐍 Python" if v == "Python" else "☕ Java"),
    )

    page_icons = {
        "Home": "🏠",
        "Analytics Dashboard": "📈",
        "Dashboard": "📊",
        "AI Optimizer": "⚡",
        "Java Assistant": "☕",
        "Java Validation": "🧪",
        "AI Assistant": "🤖",
        "Docstring": "📝",
        "Explain Function": "🧠",
        "Function Details": "🔍",
        "JSON Output": "🧾",
        "Validation": "✅",
    }

    # Page list varies by selected language to keep UI focused
    if st.session_state.selected_language == "Python":
        other_pages = [
            "Analytics Dashboard",
            "Dashboard",
            "AI Optimizer",
            "AI Assistant",
            "Docstring",
            "Explain Function",
            "Function Details",
            "JSON Output",
            "Validation",
        ]
        pages = ["Home"] + sorted(other_pages, key=lambda page_name: page_name.lower())
    else:
        # Java-focused view: show Java Validation prominently
        other_pages = [
            "Analytics Dashboard",
            "Java Assistant",
            "Java Validation",
            "Dashboard",
            "AI Assistant",
            "Validation",
            "JSON Output",
            "Function Details",
            "Docstring",
            "Explain Function",
            "AI Optimizer",
        ]
        pages = ["Home"] + sorted(other_pages, key=lambda page_name: page_name.lower())
    if st.session_state.current_page not in pages:
        st.session_state.current_page = "Home"

    view = st.sidebar.selectbox(
        "Page",
        pages,
        format_func=lambda value: f"{page_icons.get(value, '📌')} {value}",
        key="current_page"
    )

    is_java = st.session_state.get("selected_language", "Python") == "Java"
    
    if "docstring_style" not in st.session_state:
        st.session_state.docstring_style = "javadoc" if is_java else "google"
    elif is_java and st.session_state.docstring_style not in ["javadoc"]:
        st.session_state.docstring_style = "javadoc"
    elif not is_java and st.session_state.docstring_style not in ["google", "numpy", "rest"]:
        st.session_state.docstring_style = "google"
    
    output_json = st.sidebar.text_input("Output JSON path", value="storage/review_logs.json")
    if view == "Docstring":
        docstring_style = st.session_state.docstring_style
        st.sidebar.caption("Docstring style can be changed on the Docstring page.")
    else:
        docstring_style = st.sidebar.selectbox(
            "Docstring Style" if not is_java else "Javadoc Style",
            ["google", "numpy", "rest"] if not is_java else ["javadoc"],
            format_func=lambda value: value.upper(),
            key="docstring_style"
        )

    if view == "Home":
        st.markdown("<h1 style='text-align: center; margin-bottom: 2rem;'>🚀 Home</h1>", unsafe_allow_html=True)
        st.markdown("<div class='ui-section-title'>📂 1. Select Files or Folder</div>", unsafe_allow_html=True)
        
        # Bigger styled container for file selection on Home
        file_container = st.container()
        
        st.markdown("<div class='ui-section-title'>🛠️ 2. Choose an Analysis Tool</div>", unsafe_allow_html=True)
        btn_container = st.container()
    else:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📂 File Selection")
        file_container = st.sidebar
        btn_container = None

    file_selection_method = "Workspace Files (real paths)"

    uploaded_file_paths = []
    use_uploaded_files = False
    
    uploaded_files = file_container.file_uploader(
        "Drag and drop Python or Java files OR entire folders here",
        type=["py", "java"],
        accept_multiple_files=True,
        key="uploaded_files_widget",
    )

    if uploaded_files:
        workspace_root = os.path.abspath(os.getcwd())
        workspace_files = _list_workspace_source_files(workspace_root)

        rel_lookup = {}
        base_lookup = {}
        for abs_path in workspace_files:
            rel_path = os.path.relpath(abs_path, workspace_root).replace("\\", "/").lower()
            rel_lookup[rel_path] = abs_path

            base_name = os.path.basename(abs_path).lower()
            base_lookup.setdefault(base_name, []).append(abs_path)

        unresolved_names = []
        ambiguous_names = []

        for uploaded_file in uploaded_files:
            raw_name = (uploaded_file.name or "").strip()
            if not raw_name:
                continue

            normalized_name = raw_name.replace("\\", "/").lstrip("./").lower()
            resolved_path = rel_lookup.get(normalized_name)

            if resolved_path is None:
                base_name = os.path.basename(normalized_name)
                matches = base_lookup.get(base_name, [])
                if len(matches) == 1:
                    resolved_path = matches[0]
                elif len(matches) > 1:
                    root_matches = [m for m in matches if os.path.dirname(m).lower() == workspace_root.lower()]
                    if len(root_matches) == 1:
                        resolved_path = root_matches[0]
                    else:
                        ambiguous_names.append(raw_name)
                        resolved_path = None

            if resolved_path and os.path.exists(resolved_path):
                uploaded_file_paths.append(os.path.abspath(resolved_path))
            else:
                unresolved_names.append(raw_name)

        uploaded_file_paths = list(dict.fromkeys(uploaded_file_paths))
        st.session_state.uploaded_file_paths = uploaded_file_paths

        if uploaded_file_paths:
            file_container.info(f"📂 {len(uploaded_file_paths)} workspace file(s) selected (no temp copy)")
        if unresolved_names:
            file_container.warning(
                "Could not map these uploaded names to files in current workspace: "
                + ", ".join(unresolved_names)
            )
        if ambiguous_names:
            file_container.warning(
                "Multiple files share these names in workspace. Select by unique path: "
                + ", ".join(ambiguous_names)
            )
    else:
        # Keep existing selection when no new upload is made, so navigation
        # between pages does not force users to select files again.
        uploaded_file_paths = list(st.session_state.get("uploaded_file_paths", []))

    if uploaded_file_paths:
        file_container.caption(f"Current selection: {len(uploaded_file_paths)} file(s)")
        if file_container.button("Clear selected files", key="clear_selected_files", use_container_width=True):
            uploaded_file_paths = []
            st.session_state.uploaded_file_paths = []
            st.rerun()

    python_file_list = [path for path in uploaded_file_paths if path.lower().endswith(".py")]
    java_file_list = [path for path in uploaded_file_paths if path.lower().endswith(".java")]

    # Get file to scan
    # Active file list depends on selected language
    if st.session_state.selected_language == "Python":
        active_file_list = python_file_list
        display_name = f"{len(python_file_list)} Python file(s)" if python_file_list else None
    else:
        active_file_list = java_file_list
        display_name = f"{len(java_file_list)} Java file(s)" if java_file_list else None

    # Backwards-compatible alias used throughout the app
    file_list = active_file_list

    # Add floating chatbot button using Streamlit button
    st.markdown(
        """
        <style>
        /* Hide the anchor's container so it doesn't take up space */
        div[data-testid="element-container"]:has(#floating-chat-anchor),
        div[data-testid="stElementContainer"]:has(#floating-chat-anchor),
        div[data-testid="stMarkdown"]:has(#floating-chat-anchor) {
            display: none !important;
        }

        /* Target the button's wrapper using general sibling selector (~) 
           Because we wrap them in a container, this won't affect the rest of the app */
        div[data-testid="element-container"]:has(#floating-chat-anchor) ~ div[data-testid="element-container"],
        div[data-testid="stElementContainer"]:has(#floating-chat-anchor) ~ div[data-testid="stElementContainer"],
        div[data-testid="stMarkdown"]:has(#floating-chat-anchor) ~ div[data-testid="stButton"] {
            position: fixed !important;
            right: 40px !important;
            bottom: 40px !important;
            z-index: 99999 !important;
        }

        /* Target the button itself */
        div[data-testid="element-container"]:has(#floating-chat-anchor) ~ div[data-testid="element-container"] button,
        div[data-testid="stElementContainer"]:has(#floating-chat-anchor) ~ div[data-testid="stElementContainer"] button,
        div[data-testid="stMarkdown"]:has(#floating-chat-anchor) ~ div[data-testid="stButton"] button {
            width: 70px !important;
            height: 70px !important;
            min-width: 70px !important;
            min-height: 70px !important;
            max-width: 70px !important;
            max-height: 70px !important;
            padding: 0 !important;
            border-radius: 50% !important; /* Circular for professional look */
            border: none !important; /* Remove Streamlit border */
            background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%) !important;
            color: #ffffff !important;
            font-size: 32px !important;
            font-weight: 700 !important;
            box-shadow: 
                0 10px 25px rgba(0, 0, 0, 0.3),
                0 0 20px rgba(168, 85, 247, 0.5) !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
            cursor: pointer !important;
            position: relative !important;
            z-index: 10000 !important;
        }

        /* Ensure icon is centered perfectly */
        div[data-testid="element-container"]:has(#floating-chat-anchor) ~ div[data-testid="element-container"] button p,
        div[data-testid="stElementContainer"]:has(#floating-chat-anchor) ~ div[data-testid="stElementContainer"] button p,
        div[data-testid="stMarkdown"]:has(#floating-chat-anchor) ~ div[data-testid="stButton"] button p {
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }

        /* Hover effects */
        div[data-testid="element-container"]:has(#floating-chat-anchor) ~ div[data-testid="element-container"] button:hover,
        div[data-testid="stElementContainer"]:has(#floating-chat-anchor) ~ div[data-testid="stElementContainer"] button:hover,
        div[data-testid="stMarkdown"]:has(#floating-chat-anchor) ~ div[data-testid="stButton"] button:hover {
            transform: translateY(-8px) scale(1.1) !important;
            box-shadow: 
                0 20px 35px rgba(0, 0, 0, 0.4),
                0 0 30px rgba(236, 72, 153, 0.6) !important;
            background: linear-gradient(135deg, #4f46e5 0%, #9333ea 50%, #db2777 100%) !important;
            border: none !important;
            color: #ffffff !important;
        }

        /* Prevent active/focus from reverting styles */
        div[data-testid="element-container"]:has(#floating-chat-anchor) ~ div[data-testid="element-container"] button:active,
        div[data-testid="stElementContainer"]:has(#floating-chat-anchor) ~ div[data-testid="stElementContainer"] button:active,
        div[data-testid="stMarkdown"]:has(#floating-chat-anchor) ~ div[data-testid="stButton"] button:active,
        div[data-testid="element-container"]:has(#floating-chat-anchor) ~ div[data-testid="element-container"] button:focus,
        div[data-testid="stElementContainer"]:has(#floating-chat-anchor) ~ div[data-testid="stElementContainer"] button:focus,
        div[data-testid="stMarkdown"]:has(#floating-chat-anchor) ~ div[data-testid="stButton"] button:focus {
            outline: none !important;
            border: none !important;
            color: #ffffff !important;
            background: linear-gradient(135deg, #4f46e5 0%, #9333ea 50%, #db2777 100%) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Create the floating button using Streamlit's button isolated in a container
    float_container = st.container()
    with float_container:
        st.markdown('<span id="floating-chat-anchor"></span>', unsafe_allow_html=True)
        st.button(
            "💬",
            key="floating_chat_button",
            help="Open AI Assistant Chat",
            on_click=_go_to_ai_assistant,
        )

    if view == "Analytics Dashboard":
        st.markdown("<h1 style='text-align: center; margin-bottom: 2rem;'>📈 Analytics Dashboard</h1>", unsafe_allow_html=True)
        run_analytics_dashboard_section(view, file_list, docstring_style)
        return

    if view == "Dashboard":
        dashboard.show_analytics_dashboard()
        return

    if view == "Explain Function":
        st.markdown("<h1 style='text-align: center; margin-bottom: 2rem;'>🧠 Explain Function</h1>", unsafe_allow_html=True)
        show_explain_function_tab()
        return

    if view == "AI Assistant":
        st.markdown("<h1 style='text-align: center; margin-bottom: 2rem;'>🤖 AI Assistant</h1>", unsafe_allow_html=True)
        run_ai_assistant_section(view, file_list)
        return

    if view == "Java Assistant":
        st.markdown("<h1 style='text-align: center; margin-bottom: 2rem;'>☕ Java Assistant</h1>", unsafe_allow_html=True)
        run_java_assistant_section(view, show_empty_state, java_file_list)
        return

    if view == "Java Validation":
        st.markdown("<h1 style='text-align: center; margin-bottom: 2rem;'>🧪 Java Validation</h1>", unsafe_allow_html=True)
        run_java_validation_section(view, show_empty_state, java_file_list)
        return

    files_to_display = file_list
    show_all_files = True

    run_home_section(view, btn_container, file_list, docstring_style, show_empty_state)
    if view == "Home":
        return

    if len(file_list) > 1:
        file_options = {"All selected files": None}
        for i, file_path in enumerate(file_list, start=1):
            file_options[f"{i}. {os.path.basename(file_path)}"] = file_path

        selected_scope = st.selectbox(
            "Select file report at top",
            options=list(file_options.keys()),
            index=1,
            key="selected_file_scope"
        )

        if file_options[selected_scope] is None:
            files_to_display = file_list
            show_all_files = True
        else:
            files_to_display = [file_options[selected_scope]]
            show_all_files = False

    st.markdown(f"### {'✅ Validation' if view == 'Validation' else '📊 ' + view}")
    summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
    summary_col1.metric("Selected Files", len(file_list))
    summary_col2.metric("View Scope", "All" if show_all_files else "Single")
    summary_col3.metric("Docstring Style", docstring_style.upper())
    summary_col4.metric("Selection Mode", file_selection_method)
    if display_name:
        st.caption(f"Working on: {display_name}")

    # Render language-appropriate pages
    if st.session_state.selected_language == "Python":
        run_validation_section(
            view,
            active_file_list,
            files_to_display,
            show_all_files,
            docstring_style,
            output_json,
            use_uploaded_files,
            show_empty_state,
        )
        run_docstring_section(
            view,
            active_file_list,
            docstring_style,
            show_empty_state,
            _collect_callable_nodes,
            _get_docstring_issue,
        )
        run_ai_optimizer_section(
            view,
            active_file_list,
            files_to_display,
            show_all_files,
            output_json,
            show_empty_state,
        )
    else:
        run_validation_section(
            view,
            active_file_list,
            files_to_display,
            show_all_files,
            docstring_style,
            output_json,
            use_uploaded_files,
            show_empty_state,
        )
        run_docstring_section(
            view,
            active_file_list,
            docstring_style,
            show_empty_state,
            _collect_callable_nodes,
            _get_docstring_issue,
        )
        run_ai_optimizer_section(
            view,
            active_file_list,
            files_to_display,
            show_all_files,
            output_json,
            show_empty_state,
        )
    run_report_section(
        view,
        active_file_list,
        files_to_display,
        show_all_files,
        output_json,
        show_empty_state,
    )

if __name__ == "__main__":
    main()

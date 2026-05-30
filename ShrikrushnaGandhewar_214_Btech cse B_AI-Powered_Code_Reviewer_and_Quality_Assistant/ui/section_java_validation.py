"""Java validation/report section renderer."""

from __future__ import annotations

import os

import streamlit as st

from core.auto_fixer import fix_syntax_error
import core.java_support as js
from core.java_support import (
    apply_javadocs_to_file,
    get_java_file_report,
    get_java_workspace_report,
    list_java_files,
)


def _entity_key(file_path: str, name: str, line: int) -> str:
    """Return a stable key for a Java entity on the validation page."""
    return f"{file_path}|{name}|{line}"


def run_java_validation_section(view, show_empty_state, java_file_candidates=None) -> None:
    """Render the Java validation/report page."""
    if view != "Java Validation":
        return

    st.markdown(
        """
        <style>
        .java-validation-hero {
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.28) 0%, rgba(14, 165, 233, 0.14) 58%, rgba(15, 23, 42, 0.82) 100%);
            border: 1px solid rgba(59, 130, 246, 0.24);
            border-radius: 22px;
            padding: 1.15rem 1.3rem;
            margin: 0.4rem 0 1rem 0;
            box-shadow: 0 18px 48px rgba(0, 0, 0, 0.26);
        }
        .java-validation-title {
            font-size: 2rem;
            font-weight: 800;
            color: #f8fafc;
            margin-bottom: 0.15rem;
            letter-spacing: -0.03em;
        }
        .java-validation-subtitle {
            color: #cbd5e1;
            font-size: 0.98rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="java-validation-hero">
            <div class="java-validation-title">✅ Java Validation</div>
            <div class="java-validation-subtitle">Review JavaDocs, inspect optimization findings, and apply safe bulk fixes from one place.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    workspace_root = os.path.abspath(os.getcwd())
    java_files = list(java_file_candidates or []) or list_java_files(workspace_root)
    if not java_files:
        st.warning("No Java files were found in the workspace. Add a .java file to begin.")
        show_empty_state()
        return

    report = get_java_workspace_report(java_files)
    suppressed_entities = st.session_state.setdefault("java_validation_suppressed_entities", set())
    metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
    metric_col1.metric("Files", report.get("file_count", 0))
    metric_col2.metric("Classes", report.get("total_classes", 0))
    metric_col3.metric("Methods", report.get("total_methods", 0))
    metric_col4.metric("Missing Javadocs", report.get("total_missing_javadocs", 0))
    metric_col5.metric("Syntax Errors", report.get("total_syntax_errors", 0))

    st.caption(f"Optimization findings across workspace: {report.get('total_optimization_findings', 0)}")

    if st.button("✨ Fix All Missing JavaDocs", use_container_width=True, key="java_fix_all_javadocs"):
        fixed_files = 0
        for file_path in java_files:
            file_report = get_java_file_report(file_path)
            if file_report.get("missing_javadocs_count", 0) > 0:
                pending_entities = file_report.get("missing_javadocs", [])
                analysis = file_report.get("analysis", {})
                java_entities = list(analysis.get("classes", []))
                java_entities.extend(js._flatten_java_methods(analysis))
                inserted = apply_javadocs_to_file(
                    file_path,
                    java_entities,
                )
                if inserted > 0:
                    for entity in pending_entities:
                        entity_name = str(entity.get("name", ""))
                        entity_line = int(entity.get("line", 0) or 0)
                        suppressed_entities.add(_entity_key(file_path, entity_name, entity_line))
                    fixed_files += 1
        st.success(f"Applied JavaDocs in {fixed_files} file(s).")
        st.rerun()

    for file_report in report.get("file_reports", []):
        file_name = file_report.get("file_name")
        file_key = str(file_report.get("file_path", file_name)).replace("\\", "_").replace("/", "_")
        visible_missing = []
        for entity in file_report.get("missing_javadocs", []):
            entity_name = str(entity.get("name", ""))
            entity_line = int(entity.get("line", 0) or 0)
            if _entity_key(file_report.get("file_path", ""), entity_name, entity_line) in suppressed_entities:
                continue
            visible_missing.append(entity)

        syntax_errors = file_report.get("syntax_errors", [])

        with st.expander(
            f"📄 {file_name} — {len(visible_missing)} missing JavaDocs, {len(syntax_errors)} syntax errors",
            expanded=False,
        ):
            st.markdown(
                f"- Classes: {file_report.get('classes', 0)}\n"
                f"- Methods: {file_report.get('methods', 0)}\n"
                f"- Missing JavaDocs: {file_report.get('missing_javadocs_count', 0)}\n"
                f"- Syntax errors: {file_report.get('syntax_error_count', 0)}\n"
                f"- Optimization findings: {file_report.get('optimization_count', 0)}"
            )

            if syntax_errors:
                st.error("Compiler detected syntax errors in this file.")
                st.dataframe(syntax_errors, use_container_width=True)
                if st.button("🩹 Fix Syntax Error in file", key=f"java_fix_syntax_{file_key}", use_container_width=True):
                    fixed = fix_syntax_error(file_report.get("file_path"), "Java")
                    if fixed:
                        st.success(f"Applied syntax fix to {file_name}. Re-validating now.")
                        st.rerun()
                    st.warning("Could not auto-fix syntax errors for this file. Try fixing manually and re-run validation.")

            if visible_missing:
                st.dataframe(visible_missing, use_container_width=True)
                if st.button("🛠️ Fix JavaDocs in file", key=f"java_fix_file_{file_key}", use_container_width=True):
                    analysis = file_report.get("analysis", {})
                    java_entities = list(analysis.get("classes", []))
                    java_entities.extend(js._flatten_java_methods(analysis))
                    inserted = apply_javadocs_to_file(
                        file_report.get("file_path"),
                        java_entities,
                    )
                    if inserted > 0:
                        for entity in visible_missing:
                            entity_name = str(entity.get("name", ""))
                            entity_line = int(entity.get("line", 0) or 0)
                            suppressed_entities.add(_entity_key(file_report.get("file_path", ""), entity_name, entity_line))
                        st.success(f"Applied JavaDocs to {file_name}.")
                        st.rerun()
                    st.info("No new JavaDocs were applied because the file already had comments above those items.")

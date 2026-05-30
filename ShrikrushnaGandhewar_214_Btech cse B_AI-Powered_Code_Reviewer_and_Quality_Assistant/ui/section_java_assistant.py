"""Streamlit section for Java comment generation and lightweight updates."""

from __future__ import annotations

import os

import streamlit as st

from core.java_support import (
    _read_file_with_encoding,
    apply_javadoc_to_file,
    apply_javadocs_to_file,
    apply_java_optimization_to_file,
    analyze_java_optimizations,
    get_java_file_report,
    extract_java_entities,
    generate_java_optimization_summary_llm,
    generate_javadoc_comment_llm,
    generate_javadoc_comment,
    list_java_files,
    summarize_java_entities,
)


def _java_preview_code(entity: dict, source: str, use_ai: bool) -> str:
    signature = entity.get("signature") or entity.get("name") or "Java item"
    comment = generate_javadoc_comment_llm(entity, source) if use_ai else generate_javadoc_comment(entity)
    return f"{comment}\n{signature}"


def run_java_assistant_section(view, show_empty_state, java_file_candidates=None) -> None:
    """Render the Java Assistant page."""
    if view != "Java Assistant":
        return

    st.markdown(
        """
        <style>
        .java-hero {
            background: linear-gradient(135deg, rgba(20, 83, 45, 0.34) 0%, rgba(34, 197, 94, 0.16) 58%, rgba(15, 23, 42, 0.8) 100%);
            border: 1px solid rgba(34, 197, 94, 0.25);
            border-radius: 22px;
            padding: 1.15rem 1.3rem;
            margin: 0.4rem 0 1rem 0;
            box-shadow: 0 18px 48px rgba(0, 0, 0, 0.26);
        }
        .java-title {
            font-size: 2rem;
            font-weight: 800;
            color: #f8fafc;
            margin-bottom: 0.15rem;
            letter-spacing: -0.03em;
        }
        .java-subtitle {
            color: #cbd5e1;
            font-size: 0.98rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="java-hero">
            <div class="java-title">☕ Java Assistant</div>
            <div class="java-subtitle">Generate Javadoc comments, apply them to source files, and make lightweight code updates from a Python backend.</div>
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

    selected_file = st.selectbox(
        "Select Java file",
        java_files,
        format_func=lambda path: os.path.relpath(path, workspace_root).replace("\\", "/"),
        key="java_assistant_selected_file",
    )

    if not selected_file or not os.path.exists(selected_file):
        st.info("Select a Java source file to inspect classes and methods.")
        return

    source = _read_file_with_encoding(selected_file)
    analysis = extract_java_entities(source)
    summary = summarize_java_entities(analysis)
    st.caption(f"Classes: {summary['classes']} | Methods: {summary['methods']}")

    classes = analysis.get("classes", [])
    methods = analysis.get("methods", [])
    all_entities = []
    for class_item in classes:
        all_entities.append(class_item)
        all_entities.extend(class_item.get("methods", []))
    all_entities.extend(methods)

    if not all_entities:
        st.info("No class or method definitions were detected in this file.")
        return

    if "java_assistant_selected_entity" not in st.session_state and all_entities:
        st.session_state.java_assistant_selected_entity = all_entities[0]

    left_col, right_col = st.columns([1.1, 1.7])
    with left_col:
        st.markdown("### Detected Items")
        for entity in all_entities:
            label = f"{entity.get('kind', 'item').title()}: {entity.get('name')}"
            if st.button(label, key=f"java_entity_{entity['line']}", use_container_width=True):
                st.session_state.java_assistant_selected_entity = entity

        st.markdown("---")
        if st.button("✨ Auto-Javadoc All", use_container_width=True, key="java_auto_javadoc_all"):
            inserted = apply_javadocs_to_file(selected_file, all_entities)
            if inserted:
                st.success(f"Applied {inserted} Javadoc block(s) to {os.path.basename(selected_file)}.")
                st.rerun()
            st.info("No new Javadocs were applied because the file already had comments above those items.")

    with right_col:
        selected_entity = st.session_state.get("java_assistant_selected_entity") or all_entities[0]
        st.markdown(f"### Preview: {selected_entity.get('name')}")
        st.caption(selected_entity.get("signature", ""))
        preview_mode = st.radio(
            "Preview mode",
            options=["Template", "AI"],
            horizontal=True,
            key="java_preview_mode",
        )
        st.code(_java_preview_code(selected_entity, source, preview_mode == "AI"), language="java")

        if st.button("✅ Apply Javadoc", use_container_width=True, key=f"java_apply_single_{selected_entity['line']}"):
            applied = apply_javadoc_to_file(selected_file, selected_entity)
            if applied:
                st.success(f"Applied Javadoc above {selected_entity.get('name')}.")
                st.rerun()
            st.info("A Javadoc block already exists above that item, so no change was made.")

        st.markdown("### Notes")
        st.write(
            "This Java assistant uses conservative regex-based extraction so it can still work on partially broken files. "
            "It is intentionally separate from the Python pages to keep the existing workflow stable."
        )

    st.markdown("### Optimization Suggestions")
    st.markdown(generate_java_optimization_summary_llm(source, analysis))
    findings = analyze_java_optimizations(source, analysis)
    if not findings:
        st.info("No obvious optimization patterns were detected in this file.")
    else:
        st.caption(f"Detected {len(findings)} suggestion(s). These are conservative refactor ideas, not automatic edits.")
        for idx, finding in enumerate(findings):
            with st.expander(f"{idx + 1}. {finding.get('title')} — line {finding.get('line')}", expanded=False):
                st.write(finding.get("explanation", ""))
                st.code(finding.get("original_code") or "", language="java")
                st.code(finding.get("optimized_code") or "", language="java")
                if finding.get("auto_apply") and finding.get("original_code") and finding.get("optimized_code"):
                    if st.button("🛠️ Apply Safe Refactor", key=f"java_safe_refactor_{idx}", use_container_width=True):
                        if apply_java_optimization_to_file(selected_file, finding.get("original_code"), finding.get("optimized_code")):
                            st.success("Applied the safe Java refactor.")
                            st.rerun()
                        st.error("Could not apply the refactor because the target snippet was not found.")

    st.markdown("### File Report")
    file_report = get_java_file_report(selected_file)
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("Classes", file_report.get("classes", 0))
    metric_col2.metric("Methods", file_report.get("methods", 0))
    metric_col3.metric("Missing Javadocs", file_report.get("missing_javadocs_count", 0))
    metric_col4.metric("Optimization Findings", file_report.get("optimization_count", 0))

    if file_report.get("missing_javadocs"):
        with st.expander("Missing Javadocs", expanded=False):
            st.dataframe(file_report.get("missing_javadocs"), use_container_width=True)
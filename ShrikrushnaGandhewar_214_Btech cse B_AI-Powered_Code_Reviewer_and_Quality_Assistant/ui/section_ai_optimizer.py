"""AI optimizer section renderer."""

import os

import streamlit as st

from core.ai_optimizer import (
    _read_file_with_encoding,
    analyze_and_optimize_code,
    apply_multiple_optimizations,
    apply_optimized_code_to_file,
    apply_optimized_code_to_file_by_lines,
    apply_syntax_fix_to_file,
    generate_rewrite_for_finding,
    _normalize_indentation,
)


def _ensure_optimizer_state():
    """Initialize optimizer session state keys."""
    defaults = {
        "ai_optimizer_result": None,
        "ai_optimizer_selected_file": None,
        "ai_optimizer_copy_text": "",
        "ai_optimizer_show_more": False,
        "ai_optimizer_file_cache": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _render_code_panel(title: str, code_text: str, accent: str) -> None:
    """Render a dark code panel with a header badge."""
    st.markdown(
        f"""
        <div style="
            background: rgba(15, 23, 42, 0.9);
            border: 1px solid {accent};
            border-radius: 18px;
            padding: 1rem 1rem 0.85rem 1rem;
            box-shadow: 0 12px 34px rgba(0, 0, 0, 0.28);
            min-height: 100%;
        ">
            <div style="
                color: #f8fafc;
                font-size: 1.02rem;
                font-weight: 700;
                margin-bottom: 0.55rem;
                letter-spacing: 0.01em;
            ">{title}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.code(code_text or "# No code available", language="python")


def run_ai_optimizer_section(view, file_list, files_to_display, show_all_files, output_json, show_empty_state):
    """Render the AI Optimizer page."""
    if view != "AI Optimizer":
        return

    _ensure_optimizer_state()

    st.markdown(
        """
        <style>
        .ai-optimizer-hero {
            background: linear-gradient(135deg, rgba(76, 29, 149, 0.35) 0%, rgba(168, 85, 247, 0.18) 55%, rgba(15, 23, 42, 0.78) 100%);
            border: 1px solid rgba(168, 85, 247, 0.26);
            border-radius: 22px;
            padding: 1.2rem 1.3rem;
            margin: 0.4rem 0 1rem 0;
            box-shadow: 0 18px 48px rgba(0, 0, 0, 0.28);
        }
        .ai-optimizer-title {
            font-size: 2rem;
            font-weight: 800;
            color: #f8fafc;
            margin-bottom: 0.15rem;
            letter-spacing: -0.03em;
        }
        .ai-optimizer-subtitle {
            color: #cbd5e1;
            font-size: 0.98rem;
        }
        .optimizer-chip {
            display: inline-block;
            padding: 0.32rem 0.7rem;
            margin: 0.2rem 0.28rem 0.2rem 0;
            border-radius: 999px;
            background: rgba(168, 85, 247, 0.14);
            color: #e9d5ff;
            border: 1px solid rgba(168, 85, 247, 0.35);
            font-size: 0.82rem;
            font-weight: 700;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="ai-optimizer-hero">
            <div class="ai-optimizer-title">⚡ AI Optimizer</div>
            <div class="ai-optimizer-subtitle">Detect high-complexity Python or Java code, preview a cleaner rewrite, and apply the change back into the selected file.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )



    if not file_list:
        st.warning("⚠️ No supported files are available. Upload or select files first.")
        show_empty_state()
        return

    col_left, col_right = st.columns([3, 1])
    with col_left:
        selected_file = st.selectbox(
            "Select file to optimize:",
            files_to_display or file_list,
            key="ai_optimizer_selected_file",
        )
    with col_right:
        if st.button("🔍 Analyze", use_container_width=True, key="ai_optimizer_analyze_button"):
            st.session_state["ai_optimizer_trigger"] = True

    if not selected_file or not os.path.exists(selected_file):
        st.info("Choose a file to inspect its loops, conditions, and complexity hotspots.")
        return

    if st.session_state.get("ai_optimizer_trigger") or not st.session_state.get("ai_optimizer_result"):
        with st.spinner("Analyzing code for optimization opportunities..."):
            try:
                code_text = _read_file_with_encoding(selected_file)
                st.session_state["ai_optimizer_file_cache"][selected_file] = code_text
                result = analyze_and_optimize_code(code_text, file_path=selected_file)
                st.session_state["ai_optimizer_result"] = result
                st.session_state["ai_optimizer_trigger"] = False
            except Exception as exc:
                st.session_state["ai_optimizer_result"] = {
                    "file_path": selected_file,
                    "message": f"Optimization analysis failed: {exc}",
                    "findings": [],
                    "current_code": None,
                    "optimized_code": None,
                }
                st.session_state["ai_optimizer_trigger"] = False

    result = st.session_state.get("ai_optimizer_result") or {}
    # Normalize paths for comparison (case-insensitive on Windows, handle slashes)
    result_path = os.path.normpath(result.get("file_path")) if result.get("file_path") else None
    selected_path = os.path.normpath(selected_file) if selected_file else None
    if result_path and selected_path and result_path.lower() != selected_path.lower():
        st.session_state["ai_optimizer_trigger"] = True
        st.rerun()

    # Handle syntax errors with prominent auto-fix option
    if result.get("syntax_error"):
        if result.get("syntax_fixed"):
            st.markdown(
                """
                <div style="background-color: rgba(34, 197, 94, 0.15); border: 2px solid #10b981; border-radius: 12px; padding: 1rem; margin-bottom: 1rem;">
                    <div style="color: #10b981; font-weight: bold; font-size: 1.1rem; margin-bottom: 0.5rem;">✅ Syntax Auto-Fix Available</div>
                    <div style="color: #cbd5e1; font-size: 0.95rem;">A conservative automatic syntax normalization was applied. Click the button below to apply the fix to your file.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            fixed_source = result.get("fixed_source")
            file_path = result.get("file_path")
            if fixed_source and file_path:
                col_fix, col_space = st.columns([1, 3])
                with col_fix:
                    if st.button("🛠️ APPLY AUTO FIX", use_container_width=True, key="ai_optimizer_auto_fix_bug"):
                            if apply_syntax_fix_to_file(file_path, fixed_source):
                                refreshed_content = _read_file_with_encoding(file_path)
                                st.session_state["ai_optimizer_file_cache"][file_path] = refreshed_content
                                # Clear the improved preview so only current code is shown
                                st.session_state["ai_optimizer_result"] = {
                                    **(result or {}),
                                    "current_code": refreshed_content,
                                    "optimized_code": None,
                                    "ai_optimizer_applied": True,
                                    "ai_optimizer_apply_message": f"Applied syntax fix to {os.path.basename(file_path)}.",
                                }
                                st.success(f"✨ Applied the syntax fix to {os.path.basename(file_path)}. Re-run analysis to see improvements.")
                                st.session_state["ai_optimizer_trigger"] = True
                                st.rerun()
                            else:
                                st.error("Could not apply the automatic syntax fix.")
        else:
            if result.get("indentation_error"):
                st.error("❌ Indentation Error Detected")
                st.error("The file has indentation issues that prevent optimization. Please correct indentation and try again.")
            else:
                st.error("❌ Syntax Error Detected")
                st.error("The file has syntax errors that prevent optimization. Please fix the syntax error in your editor and try again.")
            # show compact context if available
            if isinstance(result.get("message"), str):
                st.code(result.get("message"), language=None)
    # Friendly handling for other messages when no optimized code
    elif result.get("message") and not result.get("optimized_code"):
        st.info(result["message"])
    findings = result.get("findings", [])
    if findings:
        chips = [finding.get("improvement_type", finding.get("pattern", "Optimization")) for finding in findings]
        st.markdown("".join(f"<span class='optimizer-chip'>{chip}</span>" for chip in chips), unsafe_allow_html=True)

    # If no optimized code exists for the primary preview, still show detected opportunities
    if not result.get("optimized_code"):
        if findings:
            st.markdown("### Detected Opportunities")
            for idx, finding in enumerate(findings):
                with st.expander(f"{finding.get('title', finding.get('pattern', 'Finding'))} — line {finding.get('line', '?')}", expanded=False):
                    st.write(finding.get("explanation", ""))
                    st.code(finding.get("original_code") or "", language="python")
                    if finding.get("optimized_code"):
                        st.code(finding.get("optimized_code"), language="python")
                        if finding.get("llm_provider"):
                            st.caption(f"Provider: {finding.get('llm_provider')}")
                        col_a, col_b = st.columns(2)
                        with col_a:
                            key_apply = f"ai_apply_{idx}"
                            if st.button("Apply Fix", key=key_apply, use_container_width=True):
                                try:
                                    file_path = result.get("file_path")
                                    applied = False
                                    if file_path:
                                        applied = apply_optimized_code_to_file_by_lines(
                                            file_path,
                                            int(finding.get("line") or 0),
                                            int(finding.get("end_line") or finding.get("line") or 0),
                                            finding.get("optimized_code"),
                                        )
                                    if not applied and file_path:
                                        applied = apply_optimized_code_to_file(
                                            file_path,
                                            finding.get("original_code"),
                                            finding.get("optimized_code"),
                                        )
                                    if not applied and file_path:
                                        applied = apply_optimized_code_to_file_by_lines(
                                            file_path,
                                            int(finding.get("line") or 0),
                                            int(finding.get("end_line") or finding.get("line") or 0),
                                            finding.get("optimized_code"),
                                        )
                                    if applied:
                                        refreshed_content = _read_file_with_encoding(file_path)
                                        st.session_state["ai_optimizer_file_cache"][file_path] = refreshed_content
                                        st.session_state["ai_optimizer_result"] = {
                                            **(result or {}),
                                            "current_code": refreshed_content,
                                            "optimized_code": None,
                                            "ai_optimizer_applied": True,
                                            "ai_optimizer_apply_message": f"Applied optimization to {os.path.basename(file_path)}.",
                                        }
                                        st.session_state["ai_optimizer_trigger"] = True
                                        st.rerun()
                                    else:
                                        st.error("Could not apply the fix — original snippet not found.")
                                except Exception as exc:
                                    st.error(f"Failed to apply fix: {exc}")
                        with col_b:
                            key_copy = f"ai_copy_{idx}"
                            if st.button("Copy Fix", key=key_copy, use_container_width=True):
                                st.session_state["ai_optimizer_copy_text"] = finding.get("optimized_code")
                                st.success("Fix copied to the output box below.")
                        # Allow regeneration of the rewrite
                        if st.button("Generate Rewrite", key=f"gen_{idx}", use_container_width=True):
                            with st.spinner("Requesting rewrite from LLM..."):
                                opt, provider = generate_rewrite_for_finding(finding)
                                if opt:
                                    opt_norm = _normalize_indentation(finding.get("original_code") or "", opt)
                                    updated = st.session_state.get("ai_optimizer_result") or result or {}
                                    if "findings" in updated and len(updated["findings"]) > idx:
                                        updated["findings"][idx]["optimized_code"] = opt_norm
                                        updated["findings"][idx]["llm_provider"] = provider
                                        st.session_state["ai_optimizer_result"] = updated
                                        st.success("Rewrite generated and preview updated.")
                                        st.rerun()
                                else:
                                    st.error("Failed to generate rewrite; check model keys and connectivity.")
                    else:
                        # No optimized code yet — allow the user to generate one on-demand
                        if st.button("Generate Rewrite", key=f"gen_{idx}", use_container_width=True):
                            with st.spinner("Requesting rewrite from LLM..."):
                                opt, provider = generate_rewrite_for_finding(finding)
                                if opt:
                                    opt_norm = _normalize_indentation(finding.get("original_code") or "", opt)
                                    updated = st.session_state.get("ai_optimizer_result") or result or {}
                                    if "findings" in updated and len(updated["findings"]) > idx:
                                        updated["findings"][idx]["optimized_code"] = opt_norm
                                        updated["findings"][idx]["llm_provider"] = provider
                                        st.session_state["ai_optimizer_result"] = updated
                                        st.success("Rewrite generated and preview updated.")
                                        st.rerun()
                                else:
                                    st.error("Failed to generate rewrite; check model keys and connectivity.")
        return

    if result.get("ai_optimizer_applied"):
        st.success(result.get("ai_optimizer_apply_message", "Optimization applied successfully."))

    if result.get("ai_optimizer_copy_text"):
        st.text_area("Copied Fix", value=result["ai_optimizer_copy_text"], height=180)

    current_code = result.get("current_code") or result.get("original_code") or "# Current code not available"
    optimized_code = result.get("optimized_code") or "# Optimized code not available"

    col1, col2 = st.columns(2)
    with col1:
        _render_code_panel("❌ Current Code", current_code, "rgba(239, 68, 68, 0.55)")
        if findings:
            st.warning(f"Detected pattern: {findings[0].get('pattern', 'optimization')}")
    with col2:
        _render_code_panel("✅ Improved Code", optimized_code, "rgba(34, 197, 94, 0.55)")

    st.markdown("---")

    st.markdown("### 📌 Improvement Summary")
    summary_col1, summary_col2, summary_col3 = st.columns(3)
    summary_col1.metric("Improvement Type", result.get("improvement_type") or "Unknown")
    summary_col2.metric("Before", result.get("complexity_before") or "-")
    summary_col3.metric("After", result.get("complexity_after") or "-")

    st.markdown("### 🧠 Explanation")
    st.write(result.get("explanation") or "No explanation available.")

    button_col1, button_col2, button_col3 = st.columns(3)
    with button_col1:
        if st.button("COPY FIX", use_container_width=True, key="ai_optimizer_copy_fix"):
            st.session_state["ai_optimizer_copy_text"] = optimized_code
            st.success("Fix is shown below. Select it and copy it into your editor if needed.")
            st.rerun()

    with button_col2:
        if st.button("APPLY FIX", use_container_width=True, key="ai_optimizer_apply_fix"):
            file_path = result.get("file_path")
            line_start = int(result.get("line") or 0)
            line_end = int(result.get("end_line") or line_start)
            if not file_path:
                st.error("Cannot apply fix: file path is missing.")
            else:
                try:
                    applied = False
                    if line_start > 0:
                        applied = apply_optimized_code_to_file_by_lines(file_path, line_start, line_end, optimized_code)
                    if not applied:
                        applied = apply_optimized_code_to_file(file_path, current_code, optimized_code)
                    if not applied and line_start > 0:
                        applied = apply_optimized_code_to_file_by_lines(file_path, line_start, line_end, optimized_code)
                    if applied:
                        refreshed_content = _read_file_with_encoding(file_path)
                        st.session_state["ai_optimizer_file_cache"][file_path] = refreshed_content
                        st.session_state["ai_optimizer_result"] = {
                            **result,
                            "current_code": refreshed_content,
                            "optimized_code": None,
                            "ai_optimizer_applied": True,
                            "ai_optimizer_apply_message": f"Applied optimization to {os.path.basename(file_path)}.",
                        }
                        st.session_state["ai_optimizer_trigger"] = False
                        st.rerun()
                    else:
                        st.error("Could not apply the optimization to the file.")
                except Exception as exc:
                    st.error(f"Failed to apply optimization: {exc}")

    with button_col3:
        if st.button("LEARN MORE", use_container_width=True, key="ai_optimizer_learn_more"):
            st.session_state["ai_optimizer_show_more"] = not st.session_state.get("ai_optimizer_show_more", False)

    # Per-finding controls and Fix All
    if findings:
        st.markdown("### 🔎 All Detected Opportunities")
        for idx, finding in enumerate(findings):
            with st.container():
                st.markdown(f"**{idx+1}. {finding.get('title', finding.get('pattern'))}** — line {finding.get('line', '?')}")
                cols = st.columns([2, 1])
                with cols[0]:
                    st.code(finding.get("original_code") or "", language="python")
                with cols[1]:
                    if finding.get("optimized_code"):
                        st.code(finding.get("optimized_code"), language="python")
                        if st.button("Apply", key=f"apply_{idx}", use_container_width=True):
                            try:
                                file_path = result.get("file_path")
                                applied = False
                                if file_path:
                                    applied = apply_optimized_code_to_file_by_lines(
                                        file_path,
                                        int(finding.get("line") or 0),
                                        int(finding.get("end_line") or finding.get("line") or 0),
                                        finding.get("optimized_code"),
                                    )
                                if not applied and file_path:
                                    applied = apply_optimized_code_to_file(
                                        file_path,
                                        finding.get("original_code"),
                                        finding.get("optimized_code"),
                                    )
                                if not applied and file_path:
                                    applied = apply_optimized_code_to_file_by_lines(
                                        file_path,
                                        int(finding.get("line") or 0),
                                        int(finding.get("end_line") or finding.get("line") or 0),
                                        finding.get("optimized_code"),
                                    )
                                if applied:
                                    refreshed_content = _read_file_with_encoding(file_path)
                                    st.session_state["ai_optimizer_file_cache"][file_path] = refreshed_content
                                    st.session_state["ai_optimizer_result"] = {
                                        **(result or {}),
                                        "current_code": refreshed_content,
                                        "optimized_code": None,
                                        "ai_optimizer_applied": True,
                                        "ai_optimizer_apply_message": f"Applied optimization to {os.path.basename(file_path)}.",
                                    }
                                    st.success("Applied fix — refresh analysis to see changes.")
                                    st.session_state["ai_optimizer_trigger"] = True
                                    st.rerun()
                                else:
                                    st.error("Could not apply fix; original snippet not found.")
                            except Exception as exc:
                                st.error(f"Failed to apply fix: {exc}")
                        if st.button("Copy", key=f"copy_{idx}", use_container_width=True):
                            st.session_state["ai_optimizer_copy_text"] = finding.get("optimized_code")
                            st.success("Fix copied to the output box below.")
                    else:
                        st.info("No auto-apply rewrite available for this finding.")

        # Fix All button: only attempt to apply findings that have optimized_code
        # Fix All button: only attempt to apply findings that have optimized_code and auto_apply set to True
        if st.button("Fix All", key="ai_optimizer_fix_all", use_container_width=True):
            applicable = [f for f in findings if f.get("optimized_code") and f.get("auto_apply", True)]
            if not applicable:
                st.warning("No high-confidence optimizations are available for automatic batch application. You can still apply individual suggestions manually below.")
            else:
                with st.spinner(f"Applying {len(applicable)} optimizations..."):
                    try:
                        summary = apply_multiple_optimizations(result.get("file_path"), applicable)
                        if summary.get("status") == "ok":
                            applied_count = len(summary.get("applied", []))
                            failed_count = len(summary.get("failed", []))
                            if applied_count > 0:
                                st.success(f"✨ Successfully applied {applied_count} optimizations.")
                            if failed_count > 0:
                                st.warning(f"⚠️ {failed_count} optimizations could not be applied automatically (structural mismatch).")
                            
                            if applied_count > 0:
                                st.session_state["ai_optimizer_trigger"] = True
                                st.rerun()
                        else:
                            st.error(f"Batch application failed: {summary.get('error')}")
                    except Exception as exc:
                        st.error(f"An error occurred during application: {exc}")

    if st.session_state.get("ai_optimizer_show_more"):
        with st.expander("Why this optimization helps", expanded=True):
            st.markdown(
                """
                - Direct iteration removes unnecessary index access.
                - Converting repeated membership checks to a set reduces repeated scans.
                - Hoisting repeated calculations keeps the loop body smaller and faster.
                - Fewer branches and smaller functions improve readability and testability.
                """
            )

    if findings and len(findings) > 1:
        with st.expander("Other detected opportunities", expanded=False):
            for finding in findings[1:]:
                st.markdown(
                    f"**{finding.get('title', finding.get('pattern', 'Finding'))}**  \n"
                    f"Line {finding.get('line', '?')} | {finding.get('improvement_type', 'Optimization')}  \n"
                    f"{finding.get('explanation', '')}"
                )
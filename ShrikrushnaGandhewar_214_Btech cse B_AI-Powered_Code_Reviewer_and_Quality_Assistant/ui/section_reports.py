"""Coverage/report/source/json section renderer."""

import json
import os
import re

import pandas as pd
import plotly.express as px
import streamlit as st

from core import doc_steward
from core.doc_steward import generate_coverage_report, get_function_complexity, get_maintainability_index
from ui.dashboard_metrics import calculate_aggregate_metrics
from core import java_support as core_java_support
import streamlit as st

def _get_metrics_data(file_to_scan, selected_language):
    if selected_language == "Python":
        return get_function_complexity(file_to_scan)
    else:
        report = core_java_support.get_java_file_report(file_to_scan)
        functions = []
        analysis = report.get("analysis", {})
        
        source = doc_steward._read_file_with_encoding(file_to_scan)
        lines = source.splitlines()
        
        for m in analysis.get("methods", []):
            functions.append({
                "name": m.get("name"),
                "start_line": int(m.get("line", 0)),
                "end_line": int(m.get("end_line", m.get("line", 0))),
                "has_docstring": core_java_support._java_has_javadoc_before(lines, int(m.get("line", 0))),
                "complexity": 1,
            })
        for cls in analysis.get("classes", []):
            for method in cls.get("methods", []):
                functions.append({
                    "name": f"{cls.get('name')}.{method.get('name')}",
                    "start_line": int(method.get("line", 0)),
                    "end_line": int(method.get("end_line", method.get("line", 0))),
                    "has_docstring": core_java_support._java_has_javadoc_before(lines, int(method.get("line", 0))),
                    "complexity": 1,
                })
                
        documented_count = sum(1 for f in functions if f["has_docstring"])
        total_count = len(functions)
                
        return {
            "total_functions": total_count,
            "documented": documented_count,
            "undocumented": total_count - documented_count,
            "coverage_percent": round((documented_count / total_count * 100) if total_count else 0.0, 2),
            "functions": functions,
        }


def render_coverage_report(file_list, files_to_display=None, show_all_files=True):
    """Render coverage report components for selected files."""
    if not file_list:
        return

    if files_to_display is None:
        files_to_display = file_list

    # Display aggregate metrics report
    if len(file_list) > 1 and show_all_files:
        st.markdown("<div class='ui-section-title'>📊 Aggregate Coverage Dashboard</div>", unsafe_allow_html=True)
        agg_metrics = calculate_aggregate_metrics(file_list)

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("📁 Files", agg_metrics["file_count"])
        col2.metric("Avg MI", f"{round(agg_metrics['avg_mi'], 2)}")
        col3.metric("Total Functions", agg_metrics["total_functions"])
        col4.metric("Avg Coverage (%)", f"{round(agg_metrics['avg_coverage'], 1)}%")
        col5.metric("Documented", agg_metrics["total_documented"])

        # Show visual charts for aggregate coverage and file distribution.
        st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)
        chart_col1, chart_col2 = st.columns([1, 1])

        with chart_col1:
            st.markdown("<h4 style='text-align: center; color: #94a3b8;'>Total Coverage Breakdown</h4>", unsafe_allow_html=True)
            pie_data = pd.DataFrame({
                "Status": ["Documented", "Undocumented"],
                "Count": [agg_metrics["total_documented"], agg_metrics["total_undocumented"]]
            })
            fig_pie = px.pie(
                pie_data,
                names="Status",
                values="Count",
                hole=0.4,
                color="Status",
                color_discrete_map={"Documented": "#10b981", "Undocumented": "#ef4444"},
            )
            fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#f8fafc"))
            st.plotly_chart(fig_pie, use_container_width=True)

        with chart_col2:
            st.markdown("<h4 style='text-align: center; color: #94a3b8;'>File-wise Coverage (%)</h4>", unsafe_allow_html=True)
            file_names = [d["file"] for d in agg_metrics["file_details"]]
            coverages = [d["coverage"] for d in agg_metrics["file_details"]]
            bar_data = pd.DataFrame({"File": file_names, "Coverage (%)": coverages})
            fig_bar = px.bar(
                bar_data,
                x="File",
                y="Coverage (%)",
                color="Coverage (%)",
                color_continuous_scale="Viridis",
                text_auto=".1f",
            )
            fig_bar.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#f8fafc"))
            st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("<div class='ui-section-title'>File-wise Metrics Breakdown</div>", unsafe_allow_html=True)
        file_breakdown = []
        for detail in agg_metrics["file_details"]:
            file_breakdown.append({
                "File": detail["file"],
                "Functions": detail["functions"],
                "Documented": detail["documented"],
                "Coverage (%)": f"{round(detail['coverage'], 1)}%",
                "Maintainability Index": f"{round(detail['mi'], 2)}",
            })
        st.dataframe(file_breakdown, use_container_width=True)
        st.divider()

    # Display individual file analysis.
    if len(file_list) > 1 and show_all_files:
        st.markdown("<div class='ui-section-title'>📄 Individual File Analysis</div>", unsafe_allow_html=True)

    for file_to_scan in files_to_display:
        if not os.path.exists(file_to_scan):
            continue

        file_name = os.path.basename(file_to_scan)
        st.caption(f"📄 Analyzing: {file_name}")
        selected_language = st.session_state.get("selected_language", "Python")
        try:
            metrics_data = _get_metrics_data(file_to_scan, selected_language)
            if selected_language == "Python":
                mi = get_maintainability_index(file_to_scan)
            else:
                mi = 0.0
        except SyntaxError as e:
            error_msg = f"❌ Syntax Error in {file_name} at line {getattr(e, 'lineno', 'unknown')}!"
            st.error(error_msg)
            error_text = getattr(e, 'text', None)
            if error_text:
                st.code(error_text.rstrip(), language="python" if selected_language == "Python" else "java")
                
            if st.button(f"🪄 Auto-Fix Syntax Error in {file_name}", key=f"fix_syntax_report_cov_{file_to_scan}"):
                with st.spinner("Analyzing and fixing syntax error with LLM..."):
                    lang = st.session_state.get("selected_language", "Python")
                    if doc_steward.fix_syntax_error(file_to_scan, lang):
                        st.success("✅ Syntax error corrected! Reloading...")
                        st.rerun()
                    else:
                        st.error("❌ Failed to automatically fix syntax error. Check your GROQ API Key or code complexity.")
            continue

        if metrics_data.get("syntax_error"):
            st.warning(f"⚠️ Syntax error detected in {file_name}. Showing best-effort function and coverage data.")

        st.markdown("<p style='font-size: 14px; color: gray; margin-bottom: 0;'>Maintainability Index</p>", unsafe_allow_html=True)
        st.markdown(f"<h1 style='margin-top: 0;'>{round(mi, 2)}</h1>", unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Functions", metrics_data["total_functions"])
        col2.metric("Documented", metrics_data["documented"])
        col3.metric("Undocumented", metrics_data["undocumented"])
        col4.metric("Coverage (%)", f"{metrics_data['coverage_percent']}%")

        if metrics_data["total_functions"] > 0:
            pie_data = pd.DataFrame({
                "Type": ["Documented", "Undocumented"],
                "Count": [metrics_data["documented"], metrics_data["undocumented"]]
            })
            fig_file_pie = px.pie(
                pie_data,
                names="Type",
                values="Count",
                hole=0.5,
                color="Type",
                color_discrete_map={"Documented": "#3b82f6", "Undocumented": "#f59e0b"},
            )
            fig_file_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#f8fafc"))

            col_p1, col_p2 = st.columns(2)
            with col_p1:
                st.markdown("<h4 style='text-align: center; color: #94a3b8;'>Docstring Presence</h4>", unsafe_allow_html=True)
                st.plotly_chart(fig_file_pie, use_container_width=True, key=f"pie_chart_{file_name}")

            with col_p2:
                st.markdown("<h4 style='text-align: center; color: #94a3b8;'>Docstring Style Validation</h4>", unsafe_allow_html=True)

                valid_functions = 0
                invalid_functions = 0

                pydoc_report = generate_coverage_report([file_to_scan], include_pydocstyle=True).get("pydocstyle", {})
                file_v_details = pydoc_report.get("details", {}).get(file_to_scan, {}).get("violations_detailed", [])
                viol_lines = {v.get("line") for v in file_v_details if v.get("line")}
                viol_symbols = set()
                for violation in file_v_details:
                    msg = violation.get("message", "")
                    symbol_match = re.search(r"`([^`]+)`", msg)
                    if symbol_match:
                        viol_symbols.add(symbol_match.group(1))

                for fn in metrics_data["functions"]:
                    if not fn["has_docstring"] or fn["start_line"] in viol_lines or fn["name"] in viol_symbols:
                        invalid_functions += 1
                    else:
                        valid_functions += 1

                val_pie_data = pd.DataFrame({
                    "Status": ["Valid Standards", "Violations Found"],
                    "Count": [valid_functions, invalid_functions]
                })
                fig_val_pie = px.pie(
                    val_pie_data,
                    names="Status",
                    values="Count",
                    hole=0.5,
                    color="Status",
                    color_discrete_map={"Valid Standards": "#10b981", "Violations Found": "#ef4444"},
                )
                fig_val_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#f8fafc"))
                st.plotly_chart(fig_val_pie, use_container_width=True, key=f"pie_chart_validation_{file_name}")

        st.divider()


def run_report_section(view, file_list, files_to_display, show_all_files, output_json, show_empty_state):
    if view not in ["Function Details", "Source Code", "JSON Output"]:
        return

    if not file_list:
        show_empty_state()
        return

    if len(file_list) > 1 and show_all_files:
        st.markdown("<div class='ui-section-title'>📄 Individual File Analysis</div>", unsafe_allow_html=True)

    for file_to_scan in files_to_display:
        if not os.path.exists(file_to_scan):
            continue

        file_name = os.path.basename(file_to_scan)
        st.caption(f"📄 Analyzing: {file_name}")
        selected_language = st.session_state.get("selected_language", "Python")
        try:
            metrics_data = _get_metrics_data(file_to_scan, selected_language)
        except SyntaxError as e:
            error_msg = f"❌ Syntax Error in {file_name} at line {getattr(e, 'lineno', 'unknown')}!"
            st.error(error_msg)
            error_text = getattr(e, 'text', None)
            if error_text:
                st.code(error_text.rstrip(), language="python" if selected_language == "Python" else "java")
                
            if st.button(f"🪄 Auto-Fix Syntax Error in {file_name}", key=f"fix_syntax_report_json_{file_to_scan}"):
                with st.spinner("Analyzing and fixing syntax error with LLM..."):
                    lang = st.session_state.get("selected_language", "Python")
                    if doc_steward.fix_syntax_error(file_to_scan, lang):
                        st.success("✅ Syntax error corrected! Reloading...")
                        st.rerun()
                    else:
                        st.error("❌ Failed to automatically fix syntax error. Check your GROQ API Key or code complexity.")
            continue

        if view == "Function Details":
            st.subheader("Function Details")
            st.dataframe(metrics_data["functions"], use_container_width=True)

        elif view == "Source Code":
            st.subheader("Source Code")
            try:
                # Safely read file handling multiple potential encodings.
                file_content = doc_steward._read_file_with_encoding(file_to_scan)
                lang_str = "python" if selected_language == "Python" else "java"
                st.code(file_content, language=lang_str)
            except Exception as e:
                st.error(f"❌ Error displaying source code: {e}")

        elif view == "JSON Output":
            st.subheader("JSON Output")
            st.json(metrics_data)

            # Save to JSON.
            output_dir = os.path.dirname(output_json)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            with open(output_json, "w") as f:
                json.dump(metrics_data, f, indent=4)

        st.divider()

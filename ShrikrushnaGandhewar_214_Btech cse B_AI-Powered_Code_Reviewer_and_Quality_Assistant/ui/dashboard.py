"""Dashboard module for visualizing code review analytics."""

import json
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import plotly.graph_objects as go
import plotly.express as px


def _build_docstring_status_df(file_paths: list[str]) -> pd.DataFrame:
    """Create per-function docstring status rows for selected Python files."""
    if not file_paths:
        return pd.DataFrame(columns=["file", "function", "line", "documented"])

    from core import doc_steward as core_doc_steward
    from core import java_support as core_java_support
    import streamlit as st

    selected_language = st.session_state.get("selected_language", "Python")

    rows: list[dict[str, object]] = []
    for file_path in file_paths:
        path_obj = Path(file_path)
        if not path_obj.exists():
            continue

        # Only include files that match the selected language
        suffix = path_obj.suffix.lower()
        if selected_language == "Python" and suffix != ".py":
            continue
        if selected_language == "Java" and suffix != ".java":
            continue

        try:
            if selected_language == "Python":
                analysis = core_doc_steward.analyze_file(str(path_obj))
                for fn in analysis.get("functions", []):
                    rows.append(
                        {
                            "file": path_obj.name,
                            "function": str(fn.get("name", "")),
                            "line": int(fn.get("line") or 0),
                            "documented": bool(fn.get("docstring")),
                        }
                    )

                for cls in analysis.get("classes", []):
                    cls_name = str(cls.get("name", ""))
                    for method in cls.get("methods", []):
                        method_name = str(method.get("name", ""))
                        display_name = f"{cls_name}.{method_name}" if cls_name else method_name
                        rows.append(
                            {
                                "file": path_obj.name,
                                "function": display_name,
                                "line": int(method.get("line") or 0),
                                "documented": bool(method.get("docstring")),
                            }
                        )
            else:
                # Java: use java_support to extract methods and class methods
                source = core_java_support._read_file_with_encoding(str(path_obj))
                analysis = core_java_support.extract_java_entities(source)
                # Top-level methods
                for m in analysis.get("methods", []):
                    rows.append({
                        "file": path_obj.name,
                        "function": m.get("name", ""),
                        "line": int(m.get("line") or 0),
                        "documented": False,  # Java doc presence handled elsewhere
                    })
                # Class methods
                for cls in analysis.get("classes", []):
                    cls_name = cls.get("name", "")
                    for method in cls.get("methods", []):
                        method_name = method.get("name", "")
                        display_name = f"{cls_name}.{method_name}" if cls_name else method_name
                        rows.append({
                            "file": path_obj.name,
                            "function": display_name,
                            "line": int(method.get("line") or 0),
                            "documented": False,
                        })
        except SyntaxError:
            continue

    return pd.DataFrame(rows)


def show_analytics_dashboard():
    """Display docstring analytics for selected files only."""
    st.markdown("## 📊 Documentation Dashboard")

    selected_paths = st.session_state.get("uploaded_file_paths", [])
    if not selected_paths:
        st.info("Select one or more Python files to see documentation analytics.")
        return

    function_df = _build_docstring_status_df(selected_paths)
    if function_df.empty:
        st.warning("No Python functions or methods were found in the selected files.")
        return

    total_functions = int(len(function_df))
    documented_functions = int(function_df["documented"].sum()) if total_functions else 0
    undocumented_functions = total_functions - documented_functions
    coverage_percent = (documented_functions / total_functions * 100.0) if total_functions else 0.0

    selected_names = sorted({Path(path).name for path in selected_paths})
    st.caption("Selected files: " + ", ".join(selected_names))

    metric_cols = st.columns(4)
    metric_cols[0].metric("Total Functions", total_functions)
    metric_cols[1].metric("Documented", documented_functions)
    metric_cols[2].metric("Undocumented", undocumented_functions)
    metric_cols[3].metric("Coverage", f"{coverage_percent:.1f}%")

    st.markdown(
        """
        <style>
        .main .stButton > button {
            min-height: 58px;
            font-size: 1.02rem;
            font-weight: 700;
            border-radius: 11px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Quick Actions")
    action_keys = {
        "filters": "dashboard_show_advanced_filters",
        "search": "dashboard_show_search",
        "export": "dashboard_show_export_controls",
        "help": "dashboard_show_help_tips",
    }
    for state_key in action_keys.values():
        if state_key not in st.session_state:
            st.session_state[state_key] = False

    def _toggle_exclusive_panel(panel_key: str) -> None:
        target_state_key = action_keys[panel_key]
        is_currently_open = bool(st.session_state.get(target_state_key, False))
        for state_key in action_keys.values():
            st.session_state[state_key] = False
        st.session_state[target_state_key] = not is_currently_open

    action_cols = st.columns(4)
    if action_cols[0].button("🔎 Advanced Filters", key="dashboard_toggle_filters", use_container_width=True):
        _toggle_exclusive_panel("filters")
    if action_cols[1].button("🧭 Search", key="dashboard_toggle_search", use_container_width=True):
        _toggle_exclusive_panel("search")
    if action_cols[2].button("📤 Export", key="dashboard_toggle_export", use_container_width=True):
        _toggle_exclusive_panel("export")
    if action_cols[3].button("ℹ️ Help & Tips", key="dashboard_toggle_help", use_container_width=True):
        _toggle_exclusive_panel("help")

    chart_df = function_df.copy()

    if st.session_state[action_keys["filters"]]:
        st.markdown(
            """
            <style>
            .adv-filter-banner {
                background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
                border-radius: 12px;
                padding: 1.1rem 1rem;
                margin: 0.5rem 0 1rem 0;
                color: #eef2ff;
            }
            .adv-filter-title {
                font-size: 1.75rem;
                font-weight: 700;
                margin-bottom: 0.2rem;
            }
            .adv-filter-subtitle {
                font-size: 0.95rem;
                opacity: 0.92;
            }
            .adv-kpi {
                background: linear-gradient(135deg, #5f79e0 0%, #6d65d8 100%);
                border-radius: 10px;
                padding: 0.8rem;
                text-align: center;
                color: #eef2ff;
                margin-bottom: 0.7rem;
            }
            .adv-kpi .value {
                font-size: 1.7rem;
                font-weight: 700;
                line-height: 1;
            }
            .adv-kpi .label {
                font-size: 0.88rem;
                opacity: 0.92;
                margin-top: 0.2rem;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="adv-filter-banner">
                <div class="adv-filter-title">🔎 Advanced Filters</div>
                <div class="adv-filter-subtitle">Filter by files and docstring status, then review exact function rows.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        file_options = sorted(function_df["file"].dropna().astype(str).unique().tolist())
        selected_files = st.multiselect(
            "File scope",
            file_options,
            default=file_options,
            key="dashboard_filter_selected_files",
        )
        filtered_df = function_df.copy()
        if selected_files:
            filtered_df = filtered_df[filtered_df["file"].isin(selected_files)]

        doc_status = st.selectbox(
            "Documentation status",
            ["All", "Yes", "No"],
            key="dashboard_doc_status_filter",
        )
        if doc_status == "Yes":
            filtered_df = filtered_df[filtered_df["documented"] == True]
        elif doc_status == "No":
            filtered_df = filtered_df[filtered_df["documented"] == False]

        chart_df = filtered_df

        kpi_col1, kpi_col2 = st.columns(2)
        with kpi_col1:
            st.markdown(
                f"""
                <div class="adv-kpi">
                    <div class="value">{len(filtered_df)}</div>
                    <div class="label">Showing</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with kpi_col2:
            st.markdown(
                f"""
                <div class="adv-kpi" style="background: linear-gradient(135deg, #6d65d8 0%, #7c3aed 100%);">
                    <div class="value">{len(function_df)}</div>
                    <div class="label">Total</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        preview_df = filtered_df.copy()
        preview_df["line"] = pd.to_numeric(preview_df["line"], errors="coerce").fillna(0).astype(int)
        preview_df["documented"] = preview_df["documented"].map({True: "Yes", False: "No"})
        st.dataframe(
            preview_df[["file", "function", "line", "documented"]].head(150),
            use_container_width=True,
            hide_index=True,
        )

    if st.session_state[action_keys["search"]]:
        st.markdown("#### Search")

        file_options = ["All selected files"] + sorted(function_df["file"].dropna().astype(str).unique().tolist())
        selected_file = st.selectbox(
            "File scope",
            file_options,
            key="dashboard_function_finder_file_scope",
        )

        search_df = function_df.copy()
        if selected_file != "All selected files":
            search_df = search_df[search_df["file"] == selected_file]

        function_options = sorted(search_df["function"].dropna().astype(str).unique().tolist())
        selected_function = st.selectbox(
            "Function name (type to search)",
            ["All functions"] + function_options,
            key="dashboard_function_finder_selected_function",
            help="Start typing a function/method name.",
        )
        if selected_function != "All functions":
            search_df = search_df[search_df["function"] == selected_function]

        search_text = st.text_input(
            "Quick contains search",
            value="",
            key="dashboard_search_text",
            placeholder="Optional keyword filter",
        ).strip().lower()
        if search_text:
            search_df = search_df[
                search_df["function"].fillna("").astype(str).str.lower().str.contains(search_text)
            ]

        search_df = search_df.copy()
        search_df["line"] = pd.to_numeric(search_df["line"], errors="coerce").fillna(0).astype(int)
        search_df["documented"] = search_df["documented"].map({True: "Yes", False: "No"})
        st.caption(f"Found {len(search_df)} function(s) in current search scope.")
        st.dataframe(
            search_df[["file", "function", "line", "documented"]],
            use_container_width=True,
            hide_index=True,
        )

    if st.session_state[action_keys["help"]]:
        st.markdown("#### Help & Tips")
        st.markdown(
            """
            <style>
            .help-hero {
                background: linear-gradient(90deg, #3ddc84 0%, #35d7c4 100%);
                border-radius: 10px;
                padding: 1.1rem 1.2rem;
                margin: 0.35rem 0 0.9rem 0;
                color: #f8fafc;
            }
            .help-hero-title {
                font-size: 1.7rem;
                font-weight: 700;
                line-height: 1.15;
                margin-bottom: 0.25rem;
            }
            .help-card {
                border-radius: 10px;
                padding: 0.9rem 1rem;
                margin: 0.3rem 0 0.8rem 0;
                min-height: 150px;
            }
            .help-card-title {
                font-size: 1.35rem;
                font-weight: 700;
                margin-bottom: 0.35rem;
            }
            .help-line {
                margin: 0.12rem 0;
                font-size: 0.96rem;
                color: #334155;
            }
            .help-card.metrics {
                background: #d4e6db;
                border-left: 4px solid #4ade80;
            }
            .help-card.status {
                background: #f4e9d4;
                border-left: 4px solid #f59e0b;
            }
            .help-card.results {
                background: #d8e8f5;
                border-left: 4px solid #60a5fa;
            }
            .help-card.styles {
                background: #e6d8ef;
                border-left: 4px solid #a855f7;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="help-hero">
                <div class="help-hero-title">ℹ️ Interactive Help &amp; Tips</div>
                <div>Contextual guide for filters, search, coverage visuals, and exports.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        help_col1, help_col2 = st.columns(2)
        with help_col1:
            st.markdown(
                """
                <div class="help-card metrics">
                    <div class="help-card-title">📊 Coverage Metrics</div>
                    <div class="help-line">• Coverage % = (Documented / Total) × 100</div>
                    <div class="help-line">• Pie chart shows documented vs undocumented split</div>
                    <div class="help-line">• File bar chart compares files side-by-side</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown(
                """
                <div class="help-card results">
                    <div class="help-card-title">📈 Dashboard Charts</div>
                    <div class="help-line">• Donut: overall documentation status</div>
                    <div class="help-line">• Bar: file-wise documented vs undocumented</div>
                    <div class="help-line">• Line: coverage percentage per file</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with help_col2:
            st.markdown(
                """
                <div class="help-card status">
                    <div class="help-card-title">✅ Function Status</div>
                    <div class="help-line">• Yes: function has a docstring</div>
                    <div class="help-line">• No: function is undocumented</div>
                    <div class="help-line">• Filters and search update table instantly</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown(
                """
                <div class="help-card styles">
                    <div class="help-card-title">📄 Quick Actions</div>
                    <div class="help-line">• Advanced Filters: file + status scoped view</div>
                    <div class="help-line">• Search: locate specific functions fast</div>
                    <div class="help-line">• Export: download JSON and CSV outputs</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with st.expander("📘 Advanced Usage Guide", expanded=False):
            st.markdown(
                "1. Select files from Home and open Dashboard.\n"
                "2. Use Advanced Filters to focus your scope.\n"
                "3. Use Search to find any function/method quickly.\n"
                "4. Review pie, bar, and coverage graphs.\n"
                "5. Export JSON or CSV for reports."
            )

    display_df = chart_df.copy()
    display_df["line"] = pd.to_numeric(display_df["line"], errors="coerce").fillna(0).astype(int)
    display_df["documented"] = display_df["documented"].map({True: "Yes", False: "No"})

    if st.session_state[action_keys["export"]]:
        st.markdown("#### Export")
        summary_payload = {
            "total_functions": int(len(display_df)),
            "documented": int((display_df["documented"] == "Yes").sum()) if not display_df.empty else 0,
            "undocumented": int((display_df["documented"] == "No").sum()) if not display_df.empty else 0,
            "files": sorted(display_df["file"].dropna().astype(str).unique().tolist()) if not display_df.empty else [],
        }
        st.markdown(
            f"""
            <div style="background: linear-gradient(90deg, #2ea0ea 0%, #19d3da 100%); border-radius: 10px; padding: 1rem 1.2rem; margin: 0.35rem 0 0.8rem 0; color: #f8fafc;">
                <div style="font-size: 1.55rem; font-weight: 700; line-height: 1.1; margin-bottom: 0.2rem;">📤 Export Data</div>
                <div>Download current dashboard scope in JSON or CSV format.</div>
            </div>
            <div style="background: rgba(186, 209, 228, 0.55); border-left: 4px solid #38bdf8; border-radius: 10px; padding: 0.9rem 1rem; margin: 0.4rem 0 0.9rem 0; color: #1e293b;">
                <div style="font-size: 1.2rem; font-weight: 700; margin-bottom: 0.3rem; color: #0f172a;">📊 Export Summary</div>
                <div>• Total Functions: {summary_payload['total_functions']}</div>
                <div>• Documented: {summary_payload['documented']}</div>
                <div>• Undocumented: {summary_payload['undocumented']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        export_json = {
            **summary_payload,
            "rows": display_df.to_dict(orient="records"),
        }
        export_col1, export_col2 = st.columns(2)
        with export_col1:
            st.download_button(
                label="📥 Export Coverage JSON",
                data=json.dumps(export_json, indent=2).encode("utf-8"),
                file_name="function_docstring_summary.json",
                mime="application/json",
                use_container_width=True,
                key="dashboard_export_json",
            )
        with export_col2:
            st.download_button(
                label="📥 Export Coverage CSV",
                data=display_df.to_csv(index=False).encode("utf-8"),
                file_name="function_docstring_coverage.csv",
                mime="text/csv",
                use_container_width=True,
                key="dashboard_export_csv",
            )

    # Pie chart should reflect any active filter choices.
    pie_source_df = chart_df if not chart_df.empty else function_df
    pie_documented = int(pie_source_df["documented"].sum()) if not pie_source_df.empty else 0
    pie_undocumented = int(len(pie_source_df) - pie_documented)

    pie_df = pd.DataFrame(
        [
            {"status": "Documented", "count": pie_documented},
            {"status": "Undocumented", "count": pie_undocumented},
        ]
    )

    pie_fig = px.pie(
        pie_df,
        names="status",
        values="count",
        color="status",
        hole=0.45,
        title="Documented vs Undocumented Functions (All Selected Files)",
        color_discrete_map={
            "Documented": "#10b981",
            "Undocumented": "#ef4444",
        },
    )
    pie_fig.update_traces(textposition="inside", textinfo="label+percent")
    pie_fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Outfit, sans-serif", color="#e2e8f0"),
        legend_title_text="",
    )
    st.plotly_chart(pie_fig, use_container_width=True)

    # Additional visuals to make dashboard insights easier to scan.
    file_coverage_df = (
        pie_source_df.groupby("file", as_index=False)
        .agg(
            total_functions=("function", "count"),
            documented=("documented", "sum"),
        )
    )
    if not file_coverage_df.empty:
        file_coverage_df["documented"] = file_coverage_df["documented"].astype(int)
        file_coverage_df["undocumented"] = file_coverage_df["total_functions"] - file_coverage_df["documented"]
        file_coverage_df["coverage_percent"] = (
            file_coverage_df["documented"] / file_coverage_df["total_functions"] * 100.0
        ).round(1)

        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.markdown("### File-wise Documentation Bar Chart")
            bar_source = file_coverage_df.melt(
                id_vars=["file"],
                value_vars=["documented", "undocumented"],
                var_name="status",
                value_name="count",
            )
            fig_bar = px.bar(
                bar_source,
                x="file",
                y="count",
                color="status",
                barmode="group",
                color_discrete_map={"documented": "#10b981", "undocumented": "#ef4444"},
                title="Documented vs Undocumented by File",
                text_auto=True,
            )
            fig_bar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0.03)",
                font=dict(family="Outfit, sans-serif", color="#e2e8f0"),
                xaxis_title=None,
                yaxis_title="Functions",
                legend_title_text="",
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        with chart_col2:
            st.markdown("### Coverage Report Graph")
            coverage_plot_df = file_coverage_df.sort_values("coverage_percent", ascending=True)
            fig_coverage = px.line(
                coverage_plot_df,
                x="file",
                y="coverage_percent",
                markers=True,
                title="Coverage Percentage by File",
            )
            fig_coverage.update_traces(line=dict(color="#38bdf8", width=3), marker=dict(size=9, color="#22d3ee"))
            fig_coverage.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0.03)",
                font=dict(family="Outfit, sans-serif", color="#e2e8f0"),
                xaxis_title=None,
                yaxis_title="Coverage (%)",
                yaxis_range=[0, 100],
            )
            st.plotly_chart(fig_coverage, use_container_width=True)

    st.markdown("### Function List")
    display_df = display_df.copy()

    st.dataframe(
        display_df[["file", "function", "line", "documented"]],
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        label="⬇️ Download Function Coverage Data (CSV)",
        data=display_df.to_csv(index=False).encode("utf-8"),
        file_name="function_docstring_coverage.csv",
        mime="text/csv",
        use_container_width=True,
    )


def show_overview_tab(data):
    """Display overview metrics and statistics."""
    st.markdown("### Key Metrics Overview")
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "🔎 Total Files Analyzed",
            data["total_files"],
            f"+{data['files_today']} today",
            delta_color="off"
        )
    
    with col2:
        st.metric(
            "⚠️ Issues Found",
            data["total_issues"],
            f"-{data['issues_resolved']} resolved",
            delta_color="inverse"
        )
    
    with col3:
        st.metric(
            "📝 Avg Coverage",
            f"{data['avg_coverage']}%",
            f"+{data['coverage_gain']}%",
            delta_color="off"
        )
    
    with col4:
        st.metric(
            "⭐ Quality Score",
            f"{data['quality_score']}/100",
            f"+{data['score_change']} points",
            delta_color="off"
        )
    
    st.divider()
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.bar(
            data['issues_by_type'],
            x='type',
            y='count',
            title='Issues by Type',
            color_discrete_sequence=['#6366f1'],
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0.02)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Outfit, sans-serif", color="#e2e8f0"),
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.pie(
            data['severity_dist'],
            names='severity',
            values='count',
            title='Issues by Severity',
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Outfit, sans-serif", color="#e2e8f0"),
        )
        st.plotly_chart(fig, use_container_width=True)


def show_quality_tab(data):
    """Display code quality metrics."""
    st.markdown("### Code Quality Metrics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("🏆 Maintainability Index", "78/100", "+5 points")
    
    with col2:
        st.metric("🔄 Cyclomatic Complexity", "3.2", "-0.3")
    
    with col3:
        st.metric("📊 Code Coverage", "85%", "+8%")
    
    st.divider()
    
    # Quality trends
    col1, col2 = st.columns(2)
    
    with col1:
        df = pd.DataFrame({
            'date': pd.date_range(start='2024-01-01', periods=30),
            'score': np.random.randint(70, 95, 30),
        })
        fig = px.line(df, x='date', y='score', title='Quality Score Trend')
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0.02)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Outfit, sans-serif", color="#e2e8f0"),
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        df = pd.DataFrame({
            'category': ['Complexity', 'Duplication', 'Comments', 'Coverage', 'Style'],
            'score': [85, 72, 90, 78, 88],
        })
        # Plotly Express has no `radar`; build a radar chart with Scatterpolar.
        fig = go.Figure()
        fig.add_trace(
            go.Scatterpolar(
                r=df['score'],
                theta=df['category'],
                fill='toself',
                name='Quality',
                line=dict(color='#60a5fa', width=2),
            )
        )
        fig.update_layout(
            title='Quality Radar',
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Outfit, sans-serif", color="#e2e8f0"),
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], gridcolor='rgba(255,255,255,0.15)'),
                angularaxis=dict(gridcolor='rgba(255,255,255,0.15)'),
                bgcolor='rgba(0,0,0,0)',
            ),
        )
        st.plotly_chart(fig, use_container_width=True)


def show_file_analysis_tab(data):
    """Display file analysis visualizations."""
    st.markdown("### File Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.bar(
            data['files_by_size'],
            x='name',
            y='lines',
            title='Files by Size',
            color='issues',
            color_continuous_scale='Reds',
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0.02)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Outfit, sans-serif", color="#e2e8f0"),
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.scatter(
            data['complexity_vs_coverage'],
            x='complexity',
            y='coverage',
            size='lines',
            color='issues',
            title='Complexity vs Coverage',
            color_continuous_scale='Viridis',
            hover_data=['filename'],
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0.02)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Outfit, sans-serif", color="#e2e8f0"),
        )
        st.plotly_chart(fig, use_container_width=True)


def show_trends_tab(data):
    """Display trend analysis."""
    st.markdown("### Trend Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        df = pd.DataFrame({
            'date': pd.date_range(start='2024-01-01', periods=30),
            'issues': np.random.randint(5, 25, 30),
        })
        fig = px.area(df, x='date', y='issues', title='Issues Over Time')
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0.02)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Outfit, sans-serif", color="#e2e8f0"),
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        df = pd.DataFrame({
            'date': pd.date_range(start='2024-01-01', periods=30),
            'resolved': np.random.randint(2, 12, 30),
            'new': np.random.randint(3, 15, 30),
        })
        fig = go.Figure(
            data=[
                go.Scatter(x=df['date'], y=df['new'], name='New Issues'),
                go.Scatter(x=df['date'], y=df['resolved'], name='Resolved'),
            ]
        )
        fig.update_layout(
            title='New vs Resolved Issues',
            plot_bgcolor="rgba(0,0,0,0.02)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Outfit, sans-serif", color="#e2e8f0"),
        )
        st.plotly_chart(fig, use_container_width=True)


def show_performance_tab():
    """Display performance metrics."""
    st.markdown("### Performance Metrics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("⚡ Avg Analysis Time", "2.3s", "-0.5s")
    
    with col2:
        st.metric("🎯 Detection Rate", "94%", "+3%")
    
    with col3:
        st.metric("✅ False Positives", "2.1%", "-0.5%")
    
    st.divider()
    
    # Performance visualization
    categories = ['Speed', 'Accuracy', 'Coverage', 'Reliability', 'Scalability']
    values = [85, 92, 78, 88, 80]
    
    fig = go.Figure(
        data=go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name='Performance'
        )
    )
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                gridcolor="rgba(148, 163, 184, 0.1)",
            ),
            bgcolor="rgba(30, 41, 59, 0.1)",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Outfit, sans-serif", color="#e2e8f0"),
        title='Performance Spider Chart',
    )
    
    st.plotly_chart(fig, use_container_width=True)


def generate_overview_data():
    """Generate sample overview data."""
    return {
        'total_files': 156,
        'files_today': 12,
        'total_issues': 45,
        'issues_resolved': 8,
        'avg_coverage': 85,
        'coverage_gain': 5,
        'quality_score': 82,
        'score_change': 3,
        'issues_by_type': pd.DataFrame({
            'type': ['Style', 'Logic', 'Security', 'Performance', 'Documentation'],
            'count': [15, 12, 8, 6, 4],
        }),
        'severity_dist': pd.DataFrame({
            'severity': ['Critical', 'High', 'Medium', 'Low'],
            'count': [3, 8, 18, 16],
        }),
    }


def generate_file_data():
    """Generate sample file data."""
    files = ['main.py', 'utils.py', 'config.py', 'handler.py', 'models.py']
    return {
        'files_by_size': pd.DataFrame({
            'name': files,
            'lines': [450, 320, 180, 650, 420],
            'issues': [5, 3, 2, 8, 4],
        }),
        'complexity_vs_coverage': pd.DataFrame({
            'filename': files,
            'complexity': [3.2, 2.1, 1.5, 4.8, 2.9],
            'coverage': [85, 92, 78, 65, 88],
            'lines': [450, 320, 180, 650, 420],
            'issues': [5, 3, 2, 8, 4],
        }),
    }


def generate_trend_data():
    """Generate sample trend data."""
    return pd.DataFrame({
        'date': pd.date_range(start='2024-01-01', periods=30),
        'issues': np.random.randint(10, 30, 30),
        'resolved': np.random.randint(5, 15, 30),
    })


def generate_quality_data():
    """Generate sample quality data."""
    return pd.DataFrame({
        'date': pd.date_range(start='2024-01-01', periods=30),
        'score': np.random.randint(75, 95, 30),
        'complexity': np.random.randint(1, 8, 30),
    })


def show_comparison_charts():
    """Show comparison metrics."""
    st.markdown("### 📊 Detailed Comparison")
    
    col1, col2 = st.columns(2)
    
    with col1:
        df = pd.DataFrame({
            'Module': ['Auth', 'Database', 'API', 'Utils', 'Config'],
            'Complexity': [3.2, 2.8, 4.1, 1.9, 1.2],
            'Coverage': [85, 78, 92, 88, 95],
        })
        
        fig = go.Figure(
            data=[
                go.Bar(name='Complexity', x=df['Module'], y=df['Complexity']),
                go.Bar(name='Coverage', x=df['Module'], y=df['Coverage']),
            ]
        )
        fig.update_layout(
            barmode='group',
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0.02)",
            font=dict(family="Outfit, sans-serif", color="#e2e8f0"),
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        df = pd.DataFrame({
            'Language': ['Python', 'JavaScript', 'TypeScript', 'Go'],
            'Files': [45, 32, 28, 15],
            'Issues': [8, 12, 5, 3],
        })
        
        fig = px.scatter(
            df,
            x='Files',
            y='Issues',
            size='Issues',
            hover_name='Language',
            title='Files vs Issues by Language',
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0.02)",
            font=dict(family="Outfit, sans-serif", color="#e2e8f0"),
        )
        st.plotly_chart(fig, use_container_width=True)

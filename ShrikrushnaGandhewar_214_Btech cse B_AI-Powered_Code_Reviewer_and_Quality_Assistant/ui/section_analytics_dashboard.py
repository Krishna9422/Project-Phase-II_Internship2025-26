"""Interactive Analytics Dashboard - Comprehensive Project Metrics & Visualizations."""

import json
import os
from pathlib import Path
from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

from core.doc_steward import get_entity_list, get_function_complexity, get_maintainability_index
from ui.dashboard_metrics import calculate_aggregate_metrics


def load_pytest_results():
    """Load pytest results from the storage."""
    pytest_file = Path("storage/reports/pytest_results.json")
    if pytest_file.exists():
        with open(pytest_file) as f:
            return json.load(f)
    return None


def calculate_test_pass_rate(pytest_data):
    """Calculate the current test pass rate from pytest results."""
    if not pytest_data:
        return None
    
    summary = pytest_data.get("summary", {})
    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    
    if total == 0:
        return 0
    return (passed / total) * 100


def get_test_breakdown(pytest_data):
    """Get detailed test breakdown from pytest results."""
    if not pytest_data:
        return None
    
    tests = pytest_data.get("tests", [])
    outcomes = {}
    
    for test in tests:
        outcome = test.get("outcome", "unknown")
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
    
    return outcomes


def create_metric_card(title, value, unit="", icon="📊", change_text=None, accent="#3b82f6", tone="blue"):
    """Create a modern stats card."""
    st.markdown(
        f"""
        <div class="analytics-card analytics-card-{tone}" style="--accent: {accent};">
            <div class="analytics-card-top">
                <div class="analytics-card-icon">{icon}</div>
                <div class="analytics-card-title">{title}</div>
            </div>
            <div class="analytics-card-value">{value}{unit}</div>
            {f'<div class="analytics-card-note">{change_text}</div>' if change_text else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def run_analytics_dashboard_section(view, file_list, docstring_style):
    """Main analytics dashboard section."""
    if view != "Analytics Dashboard":
        return
    
    st.markdown("""
    <style>
        .analytics-shell {
            position: relative;
            padding: 1.2rem 1.2rem 0.3rem 1.2rem;
            border-radius: 28px;
            background:
                radial-gradient(circle at top left, rgba(59, 130, 246, 0.18), transparent 28%),
                radial-gradient(circle at top right, rgba(168, 85, 247, 0.16), transparent 22%),
                linear-gradient(180deg, rgba(15, 23, 42, 0.92) 0%, rgba(15, 23, 42, 0.84) 100%);
            border: 1px solid rgba(148, 163, 184, 0.16);
            box-shadow: 0 24px 60px rgba(2, 6, 23, 0.35);
        }
        .analytics-hero {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            align-items: flex-end;
            padding: 1.15rem 1.25rem;
            margin-bottom: 1rem;
            border-radius: 22px;
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.14), rgba(15, 23, 42, 0.14));
            border: 1px solid rgba(96, 165, 250, 0.18);
        }
        .analytics-hero h1 {
            margin: 0;
            font-size: 2rem;
            line-height: 1.05;
            font-weight: 800;
            color: #f8fafc;
        }
        .analytics-hero p {
            margin: 0.35rem 0 0 0;
            color: #cbd5e1;
            font-size: 0.98rem;
            max-width: 56rem;
        }
        .analytics-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
            justify-content: flex-end;
        }
        .analytics-chip {
            padding: 0.45rem 0.7rem;
            border-radius: 999px;
            font-size: 0.82rem;
            font-weight: 600;
            color: #dbeafe;
            background: rgba(30, 41, 59, 0.75);
            border: 1px solid rgba(148, 163, 184, 0.16);
        }
        .analytics-section {
            background: rgba(15, 23, 42, 0.58);
            border: 1px solid rgba(148, 163, 184, 0.14);
            border-radius: 22px;
            padding: 1rem 1rem 1.2rem 1rem;
            margin-bottom: 1rem;
            box-shadow: 0 12px 30px rgba(2, 6, 23, 0.18);
        }
        .dashboard-title {
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 50%, #f472b6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.2rem;
        }
        .section-divider {
            height: 2px;
            background: linear-gradient(90deg, rgba(96, 165, 250, 0.35), rgba(168, 85, 247, 0.12), transparent);
            margin: 28px 0;
        }
        .analytics-card {
            min-height: 148px;
            padding: 1rem 1rem 0.95rem 1rem;
            border-radius: 18px;
            background:
                radial-gradient(circle at top right, rgba(255, 255, 255, 0.06), transparent 28%),
                linear-gradient(180deg, rgba(30, 41, 59, 0.9), rgba(15, 23, 42, 0.96));
            border: 1px solid rgba(148, 163, 184, 0.14);
            border-top: 4px solid var(--accent);
            box-shadow: 0 16px 30px rgba(2, 6, 23, 0.2);
        }
        .analytics-card-top {
            display: flex;
            align-items: center;
            gap: 0.65rem;
            margin-bottom: 0.85rem;
        }
        .analytics-card-icon {
            width: 2rem;
            height: 2rem;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 10px;
            background: rgba(59, 130, 246, 0.16);
            font-size: 1rem;
        }
        .analytics-card-title {
            color: #e2e8f0;
            font-size: 0.88rem;
            font-weight: 700;
            letter-spacing: 0.01em;
        }
        .analytics-card-value {
            color: #f8fafc;
            font-size: 2.25rem;
            line-height: 1;
            font-weight: 800;
            letter-spacing: -0.03em;
        }
        .analytics-card-note {
            margin-top: 0.72rem;
            color: #94a3b8;
            font-size: 0.84rem;
        }
        .analytics-card-blue { --accent: #3b82f6; }
        .analytics-card-cyan { --accent: #06b6d4; }
        .analytics-card-emerald { --accent: #22c55e; }
        .analytics-card-violet { --accent: #8b5cf6; }
        .analytics-panel {
            border-radius: 18px;
            padding: 1rem;
            background: rgba(15, 23, 42, 0.72);
            border: 1px solid rgba(148, 163, 184, 0.12);
        }
        .analytics-panel h4 {
            margin: 0 0 0.65rem 0;
            color: #e2e8f0;
        }
        .analytics-panel p,
        .analytics-panel span,
        .analytics-panel small {
            color: #cbd5e1;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(
        """
        <div class="analytics-shell">
            <div class="analytics-hero">
                <div>
                    <h1 class="dashboard-title">Project Analytics Dashboard</h1>
                    <p>
                        A focused snapshot of test health, documentation coverage, maintainability, and file breadth.
                        The panels below are styled to make trends and status easier to scan at a glance.
                    </p>
                </div>
                <div class="analytics-chip-row">
                    <div class="analytics-chip">Live test snapshot</div>
                    <div class="analytics-chip">Documentation quality</div>
                    <div class="analytics-chip">Maintainability review</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Load test results
    pytest_data = load_pytest_results()
    test_pass_rate = calculate_test_pass_rate(pytest_data)
    
    # Calculate aggregate metrics
    agg_metrics = calculate_aggregate_metrics(file_list) if file_list else {}
    
    # ============================================================================
    # SECTION 1: KEY METRICS
    # ============================================================================
    st.markdown('<div class="analytics-section">', unsafe_allow_html=True)
    st.markdown("### 📊 Quality Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        create_metric_card(
            "Test Pass Rate",
            f"{test_pass_rate:.1f}" if test_pass_rate is not None else "N/A",
            unit="%" if test_pass_rate is not None else "",
            icon="🧪",
            change_text="Based on the latest test run",
            accent="#22c55e",
            tone="emerald",
        )
    
    with col2:
        doc_coverage = agg_metrics.get("avg_coverage", 0)
        create_metric_card(
            "Documentation Coverage",
            f"{doc_coverage:.1f}",
            unit="%",
            icon="📚",
            change_text="How much of the codebase is documented",
            accent="#06b6d4",
            tone="cyan",
        )
    
    with col3:
        avg_mi = agg_metrics.get("avg_mi", 0)
        create_metric_card(
            "Code Maintainability",
            f"{avg_mi:.1f}",
            icon="🛠️",
            change_text="Higher values indicate easier maintenance",
            accent="#8b5cf6",
            tone="violet",
        )
    
    with col4:
        file_count = len(file_list) if file_list else 0
        create_metric_card(
            "Total Files Analyzed",
            str(file_count),
            icon="📦",
            change_text="Files included in the current scope",
            accent="#3b82f6",
            tone="blue",
        )
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    
    # ============================================================================
    # SECTION 2: TEST RESULTS
    # ============================================================================
    st.markdown('<div class="analytics-section">', unsafe_allow_html=True)
    st.markdown("### ✅ Test Results Analysis")
    
    if pytest_data:
        col1, col2 = st.columns(2)
        
        with col1:
            # Test Summary
            summary = pytest_data.get("summary", {})
            total = summary.get("total", 0)
            passed = summary.get("passed", 0)
            failed = total - passed
            
            st.markdown(f"""
            <div class="analytics-panel">
                <h4>Test Suite Summary</h4>
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <span>Total Tests:</span>
                    <strong>{total}</strong>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <span>✅ Passed:</span>
                    <strong style="color: #22c55e;">{passed}</strong>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span>❌ Failed:</span>
                    <strong style="color: #ef4444;">{failed}</strong>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Test duration
            duration = pytest_data.get("duration", 0)
            st.info(f"⏱️ Latest test run finished in {duration:.2f} seconds")
        
        with col2:
            # Test outcome pie chart
            test_breakdown = get_test_breakdown(pytest_data)
            if test_breakdown:
                df_tests = pd.DataFrame([
                    {"Outcome": outcome.title(), "Count": count}
                    for outcome, count in test_breakdown.items()
                ])
                
                fig = px.pie(
                    df_tests,
                    values="Count",
                    names="Outcome",
                    color_discrete_map={"Passed": "#22c55e", "Failed": "#ef4444"},
                    hole=0.4
                )
                fig.update_traces(textposition="inside", textinfo="label+percent")
                fig.update_layout(height=300, showlegend=True, margin=dict(l=0, r=0, t=0, b=0))
                st.plotly_chart(fig, use_container_width=True)
        
        # Display Individual Test Results
        st.markdown("#### 📋 Individual Test Results")
        
        tests = pytest_data.get("tests", [])
        if tests:
            # Create detailed test results table
            test_rows = []
            for test in tests:
                test_name = test.get("nodeid", "").split("::")[-1]
                test_file = test.get("nodeid", "").split("::")[0].split("/")[-1] if "::" in test.get("nodeid", "") else "unknown"
                outcome = test.get("outcome", "unknown")
                duration = test.get("call", {}).get("duration", 0) if isinstance(test.get("call"), dict) else 0
                
                test_rows.append({
                    "Status": "✅ PASS" if outcome == "passed" else "❌ FAIL",
                    "Test Name": test_name,
                    "File": test_file,
                    "Duration (s)": f"{duration:.4f}",
                    "Outcome": outcome.title()
                })
            
            df_test_results = pd.DataFrame(test_rows)
            
            # Display with color coding
            col1_tests, col2_tests = st.columns([3, 1])
            
            with col1_tests:
                # Filter options
                test_filter = st.selectbox(
                    "Filter tests:",
                    ["All", "Passed Only", "Failed Only"],
                    key="test_filter"
                )
                
                if test_filter == "Passed Only":
                    df_filtered = df_test_results[df_test_results["Outcome"] == "Passed"]
                elif test_filter == "Failed Only":
                    df_filtered = df_test_results[df_test_results["Outcome"] == "Failed"]
                else:
                    df_filtered = df_test_results
                
                # Color the dataframe
                def color_status(val):
                    if "PASS" in val:
                        return "background-color: rgba(34, 197, 94, 0.3)"
                    elif "FAIL" in val:
                        return "background-color: rgba(239, 68, 68, 0.3)"
                    return ""
                
                styled_df = df_filtered.style.applymap(color_status, subset=["Status"])
                st.dataframe(styled_df, use_container_width=True, height=300)
            
            with col2_tests:
                # Test statistics
                passed_count = len(df_test_results[df_test_results["Outcome"] == "Passed"])
                failed_count = len(df_test_results[df_test_results["Outcome"] == "Failed"])
                
                st.metric("✅ Passed", passed_count)
                st.metric("❌ Failed", failed_count)
            
            # Test file summary
            st.markdown("#### 📁 Tests by File")
            
            file_summary = df_test_results.groupby("File").agg({
                "Status": "count",
                "Outcome": lambda x: (x == "Passed").sum()
            }).rename(columns={"Status": "Total", "Outcome": "Passed"})
            file_summary["Failed"] = file_summary["Total"] - file_summary["Passed"]
            file_summary["Pass Rate %"] = (file_summary["Passed"] / file_summary["Total"] * 100).round(1)
            
            fig_file_summary = px.bar(
                file_summary.reset_index(),
                x="File",
                y=["Passed", "Failed"],
                barmode="stack",
                color_discrete_map={"Passed": "#22c55e", "Failed": "#ef4444"},
                height=300,
                labels={"value": "Count", "variable": "Status"}
            )
            fig_file_summary.update_layout(
                xaxis_title="Test File",
                yaxis_title="Test Count",
                margin=dict(l=50, r=20, t=40, b=100),
                xaxis_tickangle=-45
            )
            st.plotly_chart(fig_file_summary, use_container_width=True)
            
            # Tests per function breakdown
            st.markdown("#### 🔍 Test Count Per Function")
            
            test_func_count = df_test_results.groupby("Test Name").agg({
                "Status": "count",
                "Outcome": lambda x: (x == "Passed").sum()
            }).reset_index()
            test_func_count.columns = ["Test Function", "Total Tests", "Passed Tests"]
            test_func_count["Failed Tests"] = test_func_count["Total Tests"] - test_func_count["Passed Tests"]
            test_func_count = test_func_count.sort_values("Total Tests", ascending=False)
            
            col_count1, col_count2 = st.columns([2, 1])
            
            with col_count1:
                # Display in a nicely formatted table
                st.dataframe(
                    test_func_count[["Test Function", "Total Tests", "Passed Tests", "Failed Tests"]],
                    use_container_width=True,
                    height=350
                )
            
            with col_count2:
                # Horizontal bar chart showing test counts
                fig_count = px.bar(
                    test_func_count.head(10),
                    x="Total Tests",
                    y="Test Function",
                    orientation='h',
                    color="Total Tests",
                    color_continuous_scale="Viridis",
                    height=400,
                    labels={"Total Tests": "Count", "Test Function": ""}
                )
                fig_count.update_layout(
                    xaxis_title="Number of Tests",
                    yaxis_title="",
                    margin=dict(l=150, r=20, t=20, b=20),
                    showlegend=False
                )
                st.plotly_chart(fig_count, use_container_width=True)
            
            # Performance analysis
            st.markdown("#### ⚡ Test Performance")
            
            df_test_results["Duration (float)"] = df_test_results["Duration (s)"].astype(float)
            slowest_tests = df_test_results.nlargest(5, "Duration (float)")[["Test Name", "File", "Duration (s)"]].head(5)
            
            col_perf1, col_perf2 = st.columns(2)
            
            with col_perf1:
                st.markdown("**🐢 Slowest Tests (Top 5)**")
                for idx, row in slowest_tests.iterrows():
                    st.markdown(f"""
                    <div style="background: rgba(245, 158, 11, 0.1); padding: 10px; border-radius: 5px; margin: 5px 0;">
                        <strong>{row['Test Name']}</strong><br/>
                        <small>File: {row['File']} | Duration: {row['Duration (s)']}s</small>
                    </div>
                    """, unsafe_allow_html=True)
            
            with col_perf2:
                # Average duration by outcome
                avg_duration = df_test_results.groupby("Outcome")["Duration (float)"].mean()
                
                if not avg_duration.empty:
                    fig_perf = px.bar(
                        x=avg_duration.index,
                        y=avg_duration.values,
                        color=avg_duration.index,
                        color_discrete_map={"Passed": "#22c55e", "Failed": "#ef4444"},
                        labels={"x": "Test Status", "y": "Avg Duration (s)"},
                        height=250
                    )
                    fig_perf.update_layout(showlegend=False, margin=dict(l=50, r=20, t=20, b=50))
                    st.plotly_chart(fig_perf, use_container_width=True)
        else:
            st.info("No individual test results available")
    else:
        st.warning("⚠️ No test data available yet. Run tests to generate a live snapshot.")
    
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    
    # ============================================================================
    # SECTION 3: CODE QUALITY METRICS
    # ============================================================================
    st.markdown("### 📈 Code Quality Metrics")
    
    if agg_metrics and agg_metrics.get("file_details"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Docstring Coverage by file
            file_details = agg_metrics.get("file_details", [])
            if file_details:
                df_coverage = pd.DataFrame([
                    {
                        "File": Path(f.get("file_path", "")).name,
                        "Coverage %": f.get("coverage", 0)
                    }
                    for f in file_details
                    if f.get("file_path")
                ])
                
                if not df_coverage.empty:
                    fig = px.bar(
                        df_coverage.sort_values("Coverage %", ascending=True),
                        y="File",
                        x="Coverage %",
                        orientation="h",
                        color="Coverage %",
                        color_continuous_scale="viridis",
                        height=400
                    )
                    fig.update_layout(
                        xaxis_title="Docstring Coverage %",
                        yaxis_title="",
                        margin=dict(l=150, r=20, t=40, b=20),
                        showlegend=False
                    )
                    st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Maintainability Index by file
            if file_details:
                df_mi = pd.DataFrame([
                    {
                        "File": Path(f.get("file_path", "")).name,
                        "MI Score": f.get("mi", 0)
                    }
                    for f in file_details
                    if f.get("file_path")
                ])
                
                if not df_mi.empty:
                    fig = px.scatter(
                        df_mi,
                        x="File",
                        y="MI Score",
                        size="MI Score",
                        color="MI Score",
                        color_continuous_scale="RdYlGn",
                        size_max=50,
                        height=400,
                        hover_data=["MI Score"]
                    )
                    fig.update_layout(
                        yaxis_title="Maintainability Index",
                        xaxis_title="",
                        margin=dict(b=100),
                        xaxis_tickangle=-45,
                        showlegend=False
                    )
                    st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📝 Select files to see coverage and maintainability breakdowns.")
    
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    
    # ============================================================================
    # SECTION 4: FUNCTION COMPLEXITY ANALYSIS
    # ============================================================================
    st.markdown("### 🔍 Function Complexity Distribution")
    
    if file_list:
        all_functions = []
        for file_path in file_list:
            try:
                if file_path.endswith(".py"):
                    complexity_data = get_function_complexity(file_path)
                    if complexity_data:
                        functions = complexity_data.get("total_functions", [])
                        if isinstance(functions, list):
                            for func in functions:
                                all_functions.append({
                                    "Name": func.get("name", ""),
                                    "Complexity": func.get("complexity", 1),
                                    "File": Path(file_path).name,
                                    "Documented": func.get("has_docstring", False)
                                })
            except Exception as e:
                continue
        
        if all_functions:
            df_complexity = pd.DataFrame(all_functions)
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Complexity histogram
                fig = px.histogram(
                    df_complexity,
                    x="Complexity",
                    nbins=15,
                    color="Documented",
                    color_discrete_map={True: "#22c55e", False: "#ef4444"},
                    height=350,
                    labels={"Complexity": "Cyclomatic Complexity", "Documented": "Has Docstring"}
                )
                fig.update_layout(
                    xaxis_title="Complexity Score",
                    yaxis_title="Number of Functions",
                    margin=dict(l=20, r=20, t=40, b=20)
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Top complex functions
                st.markdown("**⚠️ Most Complex Functions (Top 5)**")
                top_complex = df_complexity.nlargest(5, "Complexity")[["Name", "Complexity", "File"]]
                
                for idx, row in top_complex.iterrows():
                    status_color = "#ef4444" if row["Complexity"] > 10 else "#f59e0b" if row["Complexity"] > 5 else "#22c55e"
                    st.markdown(f"""
                    <div style="
                        background: rgba(255, 255, 255, 0.05);
                        padding: 12px;
                        border-left: 3px solid {status_color};
                        border-radius: 5px;
                        margin: 8px 0;
                    ">
                        <strong>{row['Name']}</strong><br/>
                        <small>File: {row['File']} | Complexity: {row['Complexity']}</small>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("📊 No function data available for complexity analysis.")
    else:
        st.info("📝 Select files to analyze function complexity.")
    
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    
    # ============================================================================
    # SECTION 5: DOCUMENTATION STATISTICS
    # ============================================================================
    st.markdown("### 📚 Documentation Statistics")
    
    if agg_metrics:
        total_functions = agg_metrics.get("total_functions", 0)
        documented = agg_metrics.get("total_documented", 0)
        undocumented = agg_metrics.get("total_undocumented", 0)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Functions", total_functions)
        
        with col2:
            st.metric("✅ Documented", documented)
        
        with col3:
            st.metric("❌ Undocumented", undocumented)
        
        # Documentation progress
        if total_functions > 0:
            st.markdown("**Documentation Progress**")
            progress_percent = (documented / total_functions) * 100
            st.progress(progress_percent / 100, text=f"{progress_percent:.1f}% Complete")
            
            # Visualization
            col1, col2 = st.columns(2)
            
            with col1:
                fig = go.Figure(data=[
                    go.Bar(name="Documented", x=["Functions"], y=[documented], marker_color="#22c55e"),
                    go.Bar(name="Undocumented", x=["Functions"], y=[undocumented], marker_color="#ef4444")
                ])
                fig.update_layout(
                    barmode="stack",
                    height=300,
                    xaxis_title="",
                    yaxis_title="Count",
                    showlegend=True,
                    margin=dict(l=20, r=20, t=20, b=20)
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Documentation status pie
                fig = go.Figure(data=[
                    go.Pie(
                        labels=["Documented", "Undocumented"],
                        values=[documented, undocumented],
                        marker=dict(colors=["#22c55e", "#ef4444"]),
                        hole=0.4,
                        textposition="inside",
                        textinfo="label+percent"
                    )
                ])
                fig.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0))
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📝 Select files to view documentation statistics.")
    
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    
    # ============================================================================
    # SECTION 6: PROJECT SUMMARY & RECOMMENDATIONS
    # ============================================================================
    st.markdown("### 🎯 Project Summary & Recommendations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📊 Current Status**")
        
        status_items = []
        
        # Test Status
        if test_pass_rate is not None:
            if test_pass_rate >= 99:
                status_items.append("✅ No test failures in the latest run")
            elif test_pass_rate >= 80:
                status_items.append("⚠️ Most tests are passing")
            else:
                status_items.append("❌ Test failures need attention")
        
        # Documentation Status
        if agg_metrics:
            doc_cov = agg_metrics.get("avg_coverage", 0)
            if doc_cov >= 80:
                status_items.append("✅ Good documentation coverage")
            elif doc_cov >= 50:
                status_items.append("⚠️ Documentation could improve")
            else:
                status_items.append("❌ Documentation coverage low")
        
        # Maintainability Status
        if agg_metrics:
            avg_mi = agg_metrics.get("avg_mi", 0)
            if avg_mi >= 70:
                status_items.append("✅ Code is highly maintainable")
            elif avg_mi >= 40:
                status_items.append("⚠️ Code maintainability moderate")
            else:
                status_items.append("❌ Code needs refactoring")
        
        for item in status_items:
            st.write(item)
    
    with col2:
        st.markdown("**💡 Recommendations**")
        
        recommendations = []
        
        if test_pass_rate is not None and test_pass_rate < 100:
            recommendations.append("🧪 Review failing tests to improve code quality")
        
        if agg_metrics and agg_metrics.get("avg_coverage", 0) < 80:
            recommendations.append("📝 Add missing docstrings for better code clarity")
        
        if agg_metrics and agg_metrics.get("avg_mi", 0) < 70:
            recommendations.append("🔧 Refactor complex functions to improve maintainability")
        
        if file_list and len(file_list) > 10:
            recommendations.append("🏗️ Consider modularizing code into smaller files")
        
        if not recommendations:
            recommendations.append("✨ Keep up the great work!")
        
        for idx, rec in enumerate(recommendations, 1):
            st.write(f"{idx}. {rec}")
    
    # ============================================================================
    # FOOTER
    # ============================================================================
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col2:
        st.markdown(f"""
        <div style="text-align: center; color: #64748b; font-size: 12px; margin-top: 20px;">
            📊 Dashboard Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
        """, unsafe_allow_html=True)

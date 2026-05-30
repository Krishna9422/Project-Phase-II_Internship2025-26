"""Tests for dashboard metrics aggregation."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from ui.dashboard_metrics import calculate_aggregate_metrics


def test_calculate_aggregate_metrics_includes_java_syntax_errors(monkeypatch, tmp_path: Path):
    """Java syntax diagnostics should be exposed in aggregate syntax_errors."""
    java_file = tmp_path / "Broken.java"
    java_file.write_text("public class Broken {}\n", encoding="utf-8")

    st.session_state.selected_language = "Java"

    def fake_report(_file_path: str):
        return {
            "methods": 1,
            "classes": 1,
            "documented_count": 0,
            "syntax_errors": [
                {
                    "line": 6,
                    "column": 8,
                    "message": "';' expected",
                    "source": "        return total",
                }
            ],
        }

    monkeypatch.setattr("ui.dashboard_metrics.core_java_support.get_java_file_report", fake_report)

    result = calculate_aggregate_metrics([str(java_file)])

    assert result["syntax_errors"]
    assert result["syntax_errors"][0]["lineno"] == 6
    assert result["syntax_errors"][0]["column"] == 8
    assert result["syntax_errors"][0]["message"] == "';' expected"

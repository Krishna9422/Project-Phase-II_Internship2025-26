"""Tests for Java support helpers."""

from __future__ import annotations

from pathlib import Path

from core.java_support import (
    _parse_javac_output,
    _flatten_java_methods,
    apply_java_optimization_to_file,
    apply_javadocs_to_file,
    extract_java_entities,
    generate_javadoc_comment,
    get_java_file_report,
)


def test_extract_java_entities_finds_class_and_methods():
    """Java parsing should find one class and two methods."""
    source = """
public class Demo {
    public int findMax(int[] numbers) {
        return numbers[0];
    }

    private String label(String name, int count) {
        return name + count;
    }
}
"""
    analysis = extract_java_entities(source)

    assert len(analysis["classes"]) == 1
    assert len(analysis["classes"][0]["methods"]) == 2


def test_generate_javadoc_comment_includes_parameters():
    """Generated JavaDoc should mention each parameter."""
    entity = {
        "kind": "method",
        "name": "findMax",
        "indent": "    ",
        "parameters": ["int[] numbers", "int limit"],
        "return_type": "int",
    }

    comment = generate_javadoc_comment(entity)

    assert "@param numbers" in comment
    assert "@param limit" in comment
    assert "@return" in comment


def test_java_report_detects_missing_javadocs_and_findings(tmp_path: Path):
    """The report should surface missing JavaDocs and optimization opportunities."""
    file_path = tmp_path / "Demo.java"
    file_path.write_text(
        """
public class Demo {
    public int findMax(int[] numbers) {
        int max = numbers[0];
        for (int i = 0; i < numbers.size(); i++) {
            max = Math.max(max, numbers[i]);
        }
        return max;
    }
}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    report = get_java_file_report(str(file_path))

    assert report["classes"] == 1
    assert report["methods"] == 1
    assert report["missing_javadocs_count"] >= 1
    assert report["optimization_count"] >= 1
    assert report["optimization_findings"][0]["auto_apply"] is True


def test_apply_javadocs_to_file_adds_methods_after_class_docstring(tmp_path: Path):
    """Bulk JavaDoc insertion should not confuse a class docstring with method docs."""
    file_path = tmp_path / "StudentManager.java"
    file_path.write_text(
        """
import java.util.*;

/**
 * Provides methods for managing student data and performing various calculations.
 */
public class StudentManager {

    public static double calculateAverage(int[] numbers) {
        return 0;
    }
}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    before_report = get_java_file_report(str(file_path))
    assert before_report["missing_javadocs_count"] >= 1

    analysis = before_report["analysis"]
    inserted = apply_javadocs_to_file(
        str(file_path),
        list(analysis.get("classes", [])) + _flatten_java_methods(analysis),
        use_llm=False,
    )

    updated = file_path.read_text(encoding="utf-8")
    after_report = get_java_file_report(str(file_path))

    assert inserted >= 1
    assert updated.count("/**") >= 2
    assert after_report["missing_javadocs_count"] < before_report["missing_javadocs_count"]


def test_apply_java_optimization_to_file_rewrites_loop(tmp_path: Path):
    """Safe Java refactors should update the matched snippet in place."""
    file_path = tmp_path / "Demo.java"
    file_path.write_text(
        """
public class Demo {
    public int findMax(int[] numbers) {
        int max = numbers[0];
        for (int i = 0; i < numbers.size(); i++) {
            max = Math.max(max, numbers[i]);
        }
        return max;
    }
}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    report = get_java_file_report(str(file_path))
    finding = report["optimization_findings"][0]

    applied = apply_java_optimization_to_file(
        str(file_path),
        finding["original_code"],
        finding["optimized_code"],
    )

    updated = file_path.read_text(encoding="utf-8")

    assert applied is True
    assert "numbersSize = numbers.size()" in updated
    assert "numbers.size()" not in updated.split("numbersSize = numbers.size()", 1)[1]


def test_parse_javac_output_extracts_line_and_message():
    """Compiler output should map to structured diagnostics with line numbers."""
    javac_output = (
        "Demo.java:7: error: ';' expected\n"
        "        return total\n"
        "                    ^\n"
        "Demo.java:10: error: reached end of file while parsing\n"
        "}\n"
        " ^\n"
    )

    diagnostics = _parse_javac_output(javac_output)

    assert len(diagnostics) == 2
    assert diagnostics[0]["line"] == 7
    assert diagnostics[0]["message"] == "';' expected"
    assert diagnostics[0]["column"] is not None
    assert diagnostics[1]["line"] == 10


def test_java_report_includes_syntax_error_fields(tmp_path: Path):
    """Java file reports should always include syntax error metadata fields."""
    file_path = tmp_path / "Demo.java"
    file_path.write_text(
        """
public class Demo {
    public int add(int a, int b) {
        return a + b;
    }
}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    report = get_java_file_report(str(file_path))

    assert "syntax_errors" in report
    assert "syntax_error_count" in report
    assert "has_syntax_error" in report
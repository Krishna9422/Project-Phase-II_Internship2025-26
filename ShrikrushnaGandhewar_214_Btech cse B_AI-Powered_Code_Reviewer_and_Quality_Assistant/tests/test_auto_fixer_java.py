"""Tests for Java syntax local fallback in auto_fixer."""

from __future__ import annotations

from core.auto_fixer import _try_apply_java_fix


def test_try_apply_java_fix_renames_public_class_to_file_name():
    """Public class name should be aligned to file name when compiler reports mismatch."""
    lines = ["public class Main {\n", "}\n"]
    error = {"line": 1, "message": "class Main is public, should be declared in a file named StudentManager.java"}

    changed = _try_apply_java_fix(lines, error, "StudentManager.java")

    assert changed is True
    assert lines[0].startswith("public class StudentManager")


def test_try_apply_java_fix_adds_missing_semicolon():
    """A ';' expected error should append semicolon to the target line."""
    lines = ["public class Demo {\n", "    return total\n", "}\n"]
    error = {"line": 2, "message": "';' expected"}

    changed = _try_apply_java_fix(lines, error, "Demo.java")

    assert changed is True
    assert lines[1].rstrip().endswith(";")

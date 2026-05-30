"""Tests for the AI optimizer."""

from pathlib import Path

from core.ai_optimizer import (
    analyze_and_optimize_code,
    apply_multiple_optimizations,
    apply_optimized_code_to_file,
    generate_rewrite_for_finding,
)


def test_ai_optimizer_detects_range_len_loop():
    """Direct iteration should replace range(len(...)) loops."""
    source = """
def render_items(arr):
    for i in range(len(arr)):
        print(arr[i])
"""
    result = analyze_and_optimize_code(source)

    assert result["findings"]
    assert result["optimized_code"]
    assert "for item in arr" in result["optimized_code"]
    assert "print(item)" in result["optimized_code"]


def test_ai_optimizer_detects_nested_loop_membership():
    """Nested membership scans should become set lookups."""
    source = """
def intersect(a, b):
    for i in range(len(a)):
        for j in range(len(b)):
            if a[i] == b[j]:
                print(a[i])
"""
    result = analyze_and_optimize_code(source)

    assert result["findings"]
    assert result["complexity_before"] == "O(n²)"
    assert result["complexity_after"] == "O(n)"
    assert "b_set = set(b)" in result["optimized_code"]
    assert "if item in b_set" in result["optimized_code"]


def test_ai_optimizer_detects_long_function():
    """Long functions should still be detected even when no rewrite is applied."""
    body = "\n".join("    x = 1" for _ in range(40))
    source = f"""
def very_long_function():
{body}
"""
    result = analyze_and_optimize_code(source)

    assert result["findings"]
    assert any(finding["pattern"] == "long_function" for finding in result["findings"])


def test_ai_optimizer_fix_all_applies_multiple_findings(tmp_path: Path):
    """Batch apply should rewrite multiple optimizer findings in one file."""
    file_path = tmp_path / "Demo.py"
    file_path.write_text(
        """
def render_items(arr):
    for i in range(len(arr)):
        print(arr[i])


def summarize(items):
    total = 0
    for i in range(len(items)):
        total += len(items)
    return total
""".strip()
        + "\n",
        encoding="utf-8",
    )

    source = file_path.read_text(encoding="utf-8")
    result = analyze_and_optimize_code(source, file_path=str(file_path))
    findings = [finding for finding in result["findings"] if finding.get("optimized_code")]

    summary = apply_multiple_optimizations(str(file_path), findings)
    updated = file_path.read_text(encoding="utf-8")

    assert summary["status"] == "ok"
    assert len(summary["applied"]) >= 2
    assert "for item in arr" in updated
    assert "items_len = len(items)" in updated


def test_ai_optimizer_apply_fix_rolls_back_invalid_python(tmp_path: Path):
    """Invalid Python edits should not be left on disk."""
    file_path = tmp_path / "sample_b.py"
    original = """
def demo():
    return 1
""".strip() + "\n"
    file_path.write_text(original, encoding="utf-8")

    applied = apply_optimized_code_to_file(
        str(file_path),
        "return 1",
        "return (",
    )

    assert applied is False
    assert file_path.read_text(encoding="utf-8") == original


def test_ai_optimizer_apply_fix_accepts_valid_python(tmp_path: Path):
    """Valid Python replacements should still be applied."""
    file_path = tmp_path / "sample_b.py"
    original = """
def demo():
    return 1
""".strip() + "\n"
    file_path.write_text(original, encoding="utf-8")

    applied = apply_optimized_code_to_file(
        str(file_path),
        "return 1",
        "return 2",
    )

    assert applied is True
    assert file_path.read_text(encoding="utf-8") == original.replace("return 1", "return 2", 1)


def test_ai_optimizer_apply_fix_accepts_whitespace_variants(tmp_path: Path):
    """Replacement should still work when indentation in the stored snippet drifts."""
    file_path = tmp_path / "sample_b.py"
    original = """
def demo():
    if True:
        return 1
""".strip() + "\n"
    file_path.write_text(original, encoding="utf-8")

    applied = apply_optimized_code_to_file(
        str(file_path),
        "def demo():\nif True:\nreturn 1",
        "def demo():\n    if False:\n        return 2",
    )

    assert applied is True
    assert "return 2" in file_path.read_text(encoding="utf-8")


def test_ai_optimizer_generate_rewrite_falls_back_locally(monkeypatch):
    """Generate Rewrite should still produce a rewrite when no API keys are set."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    candidate = {
        "original_code": "def demo():\n    return 1\n",
        "optimized_code": None,
        "improvement_type": "Remove Redundancy",
        "complexity_before": "O(1)",
        "complexity_after": "O(1)",
    }

    rewrite, provider = generate_rewrite_for_finding(candidate)

    assert rewrite is not None
    assert provider == "local"
    assert "def demo" in rewrite


def test_ai_optimizer_detects_return_outside_function_syntax_error():
    """Compile-time syntax errors like return outside function must be detected."""
    source = """
def f():
    x = 1
return x
""".strip() + "\n"

    result = analyze_and_optimize_code(source, file_path="demo.py")

    assert result["syntax_error"] is not None
    assert result["syntax_error_type"] == "SyntaxError"
    assert result["syntax_fixed"] is True
    assert result["fixed_source"] is not None


def test_ai_optimizer_autofix_indents_return_outside_function():
    """Auto-fix should indent a misplaced return to the surrounding block indent."""
    source = """
def f():
    x = 1
return x
""".strip() + "\n"

    result = analyze_and_optimize_code(source, file_path="demo.py")

    fixed = result.get("fixed_source") or ""
    assert "\n    return x\n" in fixed
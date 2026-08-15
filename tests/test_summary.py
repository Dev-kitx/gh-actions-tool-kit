import pytest
from pathlib import Path

from actions_tool_kit.summary import SummaryBuilder


def test_add_heading_levels():
    sb = SummaryBuilder()
    sb.add_heading("Title", level=1)
    sb.add_heading("Sub", level=2)
    md = sb.build()
    assert "# Title" in md
    assert "## Sub" in md


def test_add_heading_invalid_level():
    with pytest.raises(ValueError, match="Heading level"):
        SummaryBuilder().add_heading("x", level=7)

    with pytest.raises(ValueError):
        SummaryBuilder().add_heading("x", level=0)


def test_add_paragraph():
    md = SummaryBuilder().add_paragraph("Hello world").build()
    assert "Hello world" in md


def test_add_code_block_no_lang():
    md = SummaryBuilder().add_code_block("print('hi')").build()
    assert "```\nprint('hi')\n```" in md


def test_add_code_block_with_lang():
    md = SummaryBuilder().add_code_block("echo hi", lang="sh").build()
    assert "```sh\necho hi\n```" in md


def test_add_table():
    md = (
        SummaryBuilder()
        .add_table(
            headers=["Name", "Status"],
            rows=[["api", "ok"], ["worker", "fail"]],
        )
        .build()
    )
    assert "| Name | Status |" in md
    assert "| --- | --- |" in md
    assert "| api | ok |" in md
    assert "| worker | fail |" in md


def test_add_list_unordered():
    md = SummaryBuilder().add_list(["a", "b", "c"]).build()
    assert "- a" in md
    assert "- b" in md


def test_add_list_ordered():
    md = SummaryBuilder().add_list(["x", "y"], ordered=True).build()
    assert "1. x" in md
    assert "2. y" in md


def test_add_separator():
    md = SummaryBuilder().add_separator().build()
    assert "---" in md


def test_add_raw():
    md = SummaryBuilder().add_raw("<custom>html</custom>").build()
    assert "<custom>html</custom>" in md


def test_add_link():
    md = SummaryBuilder().add_link("Docs", "https://example.com").build()
    assert "[Docs](https://example.com)" in md


def test_add_image_basic():
    md = SummaryBuilder().add_image("https://img.example.com/logo.png", alt="Logo").build()
    assert 'src="https://img.example.com/logo.png"' in md
    assert 'alt="Logo"' in md


def test_add_image_with_dimensions():
    md = SummaryBuilder().add_image("img.png", width=200, height=100).build()
    assert 'width="200"' in md
    assert 'height="100"' in md


def test_chaining_returns_self():
    sb = SummaryBuilder()
    result = sb.add_heading("H").add_paragraph("p").add_separator()
    assert result is sb


def test_clear():
    sb = SummaryBuilder().add_heading("H")
    assert sb.build()
    sb.clear()
    assert sb.build() == ""


def test_bool_empty():
    assert not SummaryBuilder()


def test_bool_non_empty():
    assert SummaryBuilder().add_heading("H")


def test_write_appends_to_summary_file(tmp_path, monkeypatch):
    sumf = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(sumf))
    SummaryBuilder().add_heading("Test Report").add_paragraph("All good.").write()
    content = sumf.read_text()
    assert "# Test Report" in content
    assert "All good." in content


def test_full_report_structure():
    md = (
        SummaryBuilder()
        .add_heading("Deploy Report", level=1)
        .add_table(
            headers=["Service", "Version", "Status"],
            rows=[
                ["api", "1.2.3", ":white_check_mark:"],
                ["worker", "1.2.3", ":x:"],
            ],
        )
        .add_separator()
        .add_code_block("kubectl rollout status deploy/api", lang="sh")
        .build()
    )
    assert "# Deploy Report" in md
    assert "| Service | Version | Status |" in md
    assert "---" in md
    assert "```sh" in md

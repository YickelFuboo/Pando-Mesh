from pathlib import Path

import pytest

from app.workspace.refs import (
    expand_session_placeholders,
    expand_workspace_ref_paths,
    has_path_pattern,
    has_path_wildcard,
    inspect_workspace_refs,
    normalize_node_doc_path_lists,
    normalize_node_doc_refs,
    parse_doc_path_list,
    parse_workspace_refs,
    resolve_workspace_ref_path,
)
from app.workspace.refs import NodeWorkspaceRef


def test_expand_session_placeholders(tmp_path: Path):
    ws = tmp_path / "project"
    req_dir = ws / "requirements" / "req1"
    req_dir.mkdir(parents=True)
    text = expand_session_placeholders(
        "请使用{workspace}/skill/xxx，对{workspace}/requirements/{requirement_id}（{requirement_id}）分析",
        workspace_path=str(ws),
        requirement_id="req1",
    )
    assert str(ws.resolve()) in text
    assert "requirements/req1" in text.replace("\\", "/")
    assert "req1" in text


def test_normalize_node_doc_path_lists_prefers_explicit_fields():
    inp, out = normalize_node_doc_path_lists(
        input_doc_paths=["a.md"],
        output_doc_paths=["b.md"],
        doc_path="legacy.md",
        workspace_refs=parse_workspace_refs([{"path": "old.md"}]),
    )
    assert inp == ["a.md"]
    assert out == ["b.md"]


def test_normalize_node_doc_path_lists_migrates_legacy():
    inp, out = normalize_node_doc_path_lists(
        doc_path="requirements/{requirement_id}/legacy.md",
        workspace_refs=parse_workspace_refs([
            {"path": "requirements/{requirement_id}/legacy.md"},
            {"path": "requirements/{requirement_id}/other.md"},
        ]),
    )
    assert inp == [
        "requirements/{requirement_id}/legacy.md",
        "requirements/{requirement_id}/other.md",
    ]
    assert out == []


def test_parse_doc_path_list():
    assert parse_doc_path_list(["a.md", {"path": "b.md"}, ""]) == ["a.md", "b.md"]


def test_normalize_node_doc_refs_merges_doc_path():
    refs = normalize_node_doc_refs(
        "requirements/{requirement_id}/a.md",
        parse_workspace_refs([
            {"path": "requirements/{requirement_id}/a.md", "label": "重复"},
            {"path": "requirements/{requirement_id}/b.md"},
        ]),
    )
    assert [ref.path for ref in refs] == [
        "requirements/{requirement_id}/a.md",
        "requirements/{requirement_id}/b.md",
    ]


def test_parse_workspace_refs():
    refs = parse_workspace_refs([
        {"path": "src/a.py", "label": "源码"},
        "docs/readme.md",
        {"path": ""},
    ])
    assert len(refs) == 2
    assert refs[0].path == "src/a.py"
    assert refs[0].label == "源码"


def test_resolve_workspace_ref_relative(tmp_path: Path):
    ws = tmp_path / "project"
    ws.mkdir()
    target = ws / "src" / "main.py"
    target.parent.mkdir(parents=True)
    target.write_text("print('ok')", encoding="utf-8")
    resolved = resolve_workspace_ref_path(str(ws), "req1", "src/main.py")
    assert resolved == target.resolve()


def test_resolve_workspace_ref_placeholders(tmp_path: Path):
    ws = tmp_path / "project"
    req_dir = ws / "requirements" / "req1"
    req_dir.mkdir(parents=True)
    doc = req_dir / "design.md"
    doc.write_text("# design", encoding="utf-8")
    resolved = resolve_workspace_ref_path(str(ws), "req1", "requirements/{requirement_id}/design.md")
    assert resolved == doc.resolve()


def test_resolve_rejects_path_outside_workspace(tmp_path: Path):
    ws = tmp_path / "project"
    ws.mkdir()
    outside = resolve_workspace_ref_path(str(ws), "", "../../outside.txt")
    assert outside is None


def test_inspect_workspace_refs_file_and_dir(tmp_path: Path):
    ws = tmp_path / "project"
    src = ws / "src"
    src.mkdir(parents=True)
    (src / "app.py").write_text("# app", encoding="utf-8")
    (src / "utils").mkdir()
    (src / "utils" / "helper.py").write_text("x = 1", encoding="utf-8")
    refs = [
        NodeWorkspaceRef(path="src/app.py", label="应用"),
        NodeWorkspaceRef(path="src/utils/", label="工具目录"),
        NodeWorkspaceRef(path="missing.txt", label="缺失"),
    ]
    items = inspect_workspace_refs(workspace_path=str(ws), requirement_id="", refs=refs)
    assert items[0]["exists"] is True
    assert items[0]["kind"] == "file"
    assert "preview" in items[0]
    assert items[1]["exists"] is True
    assert items[1]["kind"] == "dir"
    assert len(items[1]["entries"]) >= 1
    assert items[2]["exists"] is False


def test_expand_workspace_ref_paths_single_wildcard(tmp_path: Path):
    ws = tmp_path / "project"
    req = ws / "requirements" / "req1" / "feature_changes"
    (req / "change-a").mkdir(parents=True)
    (req / "change-b").mkdir(parents=True)
    (req / "change-a" / "需求分析.md").write_text("# A", encoding="utf-8")
    (req / "change-b" / "需求分析.md").write_text("# B", encoding="utf-8")
    pattern = "requirements/{requirement_id}/feature_changes/{*}/需求分析.md"
    matches = expand_workspace_ref_paths(str(ws), "req1", pattern)
    assert len(matches) == 2
    texts = sorted(path.read_text(encoding="utf-8") for path in matches)
    assert texts == ["# A", "# B"]


def test_expand_workspace_ref_paths_no_match(tmp_path: Path):
    ws = tmp_path / "project"
    base = ws / "requirements" / "req1" / "feature_changes"
    base.mkdir(parents=True)
    matches = expand_workspace_ref_paths(
        str(ws),
        "req1",
        "requirements/{requirement_id}/feature_changes/{*}/需求分析.md",
    )
    assert matches == []


def test_resolve_workspace_ref_path_rejects_wildcard(tmp_path: Path):
    ws = tmp_path / "project"
    ws.mkdir()
    assert resolve_workspace_ref_path(str(ws), "req1", "a/{*}/b.md") is None


def test_inspect_workspace_refs_glob(tmp_path: Path):
    ws = tmp_path / "project"
    req = ws / "requirements" / "req1" / "feature_changes"
    (req / "feat-1").mkdir(parents=True)
    (req / "feat-1" / "需求分析.md").write_text("# doc", encoding="utf-8")
    refs = [NodeWorkspaceRef(path="requirements/{requirement_id}/feature_changes/{*}/需求分析.md", label="输入")]
    items = inspect_workspace_refs(workspace_path=str(ws), requirement_id="req1", refs=refs)
    assert items[0]["kind"] == "glob"
    assert items[0]["wildcard"] is True
    assert items[0]["match_count"] == 1
    assert items[0]["matches"][0]["preview"] == "# doc"


def test_expand_workspace_ref_paths_filename_wildcard(tmp_path: Path):
    ws = tmp_path / "project"
    base = ws / "requirements" / "req1" / "feature_changes" / "feat-a"
    base.mkdir(parents=True)
    (base / "需求分析.md").write_text("# fixed", encoding="utf-8")
    (base / "设计说明.md").write_text("# design", encoding="utf-8")
    matches = expand_workspace_ref_paths(
        str(ws),
        "req1",
        "requirements/{requirement_id}/feature_changes/{*}/{*}.md",
    )
    assert len(matches) == 2
    names = sorted(path.name for path in matches)
    assert names == ["设计说明.md", "需求分析.md"]


def test_expand_workspace_ref_paths_with_workspace_prefix(tmp_path: Path):
    ws = tmp_path / "project"
    base = ws / "requirements" / "req1" / "feature_changes" / "feat-a"
    base.mkdir(parents=True)
    (base / "SR-001.md").write_text("# one", encoding="utf-8")
    (base / "SR-002.md").write_text("# two", encoding="utf-8")
    pattern = "{workspace}/requirements/{requirement_id}/feature_changes/{*}/{*}.md"
    matches = expand_workspace_ref_paths(str(ws), "req1", pattern)
    assert len(matches) == 2
    names = sorted(path.name for path in matches)
    assert names == ["SR-001.md", "SR-002.md"]


def test_expand_workspace_ref_paths_filename_prefix_wildcard(tmp_path: Path):
    ws = tmp_path / "project"
    base = ws / "requirements" / "req1" / "feature_changes" / "feat-a"
    base.mkdir(parents=True)
    (base / "需求分析.md").write_text("# ok", encoding="utf-8")
    (base / "设计说明.md").write_text("# skip", encoding="utf-8")
    matches = expand_workspace_ref_paths(
        str(ws),
        "req1",
        "requirements/{requirement_id}/feature_changes/{*}/需求{*}.md",
    )
    assert len(matches) == 1
    assert matches[0].name == "需求分析.md"


def test_expand_workspace_ref_paths_regex_directory_and_filename(tmp_path: Path):
    ws = tmp_path / "project"
    base = ws / "requirements" / "req1" / "feature_changes"
    (base / "feat-001").mkdir(parents=True)
    (base / "feat-002").mkdir(parents=True)
    (base / "legacy").mkdir(parents=True)
    (base / "feat-001" / "需求分析.md").write_text("# a", encoding="utf-8")
    (base / "feat-002" / "设计说明.md").write_text("# b", encoding="utf-8")
    (base / "legacy" / "需求分析.md").write_text("# skip", encoding="utf-8")
    matches = expand_workspace_ref_paths(
        str(ws),
        "req1",
        r"requirements/{requirement_id}/feature_changes/{re:feat-\d+}/{re:需求.*\.md}",
    )
    assert len(matches) == 1
    assert matches[0].name == "需求分析.md"
    assert "feat-001" in str(matches[0])


def test_expand_workspace_ref_paths_invalid_regex_returns_empty(tmp_path: Path):
    ws = tmp_path / "project"
    (ws / "requirements" / "req1").mkdir(parents=True)
    matches = expand_workspace_ref_paths(str(ws), "req1", r"requirements/{requirement_id}/{re:[invalid}")
    assert matches == []


def test_has_path_pattern_detects_regex():
    assert has_path_pattern(r"requirements/{re:feat-\d+}/doc.md")
    assert not has_path_pattern("requirements/req1/doc.md")

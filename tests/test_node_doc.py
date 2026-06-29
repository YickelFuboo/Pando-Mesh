from pathlib import Path

import pytest

from app.graph.plan_graph import DirectExecGraph
from app.session.node_doc import load_node_doc, load_requirement_readme


def _graph_with_node(node_id: str = "step_a", task: str = "完成开发", label: str = "开发") -> DirectExecGraph:
    return DirectExecGraph.from_dict({
        "nodes": [{"id": node_id, "label": label, "task": task, "executor": {"kind": "cli", "cli": {"commands": [{"command": "echo", "args": ["ok"]}]}}}],
        "edges": [
            {"from": "START", "to": node_id, "condition": "always"},
            {"from": node_id, "to": "END", "condition": "always"},
        ],
        "entry": node_id,
    })


def test_load_requirement_readme(tmp_path: Path):
    req_dir = tmp_path / "requirements" / "req1"
    req_dir.mkdir(parents=True)
    (req_dir / "README.md").write_text("# 需求说明\n\n内容", encoding="utf-8")
    doc = load_requirement_readme(str(tmp_path), "req1")
    assert doc is not None
    assert doc.label == "需求说明"
    assert "需求说明" in doc.content
    assert doc.generated is False


def test_load_node_doc_from_file(tmp_path: Path):
    req_dir = tmp_path / "requirements" / "req1"
    req_dir.mkdir(parents=True)
    (req_dir / "step_a.md").write_text("# 步骤 A\n\n详细说明", encoding="utf-8")
    graph = _graph_with_node()
    doc = load_node_doc(
        workspace_path=str(tmp_path),
        requirement_id="req1",
        graph=graph,
        node_id="step_a",
    )
    assert doc.generated is False
    assert "详细说明" in doc.content
    assert doc.source_path.endswith("step_a.md")
    assert doc.workspace_refs == []


def test_load_node_doc_with_workspace_refs(tmp_path: Path):
    ws = tmp_path / "project"
    req_dir = ws / "requirements" / "req1"
    req_dir.mkdir(parents=True)
    design = req_dir / "design.md"
    design.write_text("# 设计文档\n\n正文", encoding="utf-8")
    graph = DirectExecGraph.from_dict({
        "nodes": [{
            "id": "step_a",
            "label": "设计",
            "task": "写设计",
            "input_doc_paths": [
                "requirements/{requirement_id}/design.md",
            ],
            "executor": {"kind": "cli", "cli": {"commands": [{"command": "echo", "args": ["ok"]}]}},
        }],
        "edges": [
            {"from": "START", "to": "step_a", "condition": "always"},
            {"from": "step_a", "to": "END", "condition": "always"},
        ],
        "entry": "step_a",
    })
    doc = load_node_doc(
        workspace_path=str(ws),
        requirement_id="req1",
        graph=graph,
        node_id="step_a",
    )
    assert doc.generated is False
    assert "正文" in doc.content
    assert len(doc.workspace_refs) == 1
    assert doc.workspace_refs[0]["label"] == "输入"
    assert doc.workspace_refs[0]["exists"] is True
    assert doc.workspace_refs[0]["preview"] == "# 设计文档\n\n正文"


def test_load_node_doc_with_wildcard_input_path(tmp_path: Path):
    ws = tmp_path / "project"
    base = ws / "requirements" / "req1" / "feature_changes"
    (base / "feat-a").mkdir(parents=True)
    (base / "feat-a" / "需求分析.md").write_text("# 通配文档", encoding="utf-8")
    graph = DirectExecGraph.from_dict({
        "nodes": [{
            "id": "step_a",
            "label": "分析",
            "task": "分析",
            "input_doc_paths": [
                "requirements/{requirement_id}/feature_changes/{*}/需求分析.md",
            ],
            "executor": {"kind": "cli", "cli": {"commands": [{"command": "echo", "args": ["ok"]}]}},
        }],
        "edges": [
            {"from": "START", "to": "step_a", "condition": "always"},
            {"from": "step_a", "to": "END", "condition": "always"},
        ],
        "entry": "step_a",
    })
    doc = load_node_doc(
        workspace_path=str(ws),
        requirement_id="req1",
        graph=graph,
        node_id="step_a",
    )
    assert doc.generated is False
    assert "通配文档" in doc.content
    assert doc.workspace_refs[0]["kind"] == "glob"
    assert doc.workspace_refs[0]["match_count"] == 1


def test_load_node_doc_fallback_when_missing(tmp_path: Path):
    req_dir = tmp_path / "requirements" / "req1"
    req_dir.mkdir(parents=True)
    graph = _graph_with_node(task="编写单元测试")
    doc = load_node_doc(
        workspace_path=str(tmp_path),
        requirement_id="req1",
        graph=graph,
        node_id="step_a",
        node_output="ok",
    )
    assert doc.generated is True
    assert "编写单元测试" in doc.content
    assert "ok" in doc.content


def test_load_node_doc_unknown_node():
    graph = _graph_with_node()
    with pytest.raises(KeyError):
        load_node_doc(
            workspace_path="/tmp",
            requirement_id="req1",
            graph=graph,
            node_id="missing",
        )


def test_graph_migrates_legacy_workspace_refs_to_input_paths():
    graph = DirectExecGraph.from_dict({
        "nodes": [{
            "id": "step_a",
            "label": "设计",
            "doc_path": "requirements/{requirement_id}/legacy.md",
            "workspace_refs": [{"path": "requirements/{requirement_id}/other.md"}],
            "executor": {"kind": "cli", "cli": {"commands": [{"command": "echo", "args": ["ok"]}]}},
        }],
        "edges": [
            {"from": "START", "to": "step_a", "condition": "always"},
            {"from": "step_a", "to": "END", "condition": "always"},
        ],
        "entry": "step_a",
    })
    node = graph.nodes["step_a"]
    assert node.input_doc_paths == [
        "requirements/{requirement_id}/legacy.md",
        "requirements/{requirement_id}/other.md",
    ]
    assert node.output_doc_paths == []

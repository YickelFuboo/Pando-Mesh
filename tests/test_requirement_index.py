import pytest
import yaml
from app.workspace.requirement_index import build_requirement_tree, load_requirements_tree


@pytest.fixture
def req_workspace(tmp_path):
    ws = tmp_path / "project"
    req_root = ws / "requirements"
    ir_dir = req_root / "REQ-001-demo"
    ir_dir.mkdir(parents=True)
    (ir_dir / "requirement.yaml").write_text(
        yaml.safe_dump(
            {
                "ir_id": "REQ-001-demo",
                "title": "演示需求",
                "status": "decomposed",
                "scenarios": [
                    {
                        "sr_id": "SR-001",
                        "title": "场景一",
                        "status": "done",
                        "source_arch_changes": ["AR-001"],
                    }
                ],
                "architecture_changes": [
                    {
                        "ar_id": "AR-001",
                        "title": "架构变更一",
                        "status": "done",
                        "source_scenarios": ["SR-001"],
                        "repo_changes": [{"repo": "demo", "status": "done"}],
                    }
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return ws


def test_build_requirement_tree(req_workspace):
    ir_dir = req_workspace / "requirements" / "REQ-001-demo"
    tree = build_requirement_tree(ir_dir)
    assert tree["id"] == "REQ-001-demo"
    assert tree["name"] == "REQ-001: 演示需求"
    assert len(tree["children"]) == 2
    sr = next(n for n in tree["children"] if n["node_type"] == "scenario")
    ar = next(n for n in tree["children"] if n["node_type"] == "architecture")
    assert sr["sr_id"] == "SR-001"
    assert ar["children"][0]["repo"] == "demo"


def test_load_requirements_tree(req_workspace):
    payload = load_requirements_tree(str(req_workspace))
    root = payload["root"]
    assert root["id"] == "requirements_root"
    assert len(root["children"]) == 1
    assert root["children"][0]["name"] == "REQ-001: 演示需求"


def test_build_requirement_tree_from_md_files(tmp_path):
    ir_dir = tmp_path / "REQ-001-md"
    sr_dir = ir_dir / "feature_changes" / "demo-feature"
    ar_dir = ir_dir / "architecture_changes" / "AUSF"
    repo_dir = ir_dir / "repo_changes" / "ausf"
    sr_dir.mkdir(parents=True)
    ar_dir.mkdir(parents=True)
    repo_dir.mkdir(parents=True)
    (ir_dir / "需求描述.md").write_text(
        "---\nir_id: REQ-001-md\ntitle: MD 演示需求\nstatus: decomposed\n---\n# MD 演示需求\n",
        encoding="utf-8",
    )
    (ir_dir / "需求分析.md").write_text("# 需求分析\n", encoding="utf-8")
    (ir_dir / "需求质量检查.md").write_text("# 需求质量检查\n", encoding="utf-8")
    (sr_dir / "SR-001-scenario.md").write_text(
        "---\nsr_id: SR-001\nchange_type: new\nsource_arch_changes: [AR-001]\n---\n# 场景一\n",
        encoding="utf-8",
    )
    (ar_dir / "AR-001-arch.md").write_text(
        "---\nar_id: AR-001\nelement_id: ausf\nchange_type: modify\nsource_scenarios: [SR-001]\n---\n# 架构变更\n",
        encoding="utf-8",
    )
    (repo_dir / "implementation_design.md").write_text(
        "---\nrepo_name: ausf\nstatus: draft\n---\n# 实现设计\n",
        encoding="utf-8",
    )
    tree = build_requirement_tree(ir_dir)
    assert tree["has_index"] is True
    assert len(tree["docs"]) == 3
    assert tree["docs"][0]["md"] == "需求描述.md"
    assert len(tree["children"]) == 2
    sr = next(n for n in tree["children"] if n["node_type"] == "scenario")
    ar = next(n for n in tree["children"] if n["node_type"] == "architecture")
    assert sr["source_arch_changes"] == ["AR-001"]
    assert ar["source_scenarios"] == ["SR-001"]
    assert ar["children"][0]["repo"] == "ausf"

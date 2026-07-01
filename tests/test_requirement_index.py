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
    assert tree["name"] == "演示需求"
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
    assert root["children"][0]["name"] == "演示需求"

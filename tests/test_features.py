import pytest
import yaml
from app.workspace.features import load_features_tree


@pytest.fixture
def feature_workspace(tmp_path):
    ws = tmp_path / "project"
    feat = ws / "features"
    feat.mkdir(parents=True)
    (feat / "feature_root.yaml").write_text(
        yaml.safe_dump(
            {
                "meta": {"schema": "root_feature_index_v1", "stats": {"l1_count": 1}},
                "child_features": [
                    {
                        "id": "cat_a",
                        "name": "分类A",
                        "status": "partial",
                        "level": "L1",
                        "path": "cat_a/feature.yaml",
                    }
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    cat = feat / "cat_a"
    cat.mkdir()
    (cat / "feature.yaml").write_text(
        yaml.safe_dump(
            {
                "feature": {
                    "id": "cat_a",
                    "name": "分类A",
                    "level": "L1",
                    "status": "partial",
                },
                "child_features": [
                    {
                        "id": "feat_x",
                        "name": "特性X",
                        "status": "planned",
                        "level": "L2",
                        "path": "feat_x/feature.yaml",
                    }
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    leaf = cat / "feat_x"
    leaf.mkdir()
    (leaf / "feature.yaml").write_text(
        yaml.safe_dump(
            {
                "feature": {
                    "id": "feat_x",
                    "name": "特性X",
                    "level": "L2",
                    "status": "planned",
                },
                "child_features": [],
                "scenarios": [
                    {
                        "id": "SCENARIO_001",
                        "name": "成功场景",
                        "scenario_type": "成功场景",
                        "path": "SCENARIO_001.md",
                    }
                ],
                "traceability": {
                    "architecture_refs": [
                        {
                            "element_id": "smf",
                            "path": "architectures/logic_view/elements/smf/spec.md",
                        }
                    ],
                },
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    (leaf / "arch_ref.yaml").write_text(
        yaml.safe_dump(
            {
                "elements_used": [
                    {
                        "element_id": "smf",
                        "role": "相关架构元素",
                        "spec_path": "architectures/logic_view/elements/smf/spec.md",
                    },
                    {
                        "element_id": "upf",
                        "role": "相关架构元素",
                        "spec_path": "architectures/logic_view/elements/upf/spec.md",
                    },
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return ws


def test_load_features_tree(feature_workspace):
    payload = load_features_tree(str(feature_workspace))
    root = payload["root"]
    assert root["id"] == "feature_root"
    assert len(root["children"]) == 1
    l1 = root["children"][0]
    assert l1["id"] == "cat_a"
    assert len(l1["children"]) == 1
    l2 = l1["children"][0]
    assert l2["id"] == "feat_x"
    assert len(l2["children"]) == 1
    assert l2["children"][0]["node_type"] == "scenario"
    refs = {item["element_id"]: item for item in l2.get("architecture_refs") or []}
    assert set(refs) == {"smf", "upf"}
    assert refs["smf"]["role"] == "相关架构元素"

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from app.workspace.paths import normalize_workspace_path


def features_root(workspace_path: str) -> Path:
    ws = normalize_workspace_path(workspace_path)
    if not ws:
        raise ValueError("workspace_path 不能为空")
    root = Path(ws) / "features"
    if not root.is_dir():
        raise FileNotFoundError(f"features 目录不存在: {root}")
    return root


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _status_from(*sources: Any) -> str:
    for src in sources:
        if isinstance(src, dict):
            val = str(src.get("status") or "").strip()
            if val:
                return val
        elif isinstance(src, str) and src.strip():
            return src.strip()
    return "unknown"


def _feature_meta(entry: Dict[str, Any], feature: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    feat = feature or {}
    entry = entry or {}
    node_id = str(feat.get("id") or entry.get("id") or "").strip()
    name = str(feat.get("name") or entry.get("name") or node_id).strip()
    level = str(feat.get("level") or entry.get("level") or "").strip()
    description = str(feat.get("description") or entry.get("description") or "").strip()
    rel_path = str(entry.get("path") or feat.get("path") or "").strip()
    spec_path = str(feat.get("spec_path") or entry.get("spec_path") or "").strip()
    return {
        "id": node_id,
        "name": name,
        "level": level,
        "status": _status_from(feat, entry),
        "description": description,
        "path": rel_path.replace("\\", "/"),
        "spec_path": spec_path,
    }


def _scenario_nodes(feature_id: str, scenarios: List[Any], rel_prefix: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in scenarios or []:
        if not isinstance(item, dict):
            continue
        sid = str(item.get("id") or "").strip()
        if not sid:
            continue
        spath = str(item.get("path") or "").strip().replace("\\", "/")
        rel = f"{rel_prefix}/{spath}".strip("/") if spath else rel_prefix
        rows.append(
            {
                "id": f"{feature_id}::{sid}",
                "name": str(item.get("name") or sid).strip(),
                "level": "scenario",
                "status": "scenario",
                "description": str(item.get("description") or "").strip(),
                "path": rel,
                "node_type": "scenario",
                "scenario_type": str(item.get("scenario_type") or "").strip(),
                "children": [],
            }
        )
    return rows


def _build_from_yaml(yaml_path: Path, features_root_path: Path) -> Optional[Dict[str, Any]]:
    data = _load_yaml(yaml_path)
    if not data:
        return None
    feature = data.get("feature") if isinstance(data.get("feature"), dict) else {}
    rel_path = str(yaml_path.relative_to(features_root_path)).replace("\\", "/")
    meta = _feature_meta({"path": rel_path}, feature)
    if not meta["id"]:
        meta["id"] = yaml_path.parent.name
    meta["node_type"] = "feature"
    meta["path"] = rel_path

    children: List[Dict[str, Any]] = []
    parent_dir = yaml_path.parent
    for entry in data.get("child_features") or []:
        if not isinstance(entry, dict):
            continue
        child_rel = str(entry.get("path") or "").strip()
        if not child_rel:
            continue
        child_path = (parent_dir / child_rel).resolve()
        if not str(child_path).startswith(str(features_root_path.resolve())):
            continue
        child_node = _build_from_yaml(child_path, features_root_path)
        if child_node is not None:
            children.append(child_node)
        else:
            children.append(
                {
                    **_feature_meta(entry, None),
                    "node_type": "feature",
                    "children": [],
                }
            )

    scenarios = _scenario_nodes(meta["id"], data.get("scenarios") or [], str(yaml_path.parent.relative_to(features_root_path)).replace("\\", "/"))
    children.extend(scenarios)
    meta["children"] = children
    return meta


def load_features_tree(workspace_path: str) -> Dict[str, Any]:
    root_dir = features_root(workspace_path)
    index_path = root_dir / "feature_root.yaml"
    if not index_path.is_file():
        raise FileNotFoundError(f"未找到 feature_root.yaml: {index_path}")

    index = _load_yaml(index_path)
    meta = index.get("meta") if isinstance(index.get("meta"), dict) else {}
    stats = meta.get("stats") if isinstance(meta.get("stats"), dict) else {}

    children: List[Dict[str, Any]] = []
    for entry in index.get("child_features") or []:
        if not isinstance(entry, dict):
            continue
        child_rel = str(entry.get("path") or "").strip()
        if not child_rel:
            continue
        child_path = (root_dir / child_rel).resolve()
        if not str(child_path).startswith(str(root_dir.resolve())):
            continue
        child_node = _build_from_yaml(child_path, root_dir)
        if child_node is not None:
            children.append(child_node)
        else:
            children.append(
                {
                    **_feature_meta(entry, None),
                    "node_type": "category",
                    "children": [],
                }
            )

    return {
        "root": {
            "id": "feature_root",
            "name": "ROOT",
            "level": "root",
            "status": "root",
            "description": str(meta.get("scope") or "特性库根索引").strip(),
            "path": "feature_root.yaml",
            "node_type": "root",
            "children": children,
        },
        "stats": stats,
        "features_path": str(root_dir),
    }

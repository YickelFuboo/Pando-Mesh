from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from app.workspace.paths import normalize_workspace_path

_YAML_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_TREE_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}


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
    cache_key = str(path.resolve())
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return {}
    cached = _YAML_CACHE.get(cache_key)
    if cached and cached[0] == mtime:
        return cached[1]
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        data: Dict[str, Any] = {}
    else:
        data = raw if isinstance(raw, dict) else {}
    _YAML_CACHE[cache_key] = (mtime, data)
    return data


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


def _normalize_arch_ref_item(item: Any) -> Optional[Dict[str, str]]:
    if not isinstance(item, dict):
        return None
    element_id = str(item.get("element_id") or "").strip()
    if not element_id:
        return None
    path = str(item.get("path") or item.get("spec_path") or "").strip().replace("\\", "/")
    name = str(item.get("name") or item.get("element_name") or element_id).strip()
    role = str(item.get("role") or "").strip()
    row: Dict[str, str] = {
        "element_id": element_id,
        "path": path,
        "name": name,
    }
    if role:
        row["role"] = role
    return row


def _architecture_refs(
    data: Dict[str, Any],
    yaml_dir: Path,
    feature: Dict[str, Any],
) -> List[Dict[str, str]]:
    merged: Dict[str, Dict[str, str]] = {}
    trace = data.get("traceability") if isinstance(data.get("traceability"), dict) else {}
    for item in trace.get("architecture_refs") or []:
        row = _normalize_arch_ref_item(item)
        if row:
            merged[row["element_id"]] = row

    arch_ref_name = str(feature.get("arch_ref_path") or "arch_ref.yaml").strip()
    if arch_ref_name:
        arch_ref_file = yaml_dir / arch_ref_name
        arch_data = _load_yaml(arch_ref_file) if arch_ref_file.is_file() else {}
        for item in arch_data.get("elements_used") or []:
            row = _normalize_arch_ref_item(item)
            if not row:
                continue
            existing = merged.get(row["element_id"], {})
            merged[row["element_id"]] = {**existing, **{k: v for k, v in row.items() if v}}

    return list(merged.values())


def _build_from_yaml(
    yaml_path: Path,
    features_root_path: Path,
    *,
    root_resolved: str,
) -> Optional[Dict[str, Any]]:
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
        if not str(child_path).startswith(root_resolved):
            continue
        child_node = _build_from_yaml(
            child_path,
            features_root_path,
            root_resolved=root_resolved,
        )
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

    rel_prefix = str(yaml_path.parent.relative_to(features_root_path)).replace("\\", "/")
    scenarios = _scenario_nodes(meta["id"], data.get("scenarios") or [], rel_prefix)
    children.extend(scenarios)
    meta["architecture_refs"] = _architecture_refs(data, parent_dir, feature)
    meta["children"] = children
    return meta


def _tree_cache_stamp(root_dir: Path) -> float:
    index_path = root_dir / "feature_root.yaml"
    try:
        return index_path.stat().st_mtime
    except OSError:
        return 0.0


def _load_features_tree_uncached(workspace_path: str) -> Dict[str, Any]:
    root_dir = features_root(workspace_path)
    index_path = root_dir / "feature_root.yaml"
    if not index_path.is_file():
        raise FileNotFoundError(f"未找到 feature_root.yaml: {index_path}")

    index = _load_yaml(index_path)
    meta = index.get("meta") if isinstance(index.get("meta"), dict) else {}
    stats = meta.get("stats") if isinstance(meta.get("stats"), dict) else {}
    root_resolved = str(root_dir.resolve())

    children: List[Dict[str, Any]] = []
    for entry in index.get("child_features") or []:
        if not isinstance(entry, dict):
            continue
        child_rel = str(entry.get("path") or "").strip()
        if not child_rel:
            continue
        child_path = (root_dir / child_rel).resolve()
        if not str(child_path).startswith(root_resolved):
            continue
        child_node = _build_from_yaml(
            child_path,
            root_dir,
            root_resolved=root_resolved,
        )
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


def load_features_tree(workspace_path: str) -> Dict[str, Any]:
    root_dir = features_root(workspace_path)
    cache_key = str(root_dir.resolve())
    stamp = _tree_cache_stamp(root_dir)
    cached = _TREE_CACHE.get(cache_key)
    if cached and cached[0] == stamp:
        return cached[1]
    payload = _load_features_tree_uncached(workspace_path)
    _TREE_CACHE[cache_key] = (stamp, payload)
    return payload


def clear_features_tree_cache(workspace_path: str = "") -> None:
    if not workspace_path.strip():
        _TREE_CACHE.clear()
        _YAML_CACHE.clear()
        return
    try:
        root_dir = features_root(workspace_path)
    except (ValueError, FileNotFoundError):
        return
    cache_key = str(root_dir.resolve())
    _TREE_CACHE.pop(cache_key, None)
    prefix = cache_key + "\\"
    prefix_posix = cache_key + "/"
    for key in list(_YAML_CACHE):
        if key.startswith(prefix) or key.startswith(prefix_posix):
            _YAML_CACHE.pop(key, None)

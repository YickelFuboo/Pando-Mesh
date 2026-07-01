from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from app.workspace.paths import normalize_workspace_path


VIEW_LABELS = {
    "logic_view": "逻辑视图",
}


def architectures_root(workspace_path: str) -> Path:
    ws = normalize_workspace_path(workspace_path)
    if not ws:
        raise ValueError("workspace_path 不能为空")
    root = Path(ws) / "architectures"
    if not root.is_dir():
        raise FileNotFoundError(f"architectures 目录不存在: {root}")
    return root


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _view_label(view_id: str) -> str:
    key = str(view_id or "").strip()
    return VIEW_LABELS.get(key, key.replace("_", " ").title() or key)


def _element_node(view_id: str, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(item, dict):
        return None
    element_id = str(item.get("element_id") or item.get("element_name") or "").strip()
    if not element_id:
        return None
    spec_path = str(item.get("spec_path") or "").strip().replace("\\", "/")
    repo_path = str(item.get("repo_path") or "").strip().replace("\\", "/")
    depends_on = [str(x).strip() for x in (item.get("depends_on") or []) if str(x).strip()]
    depended_by = [str(x).strip() for x in (item.get("depended_by") or []) if str(x).strip()]
    return {
        "id": f"{view_id}::{element_id}",
        "element_id": element_id,
        "name": str(item.get("element_name") or element_id).strip(),
        "level": "element",
        "status": str(item.get("confidence") or item.get("element_type") or "element").strip(),
        "description": str(item.get("note") or "").strip(),
        "path": spec_path,
        "spec_path": spec_path,
        "repo_path": repo_path,
        "element_type": str(item.get("element_type") or "").strip(),
        "confidence": str(item.get("confidence") or "").strip(),
        "depends_on": depends_on,
        "depended_by": depended_by,
        "node_type": "element",
        "children": [],
    }


def _view_node(view_dir: Path, arch_root: Path) -> Optional[Dict[str, Any]]:
    view_id = view_dir.name
    elements_tree = view_dir / "elements_tree.yaml"
    children: List[Dict[str, Any]] = []
    meta: Dict[str, Any] = {}
    if elements_tree.is_file():
        data = _load_yaml(elements_tree)
        tree_meta = data.get("tree_meta") if isinstance(data.get("tree_meta"), dict) else {}
        meta = tree_meta
        for item in data.get("elements") or []:
            node = _element_node(view_id, item)
            if node is not None:
                children.append(node)
    if not children and not any(view_dir.iterdir()):
        return None
    children.sort(key=lambda row: str(row.get("name") or row.get("element_id") or "").lower())
    rel = str(view_dir.relative_to(arch_root.parent)).replace("\\", "/")
    return {
        "id": f"arch_view_{view_id}",
        "view_id": view_id,
        "name": _view_label(view_id),
        "level": "view",
        "status": "view",
        "description": str(meta.get("note") or f"{view_id} 架构视图").strip(),
        "path": rel,
        "element_count": len(children),
        "node_type": "view",
        "children": children,
    }


def load_architectures_tree(workspace_path: str) -> Dict[str, Any]:
    root_dir = architectures_root(workspace_path)
    children: List[Dict[str, Any]] = []

    system_doc_path = "architectures/system_architectures.md"
    has_system_doc = (root_dir / "system_architectures.md").is_file()

    for entry in sorted(root_dir.iterdir(), key=lambda p: p.name.lower()):
        if not entry.is_dir():
            continue
        view_node = _view_node(entry, root_dir)
        if view_node is not None:
            children.append(view_node)

    return {
        "root": {
            "id": "architectures_root",
            "name": "系统架构",
            "level": "root",
            "status": "root",
            "description": "系统级架构设计文档",
            "path": system_doc_path if has_system_doc else "architectures/",
            "spec_path": system_doc_path if has_system_doc else "",
            "node_type": "root",
            "children": children,
        },
        "architectures_path": str(root_dir),
    }

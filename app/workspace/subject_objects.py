from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from app.session.subject_schema import (
    SUBJECT_TYPE_ARCH_ELEMENT,
    SUBJECT_TYPE_AR,
    SUBJECT_TYPE_FEATURE,
    SUBJECT_TYPE_IR,
    SUBJECT_TYPE_REPO,
    SUBJECT_TYPE_SR,
    SUBJECT_TYPE_WORKSPACE,
    normalize_subject_type,
)
from app.workspace.architectures import load_architectures_tree
from app.workspace.features import load_features_tree
from app.workspace.paths import normalize_workspace_path
from app.workspace.requirement_index import build_requirement_tree
from app.workspace.requirements import list_requirements, requirements_root


def _object_row(
    *,
    object_id: str,
    label: str,
    subject_kind: str,
    subject_granularity: str,
    subject_id: str,
    subject_refs: Dict[str, str] | None = None,
    summary: str = "",
) -> Dict[str, Any]:
    return {
        "object_id": object_id,
        "label": label,
        "summary": summary,
        "subject_kind": subject_kind,
        "subject_granularity": subject_granularity,
        "subject_id": subject_id,
        "subject_refs": dict(subject_refs or {}),
    }


def _flatten_feature_nodes(nodes: List[Dict[str, Any]], rows: List[Dict[str, Any]]) -> None:
    for node in nodes or []:
        if not isinstance(node, dict):
            continue
        node_type = str(node.get("node_type") or "").strip().lower()
        children = node.get("children") if isinstance(node.get("children"), list) else []
        node_id = str(node.get("id") or "").strip()
        name = str(node.get("name") or node_id).strip()
        spec_path = str(node.get("spec_path") or node.get("path") or "").strip()
        if node_type in {"feature", "scenario", "category"} and node_id and node_id != "feature_root":
            rows.append(
                _object_row(
                    object_id=node_id,
                    label=name,
                    summary=str(node.get("description") or "").strip(),
                    subject_kind="feature",
                    subject_granularity="feature",
                    subject_id=node_id,
                    subject_refs={
                        "feature_id": node_id,
                        "feature_path": spec_path,
                        "feature_name": name,
                    },
                )
            )
        if children:
            _flatten_feature_nodes(children, rows)


def _flatten_arch_nodes(nodes: List[Dict[str, Any]], rows: List[Dict[str, Any]]) -> None:
    for node in nodes or []:
        if not isinstance(node, dict):
            continue
        children = node.get("children") if isinstance(node.get("children"), list) else []
        node_type = str(node.get("node_type") or "").strip().lower()
        if node_type == "element":
            element_id = str(node.get("element_id") or node.get("id") or "").strip()
            spec_path = str(node.get("spec_path") or node.get("path") or "").strip()
            name = str(node.get("name") or element_id).strip()
            object_id = str(node.get("id") or element_id).strip()
            rows.append(
                _object_row(
                    object_id=object_id,
                    label=name,
                    summary=str(node.get("description") or "").strip(),
                    subject_kind="arch_element",
                    subject_granularity="arch_element",
                    subject_id=element_id,
                    subject_refs={
                        "element_id": element_id,
                        "element_path": spec_path,
                        "spec_path": spec_path,
                    },
                )
            )
        if children:
            _flatten_arch_nodes(children, rows)


def _list_workspace_repos(workspace_path: str) -> List[Dict[str, Any]]:
    ws = normalize_workspace_path(workspace_path)
    root = Path(ws) / "repos"
    if not root.is_dir():
        return []
    rows: List[Dict[str, Any]] = []
    for entry in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        repo_name = entry.name
        rows.append(
            _object_row(
                object_id=repo_name,
                label=repo_name,
                subject_kind="repo",
                subject_granularity="repo",
                subject_id=repo_name,
                subject_refs={"repo_id": repo_name, "repo_name": repo_name},
            )
        )
    return rows


def list_subject_objects(workspace_path: str, subject_type: str) -> List[Dict[str, Any]]:
    ws = normalize_workspace_path(workspace_path)
    if not ws:
        raise ValueError("workspace_path 不能为空")
    kind = normalize_subject_type(subject_type)
    if kind == SUBJECT_TYPE_WORKSPACE:
        return [
            _object_row(
                object_id="_workspace_",
                label="Workspace 任务",
                summary=ws,
                subject_kind="workspace",
                subject_granularity="workspace",
                subject_id="",
                subject_refs={},
            )
        ]
    if kind == SUBJECT_TYPE_FEATURE:
        tree = load_features_tree(ws)
        root = tree.get("root") if isinstance(tree.get("root"), dict) else {}
        rows: List[Dict[str, Any]] = []
        _flatten_feature_nodes(root.get("children") or [], rows)
        return rows
    if kind == SUBJECT_TYPE_ARCH_ELEMENT:
        tree = load_architectures_tree(ws)
        root = tree.get("root") if isinstance(tree.get("root"), dict) else {}
        rows = []
        _flatten_arch_nodes(root.get("children") or [], rows)
        return rows
    if kind == SUBJECT_TYPE_REPO:
        return _list_workspace_repos(ws)
    if kind == SUBJECT_TYPE_IR:
        return [
            _object_row(
                object_id=item.requirement_id,
                label=item.title or item.name or item.requirement_id,
                summary=item.summary,
                subject_kind="requirement",
                subject_granularity="ir",
                subject_id=item.requirement_id,
                subject_refs={"requirement_id": item.requirement_id},
            )
            for item in list_requirements(ws)
        ]
    root_dir = requirements_root(ws)
    rows = []
    for entry in sorted(root_dir.iterdir(), key=lambda p: p.name.lower()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        tree = build_requirement_tree(entry)
        ir_id = str(tree.get("id") or entry.name).strip()
        for child in tree.get("children") or []:
            if not isinstance(child, dict):
                continue
            level = str(child.get("level") or "").strip().upper()
            if kind == SUBJECT_TYPE_SR and level != "SR":
                continue
            if kind == SUBJECT_TYPE_AR and level != "AR":
                continue
            child_id = str(child.get("id") or "").strip()
            name = str(child.get("name") or child_id).strip()
            md = str(child.get("md") or "").strip()
            if kind == SUBJECT_TYPE_SR:
                sr_id = str(child.get("sr_id") or "").strip()
                if not sr_id:
                    continue
                object_id = child_id or f"{ir_id}::{sr_id}"
                rows.append(
                    _object_row(
                        object_id=object_id,
                        label=f"{sr_id} · {name}",
                        summary=ir_id,
                        subject_kind="requirement",
                        subject_granularity="sr",
                        subject_id=object_id,
                        subject_refs={
                            "requirement_id": ir_id,
                            "sr_id": sr_id,
                            "sr_doc": f"requirements/{ir_id}/{md}" if md else "",
                        },
                    )
                )
            elif kind == SUBJECT_TYPE_AR:
                ar_id = str(child.get("ar_id") or "").strip()
                if not ar_id:
                    continue
                object_id = child_id or f"{ir_id}::{ar_id}"
                rows.append(
                    _object_row(
                        object_id=object_id,
                        label=f"{ar_id} · {name}",
                        summary=ir_id,
                        subject_kind="requirement",
                        subject_granularity="ar",
                        subject_id=object_id,
                        subject_refs={
                            "requirement_id": ir_id,
                            "ar_id": ar_id,
                            "ar_doc": f"requirements/{ir_id}/{md}" if md else "",
                        },
                    )
                )
    return rows

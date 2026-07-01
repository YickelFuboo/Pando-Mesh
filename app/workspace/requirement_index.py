from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from app.workspace.paths import normalize_workspace_path
from app.workspace.requirements import requirements_root


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _read_frontmatter(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    try:
        meta = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return {}
    return meta if isinstance(meta, dict) else {}


def _first_markdown_title(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip()[:200]
    return ""


def read_requirement_meta(req_dir: Path) -> Dict[str, Any]:
    yaml_path = req_dir / "requirement.yaml"
    if yaml_path.is_file():
        data = _load_yaml(yaml_path)
        if data:
            data.setdefault("ir_id", req_dir.name)
            return data
    for name in ("需求描述.md", "README.md", "requirement.md"):
        md_path = req_dir / name
        if not md_path.is_file():
            continue
        meta = _read_frontmatter(md_path)
        if meta:
            meta.setdefault("ir_id", meta.get("requirement_id") or req_dir.name)
            meta.setdefault("title", _first_markdown_title(md_path) or req_dir.name)
            return meta
        title = _first_markdown_title(md_path)
        if title:
            return {
                "ir_id": req_dir.name,
                "title": title,
                "status": "raw",
            }
    return {
        "ir_id": req_dir.name,
        "title": req_dir.name,
        "status": "unknown",
    }


def _node_base(node_id: str, name: str, level: str, status: str, node_type: str, **extra: Any) -> Dict[str, Any]:
    row = {
        "id": node_id,
        "name": name,
        "level": level,
        "status": status or "unknown",
        "node_type": node_type,
        "description": str(extra.pop("description", "") or ""),
        "children": [],
    }
    row.update(extra)
    return row


def build_requirement_tree(req_dir: Path) -> Dict[str, Any]:
    meta = read_requirement_meta(req_dir)
    ir_id = str(meta.get("ir_id") or req_dir.name).strip()
    title = str(meta.get("title") or ir_id).strip()
    status = str(meta.get("status") or "unknown").strip()

    root = _node_base(
        ir_id,
        title,
        "IR",
        status,
        "requirement",
        path=str(req_dir.name),
        has_index=bool((req_dir / "requirement.yaml").is_file()),
    )

    children: List[Dict[str, Any]] = []
    for sr in meta.get("scenarios") or []:
        if not isinstance(sr, dict):
            continue
        sr_id = str(sr.get("sr_id") or "").strip()
        if not sr_id:
            continue
        children.append(
            _node_base(
                f"{ir_id}::{sr_id}",
                str(sr.get("title") or sr_id).strip(),
                "SR",
                str(sr.get("status") or "").strip(),
                "scenario",
                sr_id=sr_id,
                feature=str(sr.get("feature") or "").strip(),
                change_type=str(sr.get("change_type") or "").strip(),
                md=str(sr.get("md") or "").strip(),
                source_arch_changes=[str(x) for x in (sr.get("source_arch_changes") or [])],
            )
        )

    for ar in meta.get("architecture_changes") or []:
        if not isinstance(ar, dict):
            continue
        ar_id = str(ar.get("ar_id") or "").strip()
        if not ar_id:
            continue
        ar_node = _node_base(
            f"{ir_id}::{ar_id}",
            str(ar.get("title") or ar_id).strip(),
            "AR",
            str(ar.get("status") or "").strip(),
            "architecture",
            ar_id=ar_id,
            element=str(ar.get("element") or "").strip(),
            change_type=str(ar.get("change_type") or "").strip(),
            md=str(ar.get("md") or "").strip(),
            source_scenarios=[str(x) for x in (ar.get("source_scenarios") or [])],
        )
        for repo in ar.get("repo_changes") or []:
            if not isinstance(repo, dict):
                continue
            repo_name = str(repo.get("repo") or "").strip()
            if not repo_name:
                continue
            ar_node["children"].append(
                _node_base(
                    f"{ir_id}::{ar_id}::{repo_name}",
                    repo_name,
                    "REPO",
                    str(repo.get("status") or "").strip(),
                    "repo",
                    repo=repo_name,
                    md=str(repo.get("md") or "").strip(),
                )
            )
        children.append(ar_node)

    root["children"] = children
    return root


def load_requirements_tree(workspace_path: str) -> Dict[str, Any]:
    root_dir = requirements_root(workspace_path)
    children: List[Dict[str, Any]] = []
    for entry in sorted(root_dir.iterdir(), key=lambda p: p.name.lower()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        children.append(build_requirement_tree(entry))

    return {
        "root": {
            "id": "requirements_root",
            "name": "Requirements",
            "level": "root",
            "status": "root",
            "node_type": "root",
            "description": "Workspace 需求目录索引",
            "path": "requirements/",
            "children": children,
        },
        "requirements_path": str(root_dir),
    }

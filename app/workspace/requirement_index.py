from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from app.workspace.paths import normalize_workspace_path
from app.workspace.requirements import requirements_root

SR_FILE_RE = re.compile(r"^SR-(\d+)", re.IGNORECASE)
AR_FILE_RE = re.compile(r"^AR-(\d+)", re.IGNORECASE)


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


def _rel_md_path(req_dir: Path, file_path: Path) -> str:
    return str(file_path.relative_to(req_dir)).replace("\\", "/")


def _id_from_filename(path: Path, pattern: re.Pattern[str], prefix: str) -> str:
    match = pattern.match(path.stem)
    if not match:
        return ""
    return f"{prefix}-{match.group(1)}"


def _normalize_str_list(value: Any) -> List[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _short_req_id(ir_id: str) -> str:
    match = re.match(r"^(REQ-\d+)", str(ir_id or "").strip(), re.IGNORECASE)
    return match.group(1).upper() if match else ""


def _format_ir_display_name(ir_id: str, title: str) -> str:
    name = str(title or ir_id).strip()
    short_id = _short_req_id(ir_id)
    if not short_id:
        return name
    prefix = short_id.lower()
    normalized = name.lower()
    if normalized.startswith(prefix):
        return name
    if normalized.startswith(f"{prefix}:") or normalized.startswith(f"{prefix}："):
        return name
    return f"{short_id}: {name}"


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


def _scan_sr_nodes(req_dir: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    feature_root = req_dir / "feature_changes"
    if not feature_root.is_dir():
        return rows
    for md_path in sorted(feature_root.rglob("SR-*.md")):
        if not md_path.is_file():
            continue
        sr_id = _id_from_filename(md_path, SR_FILE_RE, "SR")
        if not sr_id:
            continue
        meta = _read_frontmatter(md_path)
        feature_parts = []
        feature_name = str(meta.get("feature_name") or "").strip()
        subfeature_name = str(meta.get("subfeature_name") or "").strip()
        if feature_name and subfeature_name:
            feature_parts = [feature_name, subfeature_name]
        elif feature_name:
            feature_parts = [feature_name]
        rows.append(
            {
                "sr_id": sr_id,
                "title": _first_markdown_title(md_path) or md_path.stem,
                "status": str(meta.get("status") or meta.get("change_type") or "").strip(),
                "feature": "/".join(feature_parts),
                "change_type": str(meta.get("change_type") or "").strip(),
                "md": _rel_md_path(req_dir, md_path),
                "source_arch_changes": _normalize_str_list(meta.get("source_arch_changes")),
            }
        )
    rows.sort(key=lambda row: row["sr_id"])
    return rows


def _scan_ar_nodes(req_dir: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    arch_root = req_dir / "architecture_changes"
    if not arch_root.is_dir():
        return rows
    for md_path in sorted(arch_root.rglob("AR-*.md")):
        if not md_path.is_file():
            continue
        ar_id = _id_from_filename(md_path, AR_FILE_RE, "AR")
        if not ar_id:
            continue
        meta = _read_frontmatter(md_path)
        rows.append(
            {
                "ar_id": ar_id,
                "title": _first_markdown_title(md_path) or md_path.stem,
                "status": str(meta.get("status") or meta.get("change_type") or "").strip(),
                "element": str(meta.get("element_id") or meta.get("element_name") or "").strip(),
                "change_type": str(meta.get("change_type") or "").strip(),
                "md": _rel_md_path(req_dir, md_path),
                "source_scenarios": _normalize_str_list(meta.get("source_scenarios")),
                "repo_changes": [],
            }
        )
    rows.sort(key=lambda row: row["ar_id"])
    return rows


def _scan_repo_nodes(req_dir: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    repo_root = req_dir / "repo_changes"
    if not repo_root.is_dir():
        return rows
    for md_path in sorted(repo_root.rglob("*.md")):
        if not md_path.is_file():
            continue
        meta = _read_frontmatter(md_path)
        repo_name = str(meta.get("repo_name") or md_path.parent.name or "").strip()
        if not repo_name:
            continue
        rows.append(
            {
                "repo": repo_name,
                "status": str(meta.get("status") or "").strip(),
                "md": _rel_md_path(req_dir, md_path),
            }
        )
    return rows


def _attach_repo_changes(ar_rows: List[Dict[str, Any]], repo_rows: List[Dict[str, Any]]) -> None:
    if not ar_rows or not repo_rows:
        return
    by_element = {str(row.get("element") or "").strip().lower(): row for row in ar_rows}
    for repo in repo_rows:
        key = str(repo.get("repo") or "").strip().lower()
        target = by_element.get(key)
        if target is not None:
            target.setdefault("repo_changes", []).append(repo)


_IR_DOC_PRIORITY = (
    "需求描述.md",
    "需求分析.md",
    "需求质量检查.md",
)


def _scan_ir_docs(req_dir: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    seen: set[str] = set()
    for name in _IR_DOC_PRIORITY:
        path = req_dir / name
        if not path.is_file():
            continue
        rows.append({"label": path.stem, "md": name})
        seen.add(name)
    for path in sorted(req_dir.glob("*.md")):
        if path.name in seen:
            continue
        rows.append({"label": path.stem, "md": path.name})
        seen.add(path.name)
    return rows


def has_decomposed_index(req_dir: Path) -> bool:
    if (req_dir / "requirement.yaml").is_file():
        return True
    feature_root = req_dir / "feature_changes"
    arch_root = req_dir / "architecture_changes"
    if feature_root.is_dir() and any(feature_root.rglob("SR-*.md")):
        return True
    if arch_root.is_dir() and any(arch_root.rglob("AR-*.md")):
        return True
    return False


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

    sr_rows = _scan_sr_nodes(req_dir)
    ar_rows = _scan_ar_nodes(req_dir)
    if not sr_rows and meta.get("scenarios"):
        sr_rows = [row for row in meta.get("scenarios") or [] if isinstance(row, dict)]
    if not ar_rows and meta.get("architecture_changes"):
        ar_rows = [row for row in meta.get("architecture_changes") or [] if isinstance(row, dict)]
    elif ar_rows:
        _attach_repo_changes(ar_rows, _scan_repo_nodes(req_dir))

    ir_docs = _scan_ir_docs(req_dir)

    root = _node_base(
        ir_id,
        _format_ir_display_name(ir_id, title),
        "IR",
        status,
        "requirement",
        path=str(req_dir.name),
        md=str(ir_docs[0]["md"]) if ir_docs else "",
        docs=ir_docs,
        has_index=has_decomposed_index(req_dir),
    )

    children: List[Dict[str, Any]] = []
    for sr in sr_rows:
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
                source_arch_changes=_normalize_str_list(sr.get("source_arch_changes")),
            )
        )

    for ar in ar_rows:
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
            source_scenarios=_normalize_str_list(ar.get("source_scenarios")),
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

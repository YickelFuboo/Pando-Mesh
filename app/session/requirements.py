import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass(frozen=True)
class RequirementItem:
    requirement_id: str
    name: str
    path: str
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "requirement_id": self.requirement_id,
            "name": self.name,
            "path": self.path,
            "summary": self.summary,
        }


def normalize_workspace_path(workspace_path: str) -> str:
    raw = str(workspace_path or "").strip()
    if not raw:
        return ""
    return str(Path(raw).expanduser().resolve())


def requirements_root(workspace_path: str) -> Path:
    ws = normalize_workspace_path(workspace_path)
    if not ws:
        raise ValueError("workspace_path 不能为空")
    root = Path(ws) / "requirements"
    if not root.is_dir():
        raise FileNotFoundError(f"requirements 目录不存在: {root}")
    return root


def _read_summary(req_dir: Path) -> str:
    for name in ("README.md", "readme.md", "requirement.md", "goal.txt", "spec.md"):
        path = req_dir / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if text:
            first = text.splitlines()[0].strip().lstrip("#").strip()
            return first[:200]
    return ""


def list_requirements(workspace_path: str) -> List[RequirementItem]:
    root = requirements_root(workspace_path)
    items: List[RequirementItem] = []
    for entry in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if not entry.is_dir():
            continue
        if entry.name.startswith("."):
            continue
        items.append(
            RequirementItem(
                requirement_id=entry.name,
                name=entry.name,
                path=str(entry.resolve()),
                summary=_read_summary(entry),
            )
        )
    return items


def requirement_path(workspace_path: str, requirement_id: str) -> Path:
    rid = str(requirement_id or "").strip()
    if not rid or rid in {".", ".."} or "/" in rid or "\\" in rid:
        raise ValueError("requirement_id 无效")
    root = requirements_root(workspace_path)
    path = (root / rid).resolve()
    if not str(path).startswith(str(root.resolve())):
        raise ValueError("requirement_id 无效")
    if not path.is_dir():
        raise FileNotFoundError(f"需求目录不存在: {path}")
    return path


def paths_equal(a: str, b: str) -> bool:
    na = normalize_workspace_path(a)
    nb = normalize_workspace_path(b)
    if not na or not nb:
        return na == nb
    if os.name == "nt":
        return na.casefold() == nb.casefold()
    return na == nb

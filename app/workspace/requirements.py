from dataclasses import dataclass
from pathlib import Path
from typing import List

from app.workspace.paths import normalize_workspace_path


@dataclass(frozen=True)
class RequirementItem:
    requirement_id: str
    name: str
    path: str
    summary: str = ""
    title: str = ""
    status: str = ""
    has_index: bool = False

    def to_dict(self) -> dict:
        return {
            "requirement_id": self.requirement_id,
            "name": self.name,
            "path": self.path,
            "summary": self.summary,
            "title": self.title or self.summary or self.name,
            "status": self.status,
            "has_index": self.has_index,
        }


def requirements_root(workspace_path: str) -> Path:
    ws = normalize_workspace_path(workspace_path)
    if not ws:
        raise ValueError("workspace_path 不能为空")
    root = Path(ws) / "requirements"
    if not root.is_dir():
        raise FileNotFoundError(f"requirements 目录不存在: {root}")
    return root


def _read_summary(req_dir: Path) -> str:
    from app.workspace.requirement_index import read_requirement_meta

    meta = read_requirement_meta(req_dir)
    title = str(meta.get("title") or "").strip()
    if title:
        return title[:200]
    for name in ("README.md", "readme.md", "requirement.md", "goal.txt", "spec.md", "需求描述.md"):
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
    from app.workspace.requirement_index import read_requirement_meta

    root = requirements_root(workspace_path)
    items: List[RequirementItem] = []
    for entry in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if not entry.is_dir():
            continue
        if entry.name.startswith("."):
            continue
        meta = read_requirement_meta(entry)
        summary = _read_summary(entry)
        title = str(meta.get("title") or summary or entry.name).strip()
        items.append(
            RequirementItem(
                requirement_id=entry.name,
                name=title,
                path=str(entry.resolve()),
                summary=summary,
                title=title,
                status=str(meta.get("status") or "").strip(),
                has_index=(entry / "requirement.yaml").is_file(),
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

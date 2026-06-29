import re
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern
from app.session.requirements import normalize_workspace_path, requirement_path
_TEXT_SUFFIXES = {
    ".md", ".markdown", ".txt", ".json", ".yaml", ".yml", ".xml",
    ".html", ".htm", ".csv", ".log", ".py", ".js", ".ts", ".vue",
    ".java", ".go", ".rs", ".c", ".cpp", ".h", ".sql", ".sh", ".ps1",
}
_PREVIEW_MAX_BYTES = 65536
_DIR_LIST_LIMIT = 40
_PATH_WILDCARD = "{*}"
_REGEX_SEGMENT_PREFIX = "{re:"
_GLOB_MATCH_LIMIT = 64


@dataclass(frozen=True)
class NodeWorkspaceRef:
    path: str
    label: str = ""

    def to_dict(self) -> Dict[str, str]:
        payload: Dict[str, str] = {"path": self.path}
        if self.label:
            payload["label"] = self.label
        return payload


def parse_doc_path_list(raw: Any) -> List[str]:
    """解析文档路径列表（字符串数组或 workspace_refs 形态）。"""
    if not isinstance(raw, list):
        return []
    paths: List[str] = []
    seen: set[str] = set()
    for item in raw:
        path = ""
        if isinstance(item, str):
            path = str(item or "").strip()
        elif isinstance(item, dict):
            path = str(item.get("path") or "").strip()
        if not path or path in seen:
            continue
        seen.add(path)
        paths.append(path)
    return paths


def normalize_node_doc_path_lists(
    *,
    doc_path: str = "",
    workspace_refs: Optional[List[NodeWorkspaceRef]] = None,
    input_doc_paths: Any = None,
    output_doc_paths: Any = None,
) -> tuple[List[str], List[str]]:
    """解析 input/output 文档路径；无新字段时将历史 doc_path/workspace_refs 归入输入。"""
    inp = parse_doc_path_list(input_doc_paths)
    out = parse_doc_path_list(output_doc_paths)
    if inp or out:
        return inp, out
    legacy = normalize_node_doc_refs(doc_path, workspace_refs or [])
    return [ref.path for ref in legacy], []


def normalize_node_doc_refs(
    doc_path: str,
    workspace_refs: List[NodeWorkspaceRef],
) -> List[NodeWorkspaceRef]:
    """合并历史 doc_path 与 workspace_refs，去重并保持顺序。"""
    merged: List[NodeWorkspaceRef] = []
    seen: set[str] = set()
    primary = str(doc_path or "").strip()
    if primary:
        seen.add(primary)
        merged.append(NodeWorkspaceRef(path=primary))
    for ref in workspace_refs or []:
        path = str(ref.path or "").strip()
        if not path or path in seen:
            continue
        seen.add(path)
        label = str(ref.label or "").strip()
        merged.append(NodeWorkspaceRef(path=path, label=label))
    return merged


def parse_workspace_refs(raw: Any) -> List[NodeWorkspaceRef]:
    if not isinstance(raw, list):
        return []
    refs: List[NodeWorkspaceRef] = []
    for item in raw:
        if isinstance(item, str):
            path = str(item or "").strip()
            if path:
                refs.append(NodeWorkspaceRef(path=path))
            continue
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "").strip()
        if not path:
            continue
        label = str(item.get("label") or "").strip()
        refs.append(NodeWorkspaceRef(path=path, label=label))
    return refs


def expand_session_placeholders(
    template: str,
    *,
    workspace_path: str,
    requirement_id: str,
) -> str:
    """将文本中的 {workspace}、{requirement_id} 替换为 Session 上下文实际值。"""
    return _replace_placeholders(
        template,
        workspace_path=workspace_path,
        requirement_id=requirement_id,
    )


def _replace_placeholders(
    template: str,
    *,
    workspace_path: str,
    requirement_id: str,
) -> str:
    ws = normalize_workspace_path(workspace_path)
    text = str(template or "").strip()
    return (
        text.replace("{workspace}", ws)
        .replace("{requirement_id}", str(requirement_id or "").strip())
    )


def has_path_wildcard(path: str) -> bool:
    """路径是否含动态匹配（{*} 通配或 {re:...} 正则）。"""
    return has_path_pattern(path)


def has_path_pattern(path: str) -> bool:
    text = str(path or "")
    return _PATH_WILDCARD in text or _REGEX_SEGMENT_PREFIX in text


def _normalize_path_slashes(text: str) -> str:
    """将路径分隔符 \\ 转为 /，但保留 {re:...} 段内的正则转义。"""
    result: List[str] = []
    index = 0
    while index < len(text):
        if text.startswith(_REGEX_SEGMENT_PREFIX, index):
            end = text.find("}", index + len(_REGEX_SEGMENT_PREFIX))
            if end < 0:
                result.append(text[index:])
                break
            result.append(text[index:end + 1])
            index = end + 1
            continue
        char = text[index]
        if char == "\\":
            result.append("/")
        else:
            result.append(char)
        index += 1
    return "".join(result)


def _path_pattern_segments(pattern: str) -> List[str]:
    normalized = _normalize_path_slashes(str(pattern or ""))
    return [part for part in normalized.split("/") if part]


def _pattern_segments_under_workspace(expanded: str, workspace_root: Path) -> List[str]:
    """将展开后的绝对路径转为 workspace 内相对段，避免 Windows 盘符被误拆成路径段。"""
    normalized = _normalize_path_slashes(str(expanded or ""))
    candidate = Path(normalized)
    if candidate.is_absolute():
        try:
            relative = candidate.resolve().relative_to(workspace_root.resolve())
            normalized = relative.as_posix()
        except ValueError:
            pass
    return _path_pattern_segments(normalized)


def _segment_is_regex(segment: str) -> bool:
    return str(segment or "").startswith(_REGEX_SEGMENT_PREFIX) and str(segment or "").endswith("}")


def _regex_from_segment(segment: str) -> Optional[Pattern[str]]:
    if not _segment_is_regex(segment):
        return None
    body = segment[len(_REGEX_SEGMENT_PREFIX):-1]
    if not body:
        return None
    try:
        return re.compile(body)
    except re.error:
        return None


def _segment_is_pattern(segment: str) -> bool:
    return segment == _PATH_WILDCARD or _PATH_WILDCARD in segment or _segment_is_regex(segment)


def _segment_matches(pattern: str, name: str) -> bool:
    if pattern == _PATH_WILDCARD:
        return True
    regex = _regex_from_segment(pattern)
    if regex is not None:
        return regex.fullmatch(name) is not None
    if _PATH_WILDCARD not in pattern:
        return name == pattern
    return fnmatch(name, pattern.replace(_PATH_WILDCARD, "*"))


def _first_pattern_index(segments: List[str]) -> Optional[int]:
    for index, segment in enumerate(segments):
        if _segment_is_pattern(segment):
            return index
    return None


def _resolve_prefix_dir(prefix_segments: List[str], workspace_root: Path) -> Optional[Path]:
    if not prefix_segments:
        return workspace_root
    path = Path(prefix_segments[0])
    for segment in prefix_segments[1:]:
        path = path / segment
    if not path.is_absolute():
        path = workspace_root / path
    path = path.resolve()
    if not _within_workspace(path, workspace_root) or not path.is_dir():
        return None
    return path


def _expand_pattern_from(
    current_dir: Path,
    segments: List[str],
    workspace_root: Path,
) -> List[Path]:
    if not segments:
        return [current_dir.resolve()] if current_dir.is_file() and _within_workspace(current_dir, workspace_root) else []

    if len(segments) == 1:
        return _match_files_in_dir(current_dir, segments[0], workspace_root)

    head, *tail = segments
    if not _segment_is_pattern(head):
        next_dir = current_dir / head
        if not next_dir.is_dir() or not _within_workspace(next_dir, workspace_root):
            return []
        return _expand_pattern_from(next_dir, tail, workspace_root)

    results: List[Path] = []
    try:
        children = [item for item in current_dir.iterdir() if item.is_dir()]
    except OSError:
        return []
    for child in children:
        if not _segment_matches(head, child.name):
            continue
        if not _within_workspace(child, workspace_root):
            continue
        results.extend(_expand_pattern_from(child, tail, workspace_root))
    return results


def _match_files_in_dir(current_dir: Path, pattern: str, workspace_root: Path) -> List[Path]:
    results: List[Path] = []
    try:
        entries = list(current_dir.iterdir())
    except OSError:
        return []
    for entry in entries:
        if not entry.is_file():
            continue
        if not _segment_matches(pattern, entry.name):
            continue
        if _within_workspace(entry, workspace_root):
            results.append(entry.resolve())
    return results


def expand_workspace_ref_paths(
    workspace_path: str,
    requirement_id: str,
    ref_path: str,
) -> List[Path]:
    """展开占位符、{*} 通配与 {re:...} 正则，返回 workspace 内所有匹配文件路径。"""
    ws = normalize_workspace_path(workspace_path)
    if not ws or not str(ref_path or "").strip():
        return []
    workspace_root = Path(ws).resolve()
    expanded = _replace_placeholders(ref_path, workspace_path=ws, requirement_id=requirement_id)
    if not has_path_pattern(ref_path):
        single = resolve_workspace_ref_path(workspace_path, requirement_id, ref_path)
        return [single] if single is not None else []

    segments = _pattern_segments_under_workspace(expanded, workspace_root)
    pattern_index = _first_pattern_index(segments)
    if pattern_index is None:
        return []

    start = _resolve_prefix_dir(segments[:pattern_index], workspace_root)
    if start is None:
        return []

    matches = _expand_pattern_from(start, segments[pattern_index:], workspace_root)
    unique: List[Path] = []
    seen: set[str] = set()
    for path in sorted(matches, key=lambda item: str(item).lower()):
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
        if len(unique) >= _GLOB_MATCH_LIMIT:
            break
    return unique

def _inspect_resolved_file(path: Path) -> Dict[str, Any]:
    item: Dict[str, Any] = {
        "resolved_path": str(path),
        "exists": True,
        "kind": "file",
    }
    try:
        item["size"] = path.stat().st_size
    except OSError:
        item["size"] = 0
    preview = _read_text_preview(path)
    if preview is not None:
        item["preview"] = preview
    return item


def _within_workspace(candidate: Path, workspace_root: Path) -> bool:
    try:
        candidate.resolve().relative_to(workspace_root.resolve())
        return True
    except ValueError:
        return False


def resolve_workspace_ref_path(
    workspace_path: str,
    requirement_id: str,
    ref_path: str,
) -> Optional[Path]:
    ws = normalize_workspace_path(workspace_path)
    if not ws or not str(ref_path or "").strip():
        return None
    if has_path_pattern(ref_path):
        return None
    workspace_root = Path(ws)
    expanded = _replace_placeholders(ref_path, workspace_path=ws, requirement_id=requirement_id)
    raw = Path(expanded)
    if raw.is_absolute():
        candidate = raw.resolve()
    else:
        candidate = (workspace_root / expanded).resolve()
    if not _within_workspace(candidate, workspace_root):
        return None
    return candidate


def _read_text_preview(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    suffix = path.suffix.lower()
    if suffix not in _TEXT_SUFFIXES and suffix:
        return None
    try:
        size = path.stat().st_size
    except OSError:
        return None
    if size > _PREVIEW_MAX_BYTES:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

def _list_dir_entries(path: Path) -> List[Dict[str, Any]]:
    if not path.is_dir():
        return []
    entries: List[Dict[str, Any]] = []
    try:
        children = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except OSError:
        return []
    for child in children[:_DIR_LIST_LIMIT]:
        entries.append({
            "name": child.name,
            "kind": "dir" if child.is_dir() else "file",
            "path": str(child.resolve()),
        })
    truncated = len(children) > _DIR_LIST_LIMIT
    if truncated:
        entries.append({"name": "…", "kind": "more", "path": ""})
    return entries


def inspect_workspace_refs(
    *,
    workspace_path: str,
    requirement_id: str,
    refs: List[NodeWorkspaceRef],
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for ref in refs:
        item: Dict[str, Any] = {
            "path": ref.path,
            "label": ref.label or ref.path,
            "resolved_path": "",
            "exists": False,
            "kind": "missing",
        }
        if has_path_pattern(ref.path):
            matches = expand_workspace_ref_paths(workspace_path, requirement_id, ref.path)
            item["wildcard"] = True
            item["match_count"] = len(matches)
            match_items = [_inspect_resolved_file(path) for path in matches]
            item["matches"] = match_items
            if match_items:
                item["exists"] = True
                item["kind"] = "glob"
                item["resolved_path"] = match_items[0]["resolved_path"]
            else:
                item["error"] = "路径模式未匹配到任何文件"
            items.append(item)
            continue

        resolved = resolve_workspace_ref_path(workspace_path, requirement_id, ref.path)
        item["resolved_path"] = str(resolved) if resolved is not None else ""
        if resolved is None:
            item["error"] = "路径无效或超出 Workspace"
            items.append(item)
            continue
        if resolved.is_file():
            item["exists"] = True
            item["kind"] = "file"
            try:
                item["size"] = resolved.stat().st_size
            except OSError:
                item["size"] = 0
            preview = _read_text_preview(resolved)
            if preview is not None:
                item["preview"] = preview
        elif resolved.is_dir():
            item["exists"] = True
            item["kind"] = "dir"
            item["entries"] = _list_dir_entries(resolved)
        else:
            item["kind"] = "missing"
        items.append(item)
    return items
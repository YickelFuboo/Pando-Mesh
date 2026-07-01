from pathlib import Path
from typing import Any, Dict

from app.workspace.markdown_meta import normalize_meta, split_markdown_frontmatter
from app.workspace.paths import normalize_workspace_path
from app.workspace.refs import resolve_workspace_ref_path

WORKSPACE_FILE_MAX_BYTES = 2 * 1024 * 1024


def read_workspace_text_file(
    workspace_path: str,
    path: str,
    *,
    requirement_id: str = "",
    max_bytes: int = WORKSPACE_FILE_MAX_BYTES,
) -> Dict[str, Any]:
    ws = normalize_workspace_path(workspace_path)
    if not ws:
        raise ValueError("workspace_path 不能为空")
    resolved = resolve_workspace_ref_path(ws, requirement_id, path)
    if resolved is None:
        raise ValueError("路径无效或超出 Workspace")
    if not resolved.is_file():
        raise FileNotFoundError("文件不存在")
    try:
        size = resolved.stat().st_size
    except OSError as exc:
        raise FileNotFoundError("无法读取文件") from exc
    if size > max_bytes:
        raise ValueError("文件过大，暂不支持在线预览")
    try:
        text = resolved.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError("无法以文本方式读取该文件") from exc
    meta, body = split_markdown_frontmatter(text)
    return {
        "path": path,
        "resolved_path": str(resolved.resolve()),
        "name": resolved.name,
        "content": body,
        "meta": normalize_meta(meta),
    }

from __future__ import annotations

import re
from typing import Any, Dict, Tuple

import yaml


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---(?:\r?\n|\r)([\s\S]*)$", re.DOTALL)


def split_markdown_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    raw = str(text or "")
    match = _FRONTMATTER_RE.match(raw)
    if not match:
        return {}, raw
    try:
        meta = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    body = match.group(2)
    if body.startswith("\r\n"):
        body = body[2:]
    elif body.startswith("\n"):
        body = body[1:]
    return meta, body


def normalize_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
    rows: Dict[str, Any] = {}
    for key, value in (meta or {}).items():
        name = str(key or "").strip()
        if not name:
            continue
        rows[name] = value
    return rows

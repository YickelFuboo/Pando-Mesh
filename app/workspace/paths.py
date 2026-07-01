import os
from pathlib import Path


def normalize_workspace_path(workspace_path: str) -> str:
    raw = str(workspace_path or "").strip()
    if not raw:
        return ""
    return str(Path(raw).expanduser().resolve())


def paths_equal(a: str, b: str) -> bool:
    na = normalize_workspace_path(a)
    nb = normalize_workspace_path(b)
    if not na or not nb:
        return na == nb
    if os.name == "nt":
        return na.casefold() == nb.casefold()
    return na == nb

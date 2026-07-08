from copy import deepcopy
from typing import Any, Dict, Tuple

DEFAULT_CLI_HISTORY_CONFIG: Dict[str, Any] = {
    "config_dir": "~/.claude",
}


def normalize_history_config(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return dict(DEFAULT_CLI_HISTORY_CONFIG)
    config_dir = str(raw.get("config_dir") or "").strip()
    out = dict(DEFAULT_CLI_HISTORY_CONFIG)
    if config_dir:
        out["config_dir"] = config_dir
    return out


def extract_session_config(executor_template: Dict[str, Any]) -> Dict[str, Any]:
    session = (executor_template or {}).get("cli", {}).get("session")
    if not isinstance(session, dict):
        return {}
    rest = {k: v for k, v in session.items() if k != "history"}
    return dict(rest)


def extract_history_config(executor_template: Dict[str, Any]) -> Dict[str, Any]:
    session = (executor_template or {}).get("cli", {}).get("session")
    if not isinstance(session, dict):
        return dict(DEFAULT_CLI_HISTORY_CONFIG)
    return normalize_history_config(session.get("history"))


def merge_cli_session(
    executor_template: Dict[str, Any],
    session_config: Dict[str, Any],
    history_config: Dict[str, Any],
) -> Dict[str, Any]:
    kind = str((executor_template or {}).get("kind") or "").strip().lower()
    if kind != "cli":
        return dict(executor_template or {})
    next_tpl = deepcopy(executor_template or {})
    cli = next_tpl.setdefault("cli", {})
    session = dict(cli.get("session") or {})
    if session_config:
        session.update(session_config)
    if history_config:
        session["history"] = normalize_history_config(
            {**(session.get("history") or {}), **history_config},
        )
    cli["session"] = session
    return next_tpl


def normalize_executor_template(
    executor_template: Dict[str, Any],
    session_config: Dict[str, Any] | None = None,
    history_config: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return merge_cli_session(
        executor_template or {},
        session_config or {},
        history_config or {},
    )


def split_executor_views(
    executor_template: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    executor = dict(executor_template or {})
    session_cfg = extract_session_config(executor)
    history_cfg = extract_history_config(executor)
    return executor, session_cfg, history_cfg

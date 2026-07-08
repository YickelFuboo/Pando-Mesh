from enum import Enum


class AgentKind(str, Enum):
    """Agent 接入类型。"""
    CLAUDE_CODE_CLI = "claude_code_cli"
    CODEX_CLI = "codex_cli"
    TREA_CLI = "trea_cli"
    RESTFUL_API = "restful_api"

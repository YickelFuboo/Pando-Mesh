from enum import Enum


class AgentKind(str, Enum):
    """Agent 接入类型。"""
    NATIVE = "native"
    CODEX_SDK = "codex_sdk"
    CLAUDE_CODE_CLI = "claude_code_cli"
    API = "api"

from typing import Any, Dict, List, Tuple
from app.register.models import AgentRegistration
from app.register.types import AgentKind

_CLAUDE_CLI_EXECUTOR: Dict[str, Any] = {
    "kind": "cli",
    "cli": {
        "commands": [
            {
                "command": "claude",
                "args": [
                    "-p",
                    "--output-format",
                    "json",
                    "--dangerously-skip-permissions",
                    "--disallowedTools",
                    "AskUserQuestion",
                ],
            },
        ],
        "input": "arg",
        "cwd": "{workspace}",
        "timeout_sec": 3600,
        "output_mode": "json",
        "result_json_key": "result",
        "session": {
            "enabled": True,
            "resume_args": ["--resume", "{cli_session_id}"],
            "read_session_id_from_json": True,
            "session_id_json_key": "session_id",
            "history": {"config_dir": "~/.claude"},
        },
    },
}

_CODEX_CLI_EXECUTOR: Dict[str, Any] = {
    "kind": "cli",
    "cli": {
        "commands": [
            {"command": "codex", "args": ["exec", "--full-auto"]},
        ],
        "input": "arg",
        "cwd": "{workspace}",
        "timeout_sec": 3600,
        "output_mode": "stdout",
    },
}

_KIND_DEFAULT_EXECUTORS: Dict[str, Dict[str, Any]] = {
    AgentKind.CLAUDE_CODE_CLI.value: _CLAUDE_CLI_EXECUTOR,
    AgentKind.CODEX_SDK.value: _CODEX_CLI_EXECUTOR,
    AgentKind.NATIVE.value: {"kind": "react", "agent_type": "AiDeveloper"},
    AgentKind.API.value: {"kind": "react", "agent_type": "ThirdPartyApi"},
}

_BUILTIN_SPECS: Tuple[Tuple[str, str, AgentKind, str], ...] = (
    (
        "claude_code",
        "Claude Code CLI",
        AgentKind.CLAUDE_CODE_CLI,
        "Anthropic Claude Code 命令行 Agent，适合代码开发与审查",
    ),
    (
        "codex_cli",
        "Codex CLI",
        AgentKind.CODEX_SDK,
        "OpenAI Codex 命令行编码助手",
    ),
    (
        "native_react",
        "自研 ReAct Agent",
        AgentKind.NATIVE,
        "Pando 自研 ReAct 执行器",
    ),
    (
        "third_party_api",
        "第三方 API Agent",
        AgentKind.API,
        "通过 ReAct 接入第三方能力；无需 URL/Body，模型在 MaaS 模型设置中配置",
    ),
)


def parse_agent_kind(kind: str) -> AgentKind:
    try:
        return AgentKind(str(kind or AgentKind.NATIVE.value).strip().lower())
    except ValueError as e:
        raise ValueError(f"不支持的 Agent 类型: {kind}") from e


def default_template_for_kind(kind: str) -> Dict[str, Any]:
    agent_kind = parse_agent_kind(kind)
    template = _KIND_DEFAULT_EXECUTORS.get(agent_kind.value)
    if template is None:
        return {"kind": "react", "agent_type": "AiDeveloper"}
    return dict(template)


def default_agents() -> List[AgentRegistration]:
    """内置 Agent 默认定义（唯一模板源，不依赖 data/agents 下文件）。"""
    return [
        AgentRegistration(
            agent_id=agent_id,
            name=name,
            kind=kind,
            description=description,
            executor_template=default_template_for_kind(kind.value),
            builtin=True,
        )
        for agent_id, name, kind, description in _BUILTIN_SPECS
    ]


def builtin_agent_ids() -> frozenset[str]:
    return frozenset(agent_id for agent_id, _, _, _ in _BUILTIN_SPECS)

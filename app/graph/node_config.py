"""GraphNode 节点配置（executor / CLI）。

本模块定义 GraphNode 执行时「走 ReAct 还是走 CLI」的配置结构，以及从
Session 拓扑 JSON 解析、序列化的方法。

配置来源（仅 Session 拓扑 / Planning 生成图）：
- 节点 JSON 的 executor 对象（ReAct：`kind` + `agent_type`；CLI：`kind` + `cli`）
- 未配置 executor 时默认 kind=react

拓扑节点完整示例（ReAct，默认）::

    {
      "id": "step_dev",
      "label": "开发实现",
      "task": "完成接口开发",
      "max_iterations": 3,
      "executor": {
        "kind": "react",
        "agent_type": "AiDeveioper"
      }
    }

CLI 模式一：commands 多步顺序执行::

    {
      "id": "step_dev",
      "label": "Claude Code 开发",
      "task": "完成接口开发",
      "max_iterations": 3,
      "executor": {
        "kind": "cli",
        "cli": {
          "commands": [
            {"cwd": "{workspace}/src"},
            {
              "command": "claude",
              "args": ["-p", "--output-format", "json", "--dangerously-skip-permissions", "--disallowedTools", "AskUserQuestion"]
            }
          ],
          "input": "arg",
          "cwd": "{workspace}",
          "timeout_sec": 3600,
          "env": {"ANTHROPIC_API_KEY": "sk-..."},
          "output_mode": "json",
          "result_json_key": "result",
          "session": {
            "enabled": true,
            "resume_args": ["--resume", "{cli_session_id}"],
            "read_session_id_from_json": true,
            "session_id_json_key": "session_id"
          }
        }
      }
    }

CLI 模式二：shell 整段脚本（cli.shell 与 cli.commands 二选一，shell 优先）::

    {
      "id": "step_dev",
      "label": "Claude Code 开发",
      "task": "完成接口开发",
      "executor": {
        "kind": "cli",
        "cli": {
          "shell": "cd {workspace} && claude -p --output-format json {session_args}",
          "input": "arg",
          "cwd": "{workspace}",
          "timeout_sec": 3600,
          "output_mode": "json",
          "result_json_key": "result",
          "session": {
            "enabled": true,
            "resume_args": ["--resume", "{cli_session_id}"],
            "read_session_id_from_json": true,
            "session_id_json_key": "session_id"
          }
        }
      }
    }

commands 单步也可只用 shell 或仅 cwd（切换后续步骤工作目录）::

    {"shell": "cd {workspace} && npm test"}
    {"cwd": "{workspace}/backend"}

常用占位符：{workspace} {task} {cli_session_id} {session_args}
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


PLANNING_EXECUTOR_REACT = "react"
PLANNING_EXECUTOR_CLI = "cli"
PLANNING_EXECUTOR_HUMAN = "human"
PLANNING_EXECUTOR_EXPAND = "expand"
PLANNING_EXECUTOR_FORK = "fork"


def _parse_bool(raw: Any, *, default: bool) -> bool:
    """将 JSON 中的布尔值规范化（支持 true/false 字符串）。"""
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() not in {"0", "false", "no", "off"}
    return bool(raw)


@dataclass(frozen=True)
class GraphNodeCliHistoryConfig:
    """从第三方 CLI 系统读取会话历史（如 Claude Code JSONL）。

    config_dir 为可选显式根目录，优先级高于进程环境变量 CLAUDE_CONFIG_DIR 与默认 ~/.claude；
    当 CLI 数据目录非默认、或 Harness 与 CLI 环境不一致时，在节点上配置 config_dir 更可靠。
    """
    provider: str = "none"
    config_dir: str = ""

    @classmethod
    def from_dict(cls, raw: Any) -> "GraphNodeCliHistoryConfig":
        if not isinstance(raw, dict):
            return cls()
        provider = str(raw.get("provider") or "none").strip().lower()
        return cls(
            provider=provider or "none",
            config_dir=str(raw.get("config_dir") or "").strip(),
        )

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"provider": self.provider}
        if self.config_dir:
            payload["config_dir"] = self.config_dir
        return payload


@dataclass(frozen=True)
class GraphNodeCliSessionConfig:
    """外部 CLI 的会话持久化（如 Claude Code --resume）。

    会话 id 保存在 PlanGraphState.node_session_id[node_id]；
    首次执行不传 session 参数，从 CLI JSON 输出读取 session_id 并回写；
    同节点再次执行（驳回返工等）用 resume_args。
    """
    enabled: bool = False
    resume_args: List[str] = field(default_factory=lambda: ["--resume", "{cli_session_id}"])
    read_session_id_from_json: bool = True
    session_id_json_key: str = "session_id"
    history: GraphNodeCliHistoryConfig = field(default_factory=GraphNodeCliHistoryConfig)

    @classmethod
    def from_dict(cls, raw: Any) -> "GraphNodeCliSessionConfig":
        if not isinstance(raw, dict):
            return cls()
        return cls(
            enabled=bool(raw.get("enabled")),
            resume_args=[str(x) for x in (raw.get("resume_args") or ["--resume", "{cli_session_id}"])],
            read_session_id_from_json=_parse_bool(
                raw.get("read_session_id_from_json"),
                default=True,
            ),
            session_id_json_key=str(raw.get("session_id_json_key") or "session_id"),
            history=GraphNodeCliHistoryConfig.from_dict(raw.get("history")),
        )

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "enabled": self.enabled,
            "resume_args": list(self.resume_args),
            "read_session_id_from_json": self.read_session_id_from_json,
            "session_id_json_key": self.session_id_json_key,
        }
        history_payload = self.history.to_dict()
        if self.enabled and history_payload.get("provider") in ("", "none"):
            history_payload = GraphNodeCliHistoryConfig(provider="claude_code_jsonl", config_dir=self.history.config_dir).to_dict()
        if history_payload.get("provider") and history_payload.get("provider") != "none":
            payload["history"] = history_payload
        return payload


@dataclass(frozen=True)
class GraphNodeCliStep:
    """多步 CLI（commands 数组）中的单步。

    每一步至少包含以下之一：
    - 仅 cwd：切换后续步骤的工作目录（等价 cd，跨平台）
    - shell：执行一段 shell 字符串（如 cd x && echo ok）
    - command + args：exec 方式调用可执行文件
    """
    cwd: str = ""
    command: str = ""
    args: Tuple[str, ...] = ()
    shell: str = ""

    @classmethod
    def from_dict(cls, raw: Any) -> Optional["GraphNodeCliStep"]:
        if not isinstance(raw, dict):
            return None
        cwd = str(raw.get("cwd") or "").strip()
        command = str(raw.get("command") or "").strip()
        args_raw = raw.get("args")
        args = tuple(str(x) for x in args_raw) if isinstance(args_raw, list) else ()
        shell = str(raw.get("shell") or "").strip()
        if not command and not shell and not cwd:
            return None
        return cls(command=command, args=args, shell=shell, cwd=cwd)

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        if self.cwd:
            payload["cwd"] = self.cwd
        if self.command:
            payload["command"] = self.command
        if self.args:
            payload["args"] = list(self.args)
        if self.shell:
            payload["shell"] = self.shell
        return payload


@dataclass(frozen=True)
class GraphNodeCliConfig:
    """单个 GraphNode 的 CLI 执行细节（GraphNodeExecutor.cli）。

    两种互斥的运行方式（由 run_mode() 自动判断）：
    - commands：cli.commands 数组（单步或多步顺序执行）
    - shell：cli.shell 整段 shell 脚本

    input（JSON 字段名）表示如何把编排任务 task 传给 CLI：
    - arg：task 作为最后一个命令行参数（Claude -p 常用，默认）
    - stdin：task 写入标准输入
    - 或在 args/shell 中自行写 {task} 占位符
    """
    shell: str = ""
    commands: Tuple[GraphNodeCliStep, ...] = ()
    input_mode: str = "arg"
    cwd: str = "{workspace}"
    timeout_sec: int = 3600
    env: Dict[str, str] = field(default_factory=dict)
    output_mode: str = "stdout"
    result_json_key: str = "result"
    session: GraphNodeCliSessionConfig = field(default_factory=GraphNodeCliSessionConfig)

    def run_mode(self) -> str:
        """返回 commands | shell | 空字符串（配置无效）。"""
        if (self.shell or "").strip():
            return "shell"
        if self.commands:
            return "commands"
        return ""

    @classmethod
    def from_dict(cls, raw: Any) -> Optional["GraphNodeCliConfig"]:
        if not isinstance(raw, dict):
            return None
        shell = str(raw.get("shell") or "").strip()
        steps: List[GraphNodeCliStep] = []
        for item in raw.get("commands") or []:
            step = GraphNodeCliStep.from_dict(item)
            if step is not None:
                steps.append(step)
        if not shell and not steps:
            return None
        env_raw = raw.get("env")
        env = {str(k): str(v) for k, v in env_raw.items()} if isinstance(env_raw, dict) else {}
        return cls(
            shell=shell,
            commands=tuple(steps),
            input_mode=str(raw.get("input") or "arg").strip().lower(),
            cwd=str(raw.get("cwd") or "{workspace}"),
            timeout_sec=max(1, int(raw.get("timeout_sec") or 3600)),
            env=env,
            session=GraphNodeCliSessionConfig.from_dict(raw.get("session")),
            output_mode=str(raw.get("output_mode") or "stdout").strip().lower(),
            result_json_key=str(raw.get("result_json_key") or "result"),
        )

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "input": self.input_mode,
            "cwd": self.cwd,
            "timeout_sec": self.timeout_sec,
            "env": dict(self.env),
            "output_mode": self.output_mode,
            "result_json_key": self.result_json_key,
            "session": self.session.to_dict(),
        }
        if self.shell:
            payload["shell"] = self.shell
        if self.commands:
            payload["commands"] = [step.to_dict() for step in self.commands]
        return payload


@dataclass(frozen=True)
class GraphNodeHumanConfig:
    auto_confirm: bool = False

    @classmethod
    def from_dict(cls, raw: Any) -> "GraphNodeHumanConfig":
        if not isinstance(raw, dict):
            return cls()
        return cls(auto_confirm=_parse_bool(raw.get("auto_confirm"), default=False))

    def to_dict(self) -> Dict[str, Any]:
        if not self.auto_confirm:
            return {}
        return {"auto_confirm": True}


@dataclass(frozen=True)
class GraphNodeExpandConfig:
    source_node_id: str = ""
    merge_label: str = "任务汇聚"
    mode: str = "auto"
    confirm_mode: str = "manual"
    default_lane_template_id: str = ""
    planner: str = "source"
    catalog_templates: Tuple[str, ...] = ()

    def is_auto_confirm(self) -> bool:
        return str(self.confirm_mode or "").strip().lower() == "auto"

    @classmethod
    def from_dict(cls, raw: Any) -> "GraphNodeExpandConfig":
        if not isinstance(raw, dict):
            return cls()
        catalog_raw = raw.get("catalog_templates")
        catalog: Tuple[str, ...] = ()
        if isinstance(catalog_raw, list):
            catalog = tuple(str(x).strip() for x in catalog_raw if str(x).strip())
        return cls(
            source_node_id=str(raw.get("source_node_id") or "").strip(),
            merge_label=str(raw.get("merge_label") or "任务汇聚").strip() or "任务汇聚",
            mode=str(raw.get("mode") or "auto").strip().lower() or "auto",
            confirm_mode=str(raw.get("confirm_mode") or "manual").strip().lower() or "manual",
            default_lane_template_id=str(raw.get("default_lane_template_id") or "").strip(),
            planner=str(raw.get("planner") or "source").strip().lower() or "source",
            catalog_templates=catalog,
        )

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"merge_label": self.merge_label}
        if self.source_node_id:
            payload["source_node_id"] = self.source_node_id
        if self.mode and self.mode != "auto":
            payload["mode"] = self.mode
        if self.confirm_mode and self.confirm_mode != "manual":
            payload["confirm_mode"] = self.confirm_mode
        if self.default_lane_template_id:
            payload["default_lane_template_id"] = self.default_lane_template_id
        if self.planner and self.planner != "source":
            payload["planner"] = self.planner
        if self.catalog_templates:
            payload["catalog_templates"] = list(self.catalog_templates)
        return payload


@dataclass
class GraphNodeExecutor:
    """节点执行策略：ReAct / CLI / 人工卡点 / 任务分裂 / 并行分发。"""
    kind: str = PLANNING_EXECUTOR_REACT
    agent_type: str = ""
    cli: Optional[GraphNodeCliConfig] = None
    expand: Optional[GraphNodeExpandConfig] = None
    human: Optional[GraphNodeHumanConfig] = None
    registered_agent_id: str = ""

    @classmethod
    def from_react(cls, agent_type: str = "", registered_agent_id: str = "") -> "GraphNodeExecutor":
        return cls(
            kind=PLANNING_EXECUTOR_REACT,
            agent_type=agent_type,
            cli=None,
            expand=None,
            registered_agent_id=(registered_agent_id or "").strip(),
        )

    @classmethod
    def from_cli(cls, cli_cfg: GraphNodeCliConfig, registered_agent_id: str = "") -> "GraphNodeExecutor":
        return cls(
            kind=PLANNING_EXECUTOR_CLI,
            agent_type="",
            cli=cli_cfg,
            expand=None,
            registered_agent_id=(registered_agent_id or "").strip(),
        )

    @classmethod
    def from_human(cls, human_cfg: Optional[GraphNodeHumanConfig] = None) -> "GraphNodeExecutor":
        return cls(
            kind=PLANNING_EXECUTOR_HUMAN,
            agent_type="",
            cli=None,
            expand=None,
            human=human_cfg or GraphNodeHumanConfig(),
        )

    @classmethod
    def from_expand(cls, expand_cfg: Optional[GraphNodeExpandConfig] = None) -> "GraphNodeExecutor":
        return cls(
            kind=PLANNING_EXECUTOR_EXPAND,
            agent_type="",
            cli=None,
            expand=expand_cfg or GraphNodeExpandConfig(),
        )

    @classmethod
    def from_fork(cls) -> "GraphNodeExecutor":
        return cls(kind=PLANNING_EXECUTOR_FORK, agent_type="", cli=None, expand=None)

    def is_cli(self) -> bool:
        return self.kind == PLANNING_EXECUTOR_CLI and self.cli is not None

    def is_human(self) -> bool:
        return self.kind == PLANNING_EXECUTOR_HUMAN

    def is_expand(self) -> bool:
        return self.kind == PLANNING_EXECUTOR_EXPAND

    def is_fork(self) -> bool:
        return self.kind == PLANNING_EXECUTOR_FORK

    def to_dict(self) -> Dict[str, Any]:
        """写入 Session 拓扑 executor 对象。"""
        payload: Dict[str, Any] = {"kind": self.kind}
        if self.registered_agent_id:
            payload["registered_agent_id"] = self.registered_agent_id
        if self.kind == PLANNING_EXECUTOR_REACT and self.agent_type:
            payload["agent_type"] = self.agent_type
        if self.cli is not None:
            payload["cli"] = self.cli.to_dict()
        if self.expand is not None and self.kind == PLANNING_EXECUTOR_EXPAND:
            payload["expand"] = self.expand.to_dict()
        if self.human is not None and self.kind == PLANNING_EXECUTOR_HUMAN:
            human_dict = self.human.to_dict()
            if human_dict:
                payload["human"] = human_dict
        return payload

    @staticmethod
    def _merge_registered_agent(raw: Dict[str, Any]) -> Dict[str, Any]:
        agent_id = str(raw.get("registered_agent_id") or "").strip()
        if not agent_id:
            return raw
        from app.third_agent.register.register import AgentRegistry
        agent = AgentRegistry().get(agent_id)
        if agent is None or not agent.executor_template:
            return raw
        template = dict(agent.executor_template)
        merged = {**template, **raw}
        if not isinstance(raw.get("cli"), dict) and isinstance(template.get("cli"), dict):
            merged["cli"] = template["cli"]
        merged["registered_agent_id"] = agent_id
        return merged

    @classmethod
    def from_dict(cls, raw: Any) -> "GraphNodeExecutor":
        """从拓扑节点 executor 子对象还原。"""
        if not isinstance(raw, dict):
            return cls.from_react()
        raw = cls._merge_registered_agent(dict(raw))
        agent_id = str(raw.get("registered_agent_id") or "").strip()
        kind = str(raw.get("kind") or PLANNING_EXECUTOR_REACT).strip().lower()
        if kind == PLANNING_EXECUTOR_HUMAN:
            return cls.from_human(GraphNodeHumanConfig.from_dict(raw.get("human")))
        if kind == PLANNING_EXECUTOR_EXPAND:
            return cls.from_expand(GraphNodeExpandConfig.from_dict(raw.get("expand")))
        if kind == PLANNING_EXECUTOR_FORK:
            return cls.from_fork()
        if kind == PLANNING_EXECUTOR_CLI:
            cli_raw = raw.get("cli")
            if isinstance(cli_raw, dict):
                cli = GraphNodeCliConfig.from_dict(cli_raw)
                if cli is not None:
                    return cls.from_cli(cli, registered_agent_id=agent_id)
        agent_type = str(raw.get("agent_type") or "").strip()
        return cls.from_react(agent_type, registered_agent_id=agent_id)

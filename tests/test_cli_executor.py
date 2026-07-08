"""Planning CLI 执行器配置与 session 持久化单元测试。"""
import asyncio
from unittest.mock import AsyncMock, patch

from app.graph.cli_executor import CliNodeExecutor
from app.graph.plan_graph import PLAN_GRAPH_METADATA_KEY, GraphNode, PlanGraphState
from app.graph.node_config import (
    GraphNodeCliConfig,
    GraphNodeCliStep,
    GraphNodeExecutor,
    GraphNodeCliSessionConfig,
)
from app.runtime.context import AgentContext, RuntimeContext

_CLAUDE_DISALLOWED = ["--disallowedTools", "AskUserQuestion"]


class TestPlanningCliConfig:
    def test_parse_cli_config(self):
        cfg = GraphNodeCliConfig.from_dict({
            "commands": [
                {
                    "command": "claude",
                    "args": ["-p", "--output-format", "json"],
                },
            ],
            "session": {"enabled": True},
        })
        assert cfg is not None
        assert cfg.commands[0].command == "claude"
        assert cfg.commands[0].args == ("-p", "--output-format", "json")
        assert cfg.session.enabled is True

    def test_parse_shell_config(self):
        cfg = GraphNodeCliConfig.from_dict({
            "shell": "cd {workspace} && claude -p {session_args}",
            "input": "arg",
        })
        assert cfg is not None
        assert cfg.run_mode() == "shell"

    def test_parse_commands_config(self):
        cfg = GraphNodeCliConfig.from_dict({
            "commands": [
                {"cwd": "{workspace}/src"},
                {"command": "claude", "args": ["-p"]},
            ],
        })
        assert cfg is not None
        assert cfg.run_mode() == "commands"
        assert len(cfg.commands) == 2


class TestCliSessionPersistence:
    def test_metadata_roundtrip_cli_session(self):
        original = PlanGraphState(
            node_session_id={"step_a": "cli-sess-1"},
        )
        wrapped = {PLAN_GRAPH_METADATA_KEY: original.to_metadata()}
        restored = PlanGraphState.from_metadata(wrapped)
        assert restored is not None
        assert restored.node_session_id == {"step_a": "cli-sess-1"}

    def test_clear_history_resets_cli_sessions(self):
        state = PlanGraphState(node_session_id={"step_a": "cli-sess-1"})
        state.clear_history()
        assert state.node_session_id == {}


class TestCliCommandBuild:
    def test_resolve_executable_windows_shim(self):
        with patch("app.graph.cli_executor.shutil.which", return_value=r"C:\npm\claude-code-best.cmd"):
            assert CliNodeExecutor._resolve_executable("claude-code-best") == r"C:\npm\claude-code-best.cmd"

    def test_resolve_executable_keeps_explicit_suffix(self):
        assert CliNodeExecutor._resolve_executable("claude-code-best.cmd") == "claude-code-best.cmd"

    def _claude_cfg(self, **kwargs) -> GraphNodeCliConfig:
        return GraphNodeCliConfig(
            commands=(GraphNodeCliStep(command="claude", args=("-p",)),),
            **kwargs,
        )

    def test_new_session_args_skipped_without_cli_session_id(self):
        cfg = self._claude_cfg(session=GraphNodeCliSessionConfig(enabled=True))
        step = cfg.commands[0]
        variables = {"task": "hello", "cli_session_id": "", "workspace": "/ws"}
        argv, stdin = CliNodeExecutor._build_exec_argv(
            cfg, step, variables, resume_session=False, with_session=True,
        )
        assert argv == ["claude", "-p", "hello", *_CLAUDE_DISALLOWED]
        assert stdin is None

    def test_resume_session_args(self):
        cfg = self._claude_cfg(session=GraphNodeCliSessionConfig(enabled=True))
        step = cfg.commands[0]
        variables = {"task": "hello", "cli_session_id": "uuid-1", "workspace": "/ws"}
        argv, stdin = CliNodeExecutor._build_exec_argv(
            cfg, step, variables, resume_session=True, with_session=True,
        )
        assert argv == ["claude", "-p", "hello", "--resume", "uuid-1", *_CLAUDE_DISALLOWED]
        assert stdin is None

    def test_task_inserted_after_p_when_more_flags_follow(self):
        cfg = GraphNodeCliConfig(
            commands=(
                GraphNodeCliStep(
                    command="claude-code-best",
                    args=("-p", "--output-format", "json", "--dangerously-skip-permissions"),
                ),
            ),
            input_mode="arg",
        )
        step = cfg.commands[0]
        task = "请分析当前代码仓的主要功能。"
        variables = {"task": task, "cli_session_id": "", "workspace": "/ws"}
        argv, stdin = CliNodeExecutor._build_exec_argv(
            cfg, step, variables, resume_session=False, with_session=True,
        )
        assert argv == [
            "claude-code-best",
            "-p",
            task,
            "--output-format",
            "json",
            "--dangerously-skip-permissions",
            "--disallowedTools",
            "AskUserQuestion",
        ]
        assert stdin is None

    def test_auto_disallowed_tools_for_claude_without_explicit_flag(self):
        cfg = GraphNodeCliConfig(
            commands=(
                GraphNodeCliStep(
                    command="claude-code-best",
                    args=("-p", "--output-format", "json", "--dangerously-skip-permissions"),
                ),
            ),
            input_mode="arg",
        )
        step = cfg.commands[0]
        variables = {"task": "hello", "cli_session_id": "", "workspace": "/ws"}
        argv, stdin = CliNodeExecutor._build_exec_argv(
            cfg, step, variables, resume_session=False, with_session=True,
        )
        assert "--disallowedTools" in argv
        assert "AskUserQuestion" in argv
        assert stdin is None

    def test_disallowed_tools_not_duplicated(self):
        cfg = GraphNodeCliConfig(
            commands=(
                GraphNodeCliStep(
                    command="claude",
                    args=("-p", "--disallowedTools", "AskUserQuestion"),
                ),
            ),
            input_mode="arg",
        )
        step = cfg.commands[0]
        variables = {"task": "hello", "cli_session_id": "", "workspace": "/ws"}
        argv, _stdin = CliNodeExecutor._build_exec_argv(
            cfg, step, variables, resume_session=False, with_session=True,
        )
        assert argv.count("--disallowedTools") == 1
        assert argv.count("AskUserQuestion") == 1

    def test_non_claude_command_skips_disallowed_tools(self):
        cfg = GraphNodeCliConfig(
            commands=(GraphNodeCliStep(command="codex", args=("exec",)),),
            input_mode="stdin",
        )
        step = cfg.commands[0]
        variables = {"task": "hello", "cli_session_id": "", "workspace": "/ws"}
        argv, stdin = CliNodeExecutor._build_exec_argv(
            cfg, step, variables, resume_session=False, with_session=True,
        )
        assert "--disallowedTools" not in argv
        assert stdin == "hello"

    def test_shell_mode_appends_disallowed_tools_for_claude(self):
        cfg = GraphNodeCliConfig(
            shell="cd {workspace} && claude -p {session_args}",
            input_mode="arg",
            session=GraphNodeCliSessionConfig(enabled=True),
        )
        variables = {
            "workspace": "/proj",
            "task": "fix bug",
            "cli_session_id": "",
            "session_args": "",
        }
        cmd = CliNodeExecutor._build_shell_command(
            cfg, cfg.shell, variables, resume_session=False, with_session=True,
        )
        assert "--disallowedTools AskUserQuestion" in cmd

    def test_multiline_task_with_p_uses_stdin(self):
        cfg = GraphNodeCliConfig(
            commands=(
                GraphNodeCliStep(
                    command="claude-code-best",
                    args=("-p", "--output-format", "json"),
                ),
            ),
            input_mode="arg",
        )
        step = cfg.commands[0]
        task = "## 用户任务\n重新执行\n\n请分析代码仓。"
        variables = {"task": task, "cli_session_id": "", "workspace": "/ws"}
        argv, stdin = CliNodeExecutor._build_exec_argv(
            cfg, step, variables, resume_session=False, with_session=True,
        )
        assert argv == [
            "claude-code-best",
            "-p",
            "--output-format",
            "json",
            *_CLAUDE_DISALLOWED,
        ]
        assert stdin == task

    def test_single_line_task_with_p_uses_arg_after_p(self):
        cfg = GraphNodeCliConfig(
            commands=(GraphNodeCliStep(command="claude", args=("-p",)),),
            input_mode="arg",
        )
        step = cfg.commands[0]
        task = "单行任务"
        variables = {"task": task, "cli_session_id": "", "workspace": "/ws"}
        argv, stdin = CliNodeExecutor._build_exec_argv(
            cfg, step, variables, resume_session=False, with_session=True,
        )
        assert argv == ["claude", "-p", task, *_CLAUDE_DISALLOWED]
        assert stdin is None

    def test_stdin_input_mode(self):
        cfg = GraphNodeCliConfig(
            commands=(GraphNodeCliStep(command="codex", args=("exec",)),),
            input_mode="stdin",
        )
        step = cfg.commands[0]
        variables = {"task": "do work", "cli_session_id": "", "workspace": "/ws"}
        argv, stdin = CliNodeExecutor._build_exec_argv(
            cfg, step, variables, resume_session=False, with_session=True,
        )
        assert argv == ["codex", "exec"]
        assert stdin == "do work"

    def test_intermediate_step_skips_task(self):
        cfg = GraphNodeCliConfig(
            commands=(
                GraphNodeCliStep(command="npm", args=("test",)),
                GraphNodeCliStep(command="claude", args=("-p",)),
            ),
            input_mode="arg",
        )
        variables = {"task": "big task", "cli_session_id": "", "workspace": "/ws"}
        argv, stdin = CliNodeExecutor._build_exec_argv(
            cfg, cfg.commands[0], variables, resume_session=False, with_session=False,
        )
        assert argv == ["npm", "test"]
        assert stdin is None
        argv, stdin = CliNodeExecutor._build_exec_argv(
            cfg, cfg.commands[1], variables, resume_session=False, with_session=True,
        )
        assert argv == ["claude", "-p", "big task", *_CLAUDE_DISALLOWED]
        assert stdin is None

    def test_shell_command_with_cd(self):
        cfg = GraphNodeCliConfig(
            shell="cd {workspace} && claude -p {session_args}",
            input_mode="arg",
            session=GraphNodeCliSessionConfig(enabled=True),
        )
        variables = {
            "workspace": "/proj",
            "task": "fix bug",
            "cli_session_id": "sid-1",
            "session_args": "--resume sid-1",
        }
        cmd = CliNodeExecutor._build_shell_command(
            cfg, cfg.shell, variables, resume_session=True, with_session=True,
        )
        assert cmd.startswith("cd /proj && claude -p --resume sid-1 ")
        assert "fix bug" in cmd


class TestGraphNodeExecutor:
    def test_from_dict_cli(self):
        executor = GraphNodeExecutor.from_dict({
            "kind": "cli",
            "cli": {
                "commands": [{"command": "claude", "args": ["-p"]}],
            },
        })
        assert executor.is_cli()
        assert executor.agent_type == ""
        assert executor.cli is not None
        assert executor.cli.commands[0].command == "claude"

    def test_from_dict_defaults_react(self):
        assert GraphNodeExecutor.from_dict(None).kind == "react"
        react = GraphNodeExecutor.from_dict({"kind": "react", "agent_type": "AiAssistant"})
        assert react.kind == "react"
        assert react.agent_type == "AiAssistant"

    def test_from_dict_embeds_cli_in_node(self):
        from app.graph.plan_graph import DirectExecGraph

        graph = DirectExecGraph.from_dict({
            "nodes": [{
                "id": "step_a",
                "label": "A",
                "executor": {
                    "kind": "cli",
                    "cli": {"commands": [{"command": "echo", "args": []}]},
                },
            }],
            "edges": [
                {"from": "START", "to": "step_a", "condition": "always"},
                {"from": "step_a", "to": "END", "condition": "always"},
            ],
            "entry": "step_a",
        })
        assert graph is not None
        node = graph.nodes["step_a"]
        assert node.is_cli()
        assert node.executor.cli is not None
        assert node.executor.cli.commands[0].command == "echo"


class TestCliNodeExecutorRun:
    def test_run_persists_session_from_json_output(self):
        plan = PlanGraphState()
        graph_node = GraphNode(
            id="step_a",
            label="测试",
            executor=GraphNodeExecutor.from_cli(
                GraphNodeCliConfig(
                    commands=(GraphNodeCliStep(command="echo"),),
                    input_mode="stdin",
                    output_mode="json",
                    result_json_key="result",
                    session=GraphNodeCliSessionConfig(
                        enabled=True,
                        read_session_id_from_json=True,
                    ),
                ),
            ),
        )
        agent_ctx = AgentContext(
            user_id="u1",
            session_id="parent",
            workspace_path="/tmp/ws",
        )
        runtime_ctx = RuntimeContext(
            actor_id="planning:test",
        )

        async def _run():
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(
                return_value=(
                    b'{"result":"done","session_id":"from-cli-99"}',
                    b"",
                )
            )
            with patch(
                "app.graph.cli_executor.asyncio.create_subprocess_exec",
                new=AsyncMock(return_value=mock_proc),
            ), patch(
                "app.graph.cli_executor.CliNodeExecutor._resolve_cli_cwd",
                return_value="/tmp/ws",
            ):
                result = await CliNodeExecutor.run(
                    plan,
                    graph_node,
                    "task body",
                    agent_ctx,
                    runtime_ctx,
                )
                return result

        result = asyncio.run(_run())
        assert result == "done"
        assert plan.node_session_id["step_a"] == "from-cli-99"


class TestCliSessionPlaceholders:
    def test_build_template_vars_includes_requirement_id(self, tmp_path):
        ws = tmp_path / "project"
        agent_ctx = AgentContext(
            workspace_path=str(ws),
            requirement_id="req1",
        )
        cli_cfg = GraphNodeCliConfig(session=GraphNodeCliSessionConfig(enabled=False))
        variables = CliNodeExecutor._build_template_vars(
            "task body",
            agent_ctx,
            "",
            cli_cfg,
            resume_session=False,
        )
        assert variables["workspace"] == str(ws)
        assert variables["requirement_id"] == "req1"
        assert "requirement" not in variables

    def test_resolve_cli_cwd_requirement_path(self, tmp_path):
        ws = tmp_path / "project"
        req_dir = ws / "requirements" / "req1"
        req_dir.mkdir(parents=True)
        cwd = CliNodeExecutor._resolve_cli_cwd(
            "{workspace}/requirements/{requirement_id}",
            str(ws),
            requirement_id="req1",
        )
        assert cwd == str(req_dir.resolve())

"""第三方 CLI Agent 通用 subprocess 执行引擎。"""
import asyncio
import json
import os
import re
import shlex
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from app.runtime.context import AgentContext, RuntimeContext
from app.graph.node_config import GraphNodeCliConfig, GraphNodeCliStep
from app.third_agent.executor.base import ThirdAgentExecutor
from app.third_agent.executor.types import AgentHistoryRequest, AgentRunRequest, AgentRunResult
from app.workspace.paths import normalize_workspace_path
from app.workspace.refs import expand_session_placeholders

# 编排调度为非交互模式，禁止 Claude Code 调用 AskUserQuestion（会卡住且无用户可答）
_PLANNING_CLI_DISALLOWED_TOOLS: Tuple[str, ...] = ("AskUserQuestion",)
_DISALLOWED_TOOLS_FLAGS = frozenset({"--disallowedTools", "--disallowed-tools"})
_CLAUDE_CLI_NAME_RE = re.compile(r"claude", re.IGNORECASE)


class CliAgentExecutor(ThirdAgentExecutor):
    """CLI Agent 执行器：subprocess 引擎与历史读取调度。"""

    @classmethod
    async def run(
        cls,
        request: AgentRunRequest,
        agent_ctx: AgentContext,
        runtime_ctx: RuntimeContext,
    ) -> AgentRunResult:
        cli_cfg = request.cli
        mode = cli_cfg.run_mode()
        node_label = (request.node_label or request.node_id or "cli").strip()
        if not mode:
            raise ValueError(f"节点「{node_label}」CLI 配置缺少 shell 或 commands")

        resume_session = False
        cli_session_id = (request.session_id or "").strip()
        if cli_cfg.session.enabled:
            resume_session = bool(cli_session_id)

        variables = cls._build_template_vars(
            request.task,
            agent_ctx,
            cli_session_id,
            cli_cfg,
            resume_session=resume_session,
        )
        cwd = cls._resolve_cli_cwd(
            cli_cfg.cwd,
            agent_ctx.workspace_path,
            requirement_id=agent_ctx.requirement_id,
        )
        env = {**os.environ, **cli_cfg.env}

        if mode == "shell":
            stdout_bytes, stderr_bytes, returncode = await cls._run_shell_mode(
                cli_cfg, variables, cwd, env, runtime_ctx, resume_session=resume_session
            )
        else:
            stdout_bytes, stderr_bytes, returncode = await cls._run_commands_mode(
                cli_cfg, variables, cwd, env, runtime_ctx, resume_session=resume_session
            )

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        result, parsed_session_id = cls._resolve_cli_result(
            cli_cfg,
            stdout,
            stderr,
            returncode,
        )
        session_id = parsed_session_id if cli_cfg.session.enabled and parsed_session_id else None
        return AgentRunResult(result=result, session_id=session_id)

    @classmethod
    async def get_history(cls, request: AgentHistoryRequest):
        handler = cls._resolve_handler(request)
        return await handler.get_history(request)

    @classmethod
    def _resolve_handler(cls, request: AgentHistoryRequest):
        kind = cls._resolve_cli_kind(request)
        return cls._kind_handlers()[kind]

    @classmethod
    def _resolve_cli_kind(cls, request: AgentHistoryRequest) -> str:
        from app.third_agent.register.register import AgentRegistry
        from app.third_agent.register.types import AgentKind

        agent_id = (request.registered_agent_id or "").strip()
        if agent_id:
            reg = AgentRegistry().get(agent_id)
            if reg is not None and reg.kind.value in cls._kind_handlers():
                return reg.kind.value
        inferred = cls._infer_kind_from_cli(request.cli)
        if inferred:
            return inferred
        return AgentKind.CLAUDE_CODE_CLI.value

    @classmethod
    def _infer_kind_from_cli(cls, cli_cfg: GraphNodeCliConfig | None) -> str | None:
        from app.third_agent.register.types import AgentKind

        if cli_cfg is None:
            return None
        command = ""
        if cli_cfg.commands:
            command = (cli_cfg.commands[0].command or "").lower()
        elif cli_cfg.shell:
            command = cli_cfg.shell.lower()
        if "codex" in command:
            return AgentKind.CODEX_CLI.value
        if "trae" in command:
            return AgentKind.TREA_CLI.value
        if "claude" in command:
            return AgentKind.CLAUDE_CODE_CLI.value
        return None

    @classmethod
    def _kind_handlers(cls) -> dict:
        from app.third_agent.executor.cli_claude import CliClaude
        from app.third_agent.executor.cli_codex import CliCodex
        from app.third_agent.executor.cli_trae import CliTrae
        from app.third_agent.register.types import AgentKind

        return {
            AgentKind.CLAUDE_CODE_CLI.value: CliClaude,
            AgentKind.CODEX_CLI.value: CliCodex,
            AgentKind.TREA_CLI.value: CliTrae,
        }


    @staticmethod
    def _build_template_vars(
        task: str,
        agent_ctx: AgentContext,
        cli_session_id: str,
        cli_cfg: GraphNodeCliConfig,
        *,
        resume_session: bool,
    ) -> Dict[str, str]:
        """组装 CLI 占位符变量表（含 session_args 的 shell 安全拼接）。
        样例：
        {
            "task": "...",           # 编排层拼好的完整任务正文（多段 markdown）
            "workspace": "/home/proj", # 工作目录
            "cli_session_id": "...", # Claude session id，首次为空字符串
            "session_args": "...",   # 给 shell 里 {session_args} 用的，已 shell 转义拼成一段（--resume arg1 arg2）
        }
        """
        ws = (agent_ctx.workspace_path or "").strip()
        req_id = (agent_ctx.requirement_id or "").strip()
        variables = {
            "task": task,
            "workspace": ws,
            "requirement_id": req_id,
            "cli_session_id": cli_session_id,
        }
        session_args = CliAgentExecutor._build_session_arg_list(
            cli_cfg, variables, resume_session=resume_session
        )
        variables["session_args"] = " ".join(shlex.quote(part) for part in session_args)
        return variables

    @staticmethod
    def _build_session_arg_list(
        cli_cfg: GraphNodeCliConfig,
        variables: Dict[str, str],
        *,
        resume_session: bool,
    ) -> List[str]:
        """生成 session 相关 argv 片段（已做占位符展开）。"""
        if not cli_cfg.session.enabled:
            return []
        cli_session_id = (variables.get("cli_session_id") or "").strip()
        if not cli_session_id or not resume_session:
            return []
        return CliAgentExecutor._expand_template_list(cli_cfg.session.resume_args, variables)

    @staticmethod
    def _expand_template_list(items: List[str], variables: Dict[str, str]) -> List[str]:
        """对 argv 列表逐项做 expand_template。"""
        return [CliAgentExecutor._expand_template(item, variables) for item in items]

    @staticmethod
    def _expand_template(value: str, variables: Dict[str, str]) -> str:
        """将字符串中的 {key} 替换为 variables[key]。"""
        text = value
        for key, val in variables.items():
            text = text.replace("{" + key + "}", val)
        return text

    @staticmethod
    def _resolve_cli_cwd(
        template: str,
        workspace_path: Optional[str],
        *,
        requirement_id: str = "",
        base_cwd: Optional[str] = None,
    ) -> str:
        """解析 cwd 模板为绝对路径；目录不存在时会创建。

        例：template="{workspace}/src"、workspace_path="/home/proj" → "/home/proj/src"
        """
        ws = normalize_workspace_path(workspace_path or "")
        base = (base_cwd or ws or str(Path.cwd())).strip()
        tmpl = (template or "").strip()
        if not tmpl:
            tmpl = "{cwd}"
        expanded = expand_session_placeholders(
            tmpl.replace("{cwd}", base),
            workspace_path=ws or base,
            requirement_id=requirement_id,
        )
        path = Path(expanded).expanduser()
        if not path.is_absolute():
            path = (Path(base) / path).resolve()
        else:
            path = path.resolve()
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    @staticmethod
    async def _run_shell_mode(
        cli_cfg: GraphNodeCliConfig,
        variables: Dict[str, str],
        cwd: str,
        env: Dict[str, str],
        runtime_ctx: RuntimeContext,
        *,
        resume_session: bool,
    ) -> Tuple[bytes, bytes, int]:
        """cli.shell 模式：整段脚本一次 subprocess。"""
        shell_cmd = CliAgentExecutor._build_shell_command(
            cli_cfg,
            cli_cfg.shell,
            variables,
            resume_session=resume_session,
            with_session=True,
        )
        stdin_text = variables.get("task") if cli_cfg.input_mode == "stdin" else None
        return await CliAgentExecutor._run_subprocess_shell(
            shell_cmd,
            cwd,
            env,
            stdin_text,
            runtime_ctx,
            cli_cfg.timeout_sec,
        )

    @staticmethod
    async def _run_commands_mode(
        cli_cfg: GraphNodeCliConfig,
        variables: Dict[str, str],
        cwd: str,
        env: Dict[str, str],
        runtime_ctx: RuntimeContext,
        *,
        resume_session: bool,
    ) -> Tuple[bytes, bytes, int]:
        """cli.commands 模式：顺序执行各步（cwd / shell / exec），任一步失败即返回。"""
        steps = cli_cfg.commands
        if not steps:
            raise ValueError("CLI commands 配置为空")
        current_cwd = cwd
        last_stdout = b""
        last_stderr = b""
        last_code = 0
        last_idx = CliAgentExecutor._last_exec_step_index(steps)
        for idx, step in enumerate(steps):
            if step.cwd:
                current_cwd = CliAgentExecutor._resolve_cli_cwd(
                    step.cwd,
                    variables.get("workspace") or None,
                    requirement_id=variables.get("requirement_id") or "",
                    base_cwd=current_cwd,
                )
            with_session = idx == last_idx
            if step.shell:
                shell_cmd = CliAgentExecutor._build_shell_command(
                    cli_cfg,
                    step.shell,
                    variables,
                    resume_session=resume_session,
                    with_session=with_session,
                )
                stdin_text = variables.get("task") if cli_cfg.input_mode == "stdin" and with_session else None
                last_stdout, last_stderr, last_code = await CliAgentExecutor._run_subprocess_shell(
                    shell_cmd,
                    current_cwd,
                    env,
                    stdin_text,
                    runtime_ctx,
                    cli_cfg.timeout_sec,
                )
            elif step.command:
                argv, stdin_text = CliAgentExecutor._build_exec_argv(
                    cli_cfg,
                    step,
                    variables,
                    resume_session=resume_session,
                    with_session=with_session,
                )
                last_stdout, last_stderr, last_code = await CliAgentExecutor._run_subprocess_exec(
                    argv,
                    current_cwd,
                    env,
                    stdin_text if with_session else None,
                    runtime_ctx,
                    cli_cfg.timeout_sec,
                )
            if last_code != 0:
                return last_stdout, last_stderr, last_code
        return last_stdout, last_stderr, last_code

    @staticmethod
    def _resolve_executable(command: str) -> str:
        """将命令名解析为可执行路径。

        Windows 上 npm 全局包多为 .cmd/.ps1 包装，`create_subprocess_exec`
        不能直接启动无扩展名的 shim，需经 shutil.which 解析。
        """
        cmd = (command or "").strip()
        if not cmd:
            return cmd
        if os.path.isabs(cmd) and Path(cmd).exists():
            return cmd
        if Path(cmd).suffix:
            return cmd
        resolved = shutil.which(cmd)
        return resolved or cmd

    @staticmethod
    async def _run_subprocess_exec(
        argv: List[str],
        cwd: str,
        env: Dict[str, str],
        stdin_text: Optional[str],
        runtime_ctx: RuntimeContext,
        timeout_sec: int,
    ) -> Tuple[bytes, bytes, int]:
        """create_subprocess_exec 封装：支持 stdin、超时与用户中止。"""
        if not argv:
            raise ValueError("CLI argv 为空")
        argv = list(argv)
        argv[0] = CliAgentExecutor._resolve_executable(argv[0])
        proc = await asyncio.create_subprocess_exec(
            *argv,
            cwd=cwd,
            env=env,
            stdin=asyncio.subprocess.PIPE if stdin_text is not None else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                CliAgentExecutor._communicate_with_abort(proc, stdin_text, runtime_ctx),
                timeout=timeout_sec,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise RuntimeError(
                f"CLI 执行超时（{timeout_sec}s）：{' '.join(argv[:3])}…"
            ) from None
        except asyncio.CancelledError:
            proc.kill()
            await proc.wait()
            raise
        return stdout_bytes, stderr_bytes, proc.returncode or 0

    @staticmethod
    async def _run_subprocess_shell(
        command: str,
        cwd: str,
        env: Dict[str, str],
        stdin_text: Optional[str],
        runtime_ctx: RuntimeContext,
        timeout_sec: int,
    ) -> Tuple[bytes, bytes, int]:
        """create_subprocess_shell 封装：Windows 用 COMSPEC，支持 stdin、超时与中止。"""
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=cwd,
            env=env,
            stdin=asyncio.subprocess.PIPE if stdin_text is not None else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            executable=CliAgentExecutor._shell_executable(),
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                CliAgentExecutor._communicate_with_abort(proc, stdin_text, runtime_ctx),
                timeout=timeout_sec,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise RuntimeError(
                f"CLI 执行超时（{timeout_sec}s）：{command[:120]}…"
            ) from None
        except asyncio.CancelledError:
            proc.kill()
            await proc.wait()
            raise
        return stdout_bytes, stderr_bytes, proc.returncode or 0

    @staticmethod
    async def _communicate_with_abort(
        proc: asyncio.subprocess.Process,
        stdin_text: Optional[str],
        runtime_ctx: RuntimeContext,
    ) -> Tuple[bytes, bytes]:
        """proc.communicate 轮询：用户中止编排时 kill 子进程并抛出 CancelledError。"""
        stdin_bytes = stdin_text.encode("utf-8") if stdin_text is not None else None
        communicate_task = asyncio.create_task(proc.communicate(input=stdin_bytes))
        while not communicate_task.done():
            if runtime_ctx.is_aborted():
                proc.kill()
                communicate_task.cancel()
                try:
                    await communicate_task
                except asyncio.CancelledError:
                    pass
                await proc.wait()
                raise asyncio.CancelledError("编排已中止")
            await asyncio.sleep(0.2)
        return communicate_task.result()

    @staticmethod
    def _resolve_cli_result(
        cli_cfg: GraphNodeCliConfig,
        stdout: str,
        stderr: str,
        returncode: int,
    ) -> Tuple[str, Optional[str]]:
        """解析 CLI stdout：非零 exit 抛错；json 模式提取 result 与可选 session id。"""
        if returncode != 0:
            err = (stderr or stdout or "").strip()
            raise RuntimeError(
                f"CLI 执行失败 (exit {returncode})"
                + (f": {err[:2000]}" if err else "")
            )
        text = (stdout or "").strip()
        if cli_cfg.output_mode != "json":
            return text, None
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return text, None
        if not isinstance(payload, dict):
            return text, None
        field = cli_cfg.result_json_key or "result"
        content = payload.get(field)
        if content is None:
            content = payload.get("result") or payload.get("content") or payload.get("text")
        if content is None:
            content = text
        session_id = None
        if cli_cfg.session.enabled and cli_cfg.session.read_session_id_from_json:
            sid = payload.get(cli_cfg.session.session_id_json_key or "session_id")
            if sid:
                session_id = str(sid).strip()
        return str(content).strip(), session_id

    @staticmethod
    def _collect_disallowed_tools(argv: List[str]) -> set:
        """从 argv 中解析已有的 --disallowedTools 工具名（支持逗号分隔）。"""
        tools: set = set()
        idx = 0
        while idx < len(argv):
            part = argv[idx]
            if part in _DISALLOWED_TOOLS_FLAGS and idx + 1 < len(argv):
                for item in argv[idx + 1].split(","):
                    name = item.strip()
                    if name:
                        tools.add(name)
                idx += 2
                continue
            idx += 1
        return tools

    @staticmethod
    def _append_disallowed_tools(argv: List[str], tools: Tuple[str, ...]) -> List[str]:
        """向 argv 追加 --disallowedTools；已存在的工具名不重复添加。"""
        if not tools:
            return list(argv)
        existing = CliAgentExecutor._collect_disallowed_tools(argv)
        missing = [name for name in tools if name not in existing]
        if not missing:
            return list(argv)
        result = list(argv)
        for name in missing:
            result.extend(["--disallowedTools", name])
        return result

    @staticmethod
    def _is_claude_cli_argv(argv: List[str]) -> bool:
        """判断 exec 步骤是否为 Claude Code 系命令（claude / claude-code-best 等）。"""
        if not argv:
            return False
        base = Path(str(argv[0])).name.lower()
        return bool(_CLAUDE_CLI_NAME_RE.search(base))

    @staticmethod
    def _shell_invokes_claude(shell_cmd: str) -> bool:
        """判断 shell 脚本字符串中是否包含 Claude Code 调用。"""
        return bool(_CLAUDE_CLI_NAME_RE.search(shell_cmd or ""))

    @staticmethod
    def _append_disallowed_tools_to_shell(shell_cmd: str, tools: Tuple[str, ...]) -> str:
        """向 shell 命令追加 --disallowedTools；仅 Claude 命令生效，已有配置不重复。"""
        if not tools or not CliAgentExecutor._shell_invokes_claude(shell_cmd):
            return shell_cmd
        existing: set = set()
        for match in re.finditer(r"--disallowed[-_]tools\s+(\S+)", shell_cmd, re.IGNORECASE):
            for item in match.group(1).split(","):
                name = item.strip()
                if name:
                    existing.add(name)
        missing = [name for name in tools if name not in existing]
        if not missing:
            return shell_cmd
        suffix = " ".join(f"--disallowedTools {shlex.quote(name)}" for name in missing)
        return f"{shell_cmd} {suffix}"

    @staticmethod
    def _build_exec_argv(
        cli_cfg: GraphNodeCliConfig,
        step: GraphNodeCliStep,
        variables: Dict[str, str],
        *,
        resume_session: bool,
        with_session: bool,
    ) -> Tuple[List[str], Optional[str]]:
        """将 commands 单步展开为 exec argv；仅 with_session 时追加 session 参数与 task。"""
        argv = [CliAgentExecutor._expand_template(step.command, variables)]
        argv.extend(CliAgentExecutor._expand_template_list(list(step.args), variables))
        if with_session:
            argv.extend(
                CliAgentExecutor._build_session_arg_list(cli_cfg, variables, resume_session=resume_session)
            )
            argv, stdin = CliAgentExecutor._append_task_input(cli_cfg, argv, variables)
            if CliAgentExecutor._is_claude_cli_argv(argv):
                argv = CliAgentExecutor._append_disallowed_tools(argv, _PLANNING_CLI_DISALLOWED_TOOLS)
            return argv, stdin
        if any("{task}" in part for part in argv):
            return [CliAgentExecutor._expand_template(part, variables) for part in argv], None
        return argv, None

    @staticmethod
    def _build_shell_command(
        cli_cfg: GraphNodeCliConfig,
        shell_text: str,
        variables: Dict[str, str],
        *,
        resume_session: bool,
        with_session: bool,
    ) -> str:
        """展开 shell 模板并追加 session/task；shell 未写 {session_args} 时自动拼 session argv。"""
        expanded = CliAgentExecutor._expand_template(shell_text, variables)
        if with_session and cli_cfg.session.enabled and "{session_args}" not in shell_text:
            session_args = CliAgentExecutor._build_session_arg_list(
                cli_cfg, variables, resume_session=resume_session
            )
            if session_args:
                expanded = f"{expanded} {' '.join(shlex.quote(part) for part in session_args)}"
        if "{task}" in expanded:
            expanded = CliAgentExecutor._expand_template(expanded, variables)
        if not with_session:
            return expanded
        if CliAgentExecutor._shell_invokes_claude(expanded):
            expanded = CliAgentExecutor._append_disallowed_tools_to_shell(
                expanded, _PLANNING_CLI_DISALLOWED_TOOLS
            )
        if cli_cfg.input_mode == "stdin":
            return expanded
        task = variables.get("task", "")
        if cli_cfg.input_mode == "arg" and task:
            return f"{expanded} {shlex.quote(task)}"
        return expanded

    @staticmethod
    def _prompt_flag_indexes(argv: List[str]) -> List[int]:
        """Claude Code / claude -p 的 prompt 必须紧跟在 -p 之后，不能放在 argv 末尾。"""
        flags = frozenset({"-p", "--print", "--prompt"})
        return [idx for idx, part in enumerate(argv) if part in flags]

    @staticmethod
    def _inject_task_arg(argv: List[str], task: str) -> List[str]:
        """将 task 注入 argv：若含 -p 则插在第一个 -p 之后，否则追加到末尾。"""
        if not task:
            return list(argv)
        items = list(argv)
        prompt_idxs = CliAgentExecutor._prompt_flag_indexes(items)
        if prompt_idxs:
            insert_at = prompt_idxs[0] + 1
            return items[:insert_at] + [task] + items[insert_at:]
        return items + [task]

    @staticmethod
    def _should_deliver_task_via_stdin(argv: List[str], task: str, input_mode: str) -> bool:
        if input_mode == "stdin":
            return True
        # claude -p 在 Windows 上把 argv 中的多行 prompt 截断为第一行；改经 stdin 传递完整任务。
        if (
            input_mode == "arg"
            and task
            and "\n" in task
            and CliAgentExecutor._prompt_flag_indexes(argv)
        ):
            return True
        return False

    @staticmethod
    def _append_task_input(
        cli_cfg: GraphNodeCliConfig,
        argv: List[str],
        variables: Dict[str, str],
    ) -> Tuple[List[str], Optional[str]]:
        """按 input_mode 将 task 注入 argv 或 stdin；支持 args 内 {task} 占位符。"""
        task = variables.get("task", "")
        has_task_placeholder = any("{task}" in part for part in argv)
        if has_task_placeholder:
            return [CliAgentExecutor._expand_template(part, variables) for part in argv], None
        if CliAgentExecutor._should_deliver_task_via_stdin(argv, task, cli_cfg.input_mode):
            return argv, task
        if cli_cfg.input_mode == "arg" and task:
            return CliAgentExecutor._inject_task_arg(argv, task), None
        return argv, None

    @staticmethod
    def _shell_executable() -> Optional[str]:
        """返回当前平台的 shell 可执行路径。"""
        if sys.platform == "win32":
            return os.environ.get("COMSPEC") or "cmd.exe"
        return os.environ.get("SHELL") or "/bin/sh"

    @staticmethod
    def _last_exec_step_index(steps: Tuple[GraphNodeCliStep, ...]) -> int:
        """commands 中最后一个含 command/shell 的步骤下标；session/task 仅在该步注入。"""
        for idx in range(len(steps) - 1, -1, -1):
            step = steps[idx]
            if step.command or step.shell:
                return idx
        return len(steps) - 1

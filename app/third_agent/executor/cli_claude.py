"""Claude Code CLI 品种：get_history 读取 Claude JSONL 会话。"""
import asyncio
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from app.graph.node_config import GraphNodeCliConfig, GraphNodeCliHistoryConfig
from app.runtime.message import Function, Message, Role, ToolCall
from app.third_agent.executor.cli import CliAgentExecutor
from app.third_agent.executor.types import AgentHistoryRequest

_CLAUDE_PROJECT_ENCODE_RE = re.compile(r"[^a-zA-Z0-9]+")


class CliClaude:
    @staticmethod
    async def get_history(request: AgentHistoryRequest) -> List[Message]:
        if not request.is_cli:
            raise ValueError("节点不是 CLI 执行方式")
        cli_cfg = request.cli
        history_cfg = CliClaude._resolve_history_config(cli_cfg)
        if history_cfg.provider == "none":
            raise ValueError("该 CLI 节点未启用历史读取")
        sid = (request.session_id or "").strip()
        if not sid:
            raise ValueError("该步骤尚未产生外部 CLI 会话")
        if history_cfg.provider != "claude_code_jsonl":
            raise ValueError(f"暂不支持的历史 provider: {history_cfg.provider}")
        cwd = CliAgentExecutor._resolve_cli_cwd(cli_cfg.cwd, request.workspace_path)
        config_dir = CliClaude._resolve_config_dir(history_cfg)
        jsonl_path = CliClaude._resolve_jsonl_path(config_dir, cwd, sid)
        if jsonl_path is None:
            raise FileNotFoundError(
                f"未找到 Claude Code 会话文件（session={sid}，workspace={cwd}）"
            )
        return await asyncio.to_thread(CliClaude._parse_jsonl, jsonl_path)

    @staticmethod
    def _encode_project_dir(cwd: str) -> str:
        text = str(Path(cwd).expanduser().resolve())
        encoded = _CLAUDE_PROJECT_ENCODE_RE.sub("-", text).strip("-")
        return encoded or "default"

    @staticmethod
    def _resolve_config_dir(history_cfg: GraphNodeCliHistoryConfig) -> Path:
        raw = (history_cfg.config_dir or "").strip()
        if raw:
            return Path(raw).expanduser()
        env_dir = (os.environ.get("CLAUDE_CONFIG_DIR") or "").strip()
        if env_dir:
            return Path(env_dir).expanduser()
        return Path.home() / ".claude"

    @staticmethod
    def _resolve_jsonl_path(
        config_dir: Path,
        workspace: str,
        session_id: str,
    ) -> Optional[Path]:
        sid = (session_id or "").strip()
        if not sid:
            return None
        ws = (workspace or "").strip()
        candidates: List[Path] = []
        if ws:
            encoded = CliClaude._encode_project_dir(ws)
            project_dir = config_dir / "projects" / encoded
            candidates.extend([
                project_dir / f"{sid}.jsonl",
                project_dir / "sessions" / f"{sid}.jsonl",
            ])
        projects_root = config_dir / "projects"
        if projects_root.is_dir():
            for project_dir in projects_root.iterdir():
                if not project_dir.is_dir():
                    continue
                candidates.extend([
                    project_dir / f"{sid}.jsonl",
                    project_dir / "sessions" / f"{sid}.jsonl",
                ])
        seen: set[str] = set()
        for path in candidates:
            key = str(path)
            if key in seen:
                continue
            seen.add(key)
            if path.is_file():
                return path
        return None

    @staticmethod
    def _resolve_history_config(cli_cfg: GraphNodeCliConfig) -> GraphNodeCliHistoryConfig:
        history = cli_cfg.session.history
        if history.provider != "none":
            return history
        if cli_cfg.session.enabled:
            return GraphNodeCliHistoryConfig(
                provider="claude_code_jsonl",
                config_dir=history.config_dir,
            )
        return history

    @staticmethod
    def _parse_timestamp(raw: Any) -> Optional[datetime]:
        if raw is None:
            return None
        if isinstance(raw, (int, float)):
            ts = float(raw)
            if ts > 1e12:
                ts /= 1000.0
            try:
                return datetime.fromtimestamp(ts)
            except (OSError, OverflowError, ValueError):
                return None
        text = str(raw).strip()
        if not text:
            return None
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(text.replace("+00:00", "Z"), fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None

    @staticmethod
    def _extract_text_content(content: Any) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: List[str] = []
            for block in content:
                if isinstance(block, str):
                    parts.append(block)
                    continue
                if not isinstance(block, dict):
                    continue
                block_type = str(block.get("type") or "").strip().lower()
                if block_type in {"text", "output_text"}:
                    parts.append(str(block.get("text") or block.get("content") or "").strip())
                elif block_type == "tool_result":
                    parts.append(str(block.get("content") or "").strip())
            return "\n\n".join(p for p in parts if p)
        if isinstance(content, dict):
            return str(content.get("text") or content.get("content") or "").strip()
        return str(content).strip()

    @staticmethod
    def _tool_use_to_tool_calls(blocks: List[Any]) -> Tuple[str, Optional[List[ToolCall]]]:
        text_parts: List[str] = []
        tool_calls: List[ToolCall] = []
        for block in blocks:
            if not isinstance(block, dict):
                continue
            block_type = str(block.get("type") or "").strip().lower()
            if block_type == "text":
                part = str(block.get("text") or "").strip()
                if part:
                    text_parts.append(part)
            elif block_type == "tool_use":
                tool_id = str(block.get("id") or "").strip()
                name = str(block.get("name") or "tool").strip()
                tool_input = block.get("input")
                if not isinstance(tool_input, dict):
                    tool_input = {"input": tool_input}
                tool_calls.append(
                    ToolCall(
                        id=tool_id or f"tool_{len(tool_calls)}",
                        function=Function(name=name, arguments=tool_input),
                    )
                )
        return "\n\n".join(text_parts), (tool_calls or None)

    @staticmethod
    def _messages_from_user_payload(
        payload: Dict[str, Any],
        record: Dict[str, Any],
        tool_names: Dict[str, str],
        created_at: Optional[datetime],
    ) -> List[Message]:
        out: List[Message] = []
        subtype = str(record.get("subtype") or payload.get("subtype") or "").strip().lower()
        if subtype in {"command", "command_output", "hook_result", "system_caveat"}:
            return out
        content_raw = payload.get("content")
        if isinstance(content_raw, str):
            text = content_raw.strip()
            if text:
                out.append(Message(role=Role.USER, content=text, create_time=created_at))
            return out
        if not isinstance(content_raw, list):
            text = CliClaude._extract_text_content(content_raw)
            if text:
                out.append(Message(role=Role.USER, content=text, create_time=created_at))
            return out
        for block in content_raw:
            if isinstance(block, str):
                if block.strip():
                    out.append(Message(role=Role.USER, content=block.strip(), create_time=created_at))
                continue
            if not isinstance(block, dict):
                continue
            block_type = str(block.get("type") or "").strip().lower()
            if block_type == "tool_result":
                tool_use_id = str(
                    block.get("tool_use_id") or block.get("toolUseId") or ""
                ).strip()
                tool_content = block.get("content")
                if isinstance(tool_content, list):
                    body = CliClaude._extract_text_content(tool_content)
                else:
                    body = str(tool_content or "").strip()
                if body:
                    msg = Message.tool_result_message(
                        content=body,
                        name=tool_names.get(tool_use_id, "tool"),
                        tool_call_id=tool_use_id or f"tool_{len(out)}",
                    )
                    if created_at:
                        msg.create_time = created_at
                    out.append(msg)
            elif block_type in {"text", "output_text"}:
                part = str(block.get("text") or block.get("content") or "").strip()
                if part:
                    out.append(Message(role=Role.USER, content=part, create_time=created_at))
        return out

    @staticmethod
    def _parse_jsonl(path: Path) -> List[Message]:
        messages: List[Message] = []
        tool_names: Dict[str, str] = {}
        with path.open("r", encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, start=1):
                text = line.strip()
                if not text:
                    continue
                try:
                    record = json.loads(text)
                except json.JSONDecodeError:
                    logging.debug("Skip invalid JSONL line %s:%s", path, line_no)
                    continue
                if not isinstance(record, dict):
                    continue
                record_type = str(record.get("type") or "").strip().lower()
                created_at = CliClaude._parse_timestamp(
                    record.get("timestamp")
                    or record.get("createdAt")
                    or record.get("isoTimestamp")
                )
                if record_type == "user":
                    payload = record.get("message") if isinstance(record.get("message"), dict) else record
                    role = str(payload.get("role") or "user").strip().lower()
                    if role != "user":
                        continue
                    messages.extend(
                        CliClaude._messages_from_user_payload(payload, record, tool_names, created_at)
                    )
                elif record_type == "assistant":
                    payload = record.get("message") if isinstance(record.get("message"), dict) else record
                    content_raw = payload.get("content")
                    if isinstance(content_raw, list):
                        text, tool_calls = CliClaude._tool_use_to_tool_calls(content_raw)
                        if tool_calls:
                            for tc in tool_calls:
                                tool_names[tc.id] = tc.function.name
                            messages.append(
                                Message(
                                    role=Role.ASSISTANT,
                                    content=text,
                                    tool_calls=tool_calls,
                                    create_time=created_at,
                                )
                            )
                        elif text:
                            messages.append(Message(role=Role.ASSISTANT, content=text, create_time=created_at))
                    else:
                        content = CliClaude._extract_text_content(content_raw)
                        if content:
                            messages.append(Message(role=Role.ASSISTANT, content=content, create_time=created_at))
                elif record_type == "tool_result":
                    result = record.get("toolUseResult")
                    if not isinstance(result, dict):
                        result = record
                    tool_use_id = str(result.get("tool_use_id") or result.get("toolUseId") or "").strip()
                    tool_content = CliClaude._extract_text_content(result.get("content"))
                    if not tool_content:
                        continue
                    messages.append(
                        Message.tool_result_message(
                            content=tool_content,
                            name=tool_names.get(tool_use_id, "tool"),
                            tool_call_id=tool_use_id or f"tool_{len(messages)}",
                        )
                    )
                    if created_at and messages[-1].create_time is None:
                        messages[-1].create_time = created_at
        return messages

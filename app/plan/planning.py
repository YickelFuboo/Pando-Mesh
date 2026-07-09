"""Planning：LLM 建图与 Judge 调用。"""
import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, Dict, List, Optional, Tuple
from app.config.settings import settings
from app.llms.chat_models.models_config import models_config
from app.llms.fallback import call_with_llm_fallback
from app.llms.prompts.prompt_template_load import get_prompt_template
from app.runtime.abort import RunAbortController
from app.graph.graph_parse import (
    normalize_graph_cli_executors,
    parse_planning_llm_response,
)
from app.graph.plan_graph import (
    DirectExecGraph,
    EdgeCondition,
    GraphNode,
    PlanGraphPhase,
    PlanGraphState,
)
from app.third_agent.register.register import AgentRegistry

PLAN_MAX_GRAPH_NODES = 12
_LLM_ABORT_POLL_SEC = 0.2

PLANNING_PROMPT_USER = "PLANNING_USER.md"
PLANNING_PROMPT_JUDGE_USER = "JUDGE_USER.md"
PLANNING_PROMPT_SYSTEM = "AGENT.md"

_agent_registry = AgentRegistry()


def _agent_catalog_text() -> str:
    catalog = _agent_registry.catalog_text()
    return catalog + "\n- shell: 自定义 shell / commands 步骤"


class PlanningLLMService:
    """LLM 建图与 Judge（供 WorkflowService 使用）。"""

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        abort_controller: Optional[RunAbortController] = None,
        on_stream_delta: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> None:
        self._provider = provider
        self._model = model
        self._abort_controller = abort_controller
        self._on_stream_delta = on_stream_delta

    def is_available(self) -> bool:
        return models_config.is_available()

    def _model_pairs(self) -> List[Tuple[str, str]]:
        return models_config.fallback_pairs(self._provider, self._model)

    def _is_aborted(self) -> bool:
        ctrl = self._abort_controller
        return ctrl is not None and ctrl.is_aborted()

    def _prompt_dir(self) -> str:
        return str(settings.prompts_dir)

    def _system_prompt(self) -> str:
        return get_prompt_template(self._prompt_dir(), PLANNING_PROMPT_SYSTEM, {}).strip()

    async def generate_graph(self, user_goal: str) -> Tuple[str, Optional[DirectExecGraph]]:
        params = {
            "user_goal": user_goal,
            "agent_catalog": _agent_catalog_text(),
            "plan_max_graph_nodes": PLAN_MAX_GRAPH_NODES,
        }
        user = get_prompt_template(self._prompt_dir(), PLANNING_PROMPT_USER, params).strip()

        async def _call(llm: Any) -> Tuple[str, Optional[DirectExecGraph]]:
            return await self._planning_with_llm(llm, user)

        result, _ = await call_with_llm_fallback(self._model_pairs(), _call)
        return result

    async def apply_generated_graph(
        self,
        state: PlanGraphState,
        goal: str,
        explanation: str,
        graph: DirectExecGraph,
    ) -> PlanGraphState:
        state.user_goal = goal
        state.plan_graph = graph
        state.phase = PlanGraphPhase.IDLE
        state.running_node_ids = []
        return state

    async def judge_callback(
        self,
        graph_node: GraphNode,
        node_output: str,
        pre_outputs: Dict[str, str],
        user_goal: str,
    ) -> EdgeCondition:
        result, _ = await call_with_llm_fallback(
            self._model_pairs(),
            lambda llm: self._judge_route_with_llm(
                llm, graph_node, node_output, pre_outputs, user_goal
            ),
        )
        return result

    async def _planning_with_llm(
        self,
        llm: Any,
        user_question: str,
    ) -> Tuple[str, Optional[DirectExecGraph]]:
        system_prompt = self._system_prompt()
        if not system_prompt:
            raise RuntimeError(f"Planning system prompt missing: {settings.prompts_dir / PLANNING_PROMPT_SYSTEM}")

        llm_task = asyncio.create_task(
            self._collect_stream(
                llm.chat_stream(
                    system_prompt=system_prompt,
                    user_question=user_question,
                    history=[],
                    temperature=0.2,
                )
            )
        )
        try:
            while not llm_task.done():
                if self._is_aborted():
                    llm_task.cancel()
                    try:
                        await llm_task
                    except asyncio.CancelledError:
                        pass
                    return "", None
                await asyncio.sleep(_LLM_ABORT_POLL_SEC)
            chunks = llm_task.result()
        except asyncio.CancelledError:
            return "", None

        if self._is_aborted():
            return "", None

        raw = "".join(chunks)
        explanation, exec_graph = parse_planning_llm_response(raw)
        if exec_graph is None:
            return "", None
        exec_graph = normalize_graph_cli_executors(exec_graph)
        plan_text = explanation.strip() or exec_graph.format_summary()
        return plan_text, exec_graph

    async def _collect_stream(self, stream: Any) -> List[str]:
        chunks: List[str] = []
        async for chunk in stream:
            if self._is_aborted():
                break
            if isinstance(chunk, str) and chunk:
                chunks.append(chunk)
                if self._on_stream_delta is not None:
                    await self._on_stream_delta(chunk)
        return chunks

    async def _judge_route_with_llm(
        self,
        llm: Any,
        graph_node: GraphNode,
        node_output: str,
        pre_outputs: Dict[str, str],
        user_goal: str,
    ) -> EdgeCondition:
        params = {
            "user_goal": user_goal,
            "pre_outputs_text": "\n\n".join(f"[{k}]\n{v}" for k, v in pre_outputs.items()) or "(无)",
            "reviewer_label": graph_node.label,
            "review_output": node_output,
        }
        user = get_prompt_template(self._prompt_dir(), PLANNING_PROMPT_JUDGE_USER, params).strip()
        llm_task = asyncio.create_task(
            llm.chat(
                system_prompt=self._system_prompt(),
                user_question=user,
                history=[],
                temperature=0.1,
            )
        )
        try:
            while not llm_task.done():
                if self._is_aborted():
                    llm_task.cancel()
                    try:
                        await llm_task
                    except asyncio.CancelledError:
                        pass
                    return EdgeCondition.REJECT
                await asyncio.sleep(_LLM_ABORT_POLL_SEC)
            text = llm_task.result()
        except asyncio.CancelledError:
            return EdgeCondition.REJECT
        text = (text or "").strip().lower()
        if "reject" in text or any(k in text for k in ("不通过", "驳回", "返工", "未通过")):
            return EdgeCondition.REJECT
        return EdgeCondition.PASS

from collections.abc import Awaitable, Callable
from typing import Dict, Optional
from app.common.json_utils import extract_json_object
from app.config.settings import settings
from app.runtime.abort import RunAbortController
from app.graph.plan_graph import EdgeCondition, GraphNode


def judge_route_from_output(
    graph_node: GraphNode,
    node_output: str,
    pre_outputs: Dict[str, str],
    user_goal: str,
) -> EdgeCondition:
    """审查路由：从 CLI 输出 JSON 解析 verdict。"""
    parsed = extract_json_object(node_output)
    if parsed:
        verdict = str(parsed.get("verdict") or "").strip().lower()
        if verdict == "reject":
            return EdgeCondition.REJECT
        if verdict == "pass":
            return EdgeCondition.PASS
    return EdgeCondition.PASS


def resolve_judge_mode(workflow_mode: Optional[str] = None) -> str:
    mode = (workflow_mode or settings.judge_mode or "auto").strip().lower()
    if mode not in {"auto", "llm", "json"}:
        return "auto"
    return mode


def build_judge_callback(
    *,
    judge_mode: Optional[str] = None,
    llm_provider: Optional[str] = None,
    llm_model: Optional[str] = None,
    abort_controller: Optional[RunAbortController] = None,
) -> Callable[[GraphNode, str, Dict[str, str], str], Awaitable[EdgeCondition]]:
    from app.plan.planning import PlanningLLMService

    mode = resolve_judge_mode(judge_mode)
    planner = PlanningLLMService(
        provider=llm_provider,
        model=llm_model,
        abort_controller=abort_controller,
    )
    llm_available = planner.is_available()

    async def _json(
        graph_node: GraphNode,
        node_output: str,
        pre_outputs: Dict[str, str],
        user_goal: str,
    ) -> EdgeCondition:
        return judge_route_from_output(graph_node, node_output, pre_outputs, user_goal)

    async def _llm(
        graph_node: GraphNode,
        node_output: str,
        pre_outputs: Dict[str, str],
        user_goal: str,
    ) -> EdgeCondition:
        return await planner.judge_callback(graph_node, node_output, pre_outputs, user_goal)

    if mode == "json":
        return _json
    if mode == "llm":
        if not llm_available:
            raise RuntimeError("Judge 模式为 llm，但 LLM 未配置")
        return _llm

    async def _auto(
        graph_node: GraphNode,
        node_output: str,
        pre_outputs: Dict[str, str],
        user_goal: str,
    ) -> EdgeCondition:
        json_route = judge_route_from_output(graph_node, node_output, pre_outputs, user_goal)
        if json_route == EdgeCondition.REJECT:
            return EdgeCondition.REJECT
        if llm_available:
            return await planner.judge_callback(graph_node, node_output, pre_outputs, user_goal)
        return json_route

    return _auto

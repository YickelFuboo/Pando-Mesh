import asyncio
import logging
import operator
import uuid
from collections.abc import Awaitable, Callable
from functools import partial
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional, TypedDict
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from app.config.settings import settings
from app.runtime.context import AgentContext, RuntimeContext
from app.runtime.message import Message
from app.workspace.refs import expand_session_placeholders
from app.graph.plan_graph import (
    DirectExecGraph,
    END_NODE,
    EdgeCondition,
    GraphNode,
    PlanGraphPhase,
    PlanGraphState,
)
from app.graph.agent_bridge import apply_run_result, build_history_request, build_run_request
from app.third_agent.executor.dispatch import ThirdAgentDispatcher
from app.graph.execution_pause import ExpandPause, HumanGatePause
from app.graph.expand_planner import ExpandPlannerCallback, uses_native_llm_planner
from app.graph.graph_expand import parse_expansion_result
from app.graph.judge import build_judge_callback
from app.graph.node_config import GraphNodeExpandConfig

PersistPlanGraphCallback = Callable[[PlanGraphState, str], Awaitable[None]]
JudgeRouteCallback = Callable[
    [GraphNode, str, Dict[str, str], str],
    Awaitable[EdgeCondition],
]

_CHECKPOINTER: Optional[AsyncSqliteSaver] = None
_CHECKPOINTER_CONN: Optional[aiosqlite.Connection] = None
_CHECKPOINTER_LOCK = asyncio.Lock()
_PLAN_RUNNING_LOCK = asyncio.Lock()


def _merge_str_dict(left: Optional[Dict[str, str]], right: Optional[Dict[str, str]]) -> Dict[str, str]:
    merged = dict(left or {})
    merged.update(right or {})
    return merged


def _merge_int_dict(left: Optional[Dict[str, int]], right: Optional[Dict[str, int]]) -> Dict[str, int]:
    merged = dict(left or {})
    merged.update(right or {})
    return merged


def _sync_plan_running(plan_graph: PlanGraphState, running_ids: List[str]) -> None:
    plan_graph.running_node_ids = list(running_ids)


async def _get_checkpointer() -> AsyncSqliteSaver:
    global _CHECKPOINTER, _CHECKPOINTER_CONN
    async with _CHECKPOINTER_LOCK:
        if _CHECKPOINTER is None:
            db_path = settings.data_dir / "planning_checkpoints.sqlite"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            _CHECKPOINTER_CONN = await aiosqlite.connect(str(db_path))
            _CHECKPOINTER = AsyncSqliteSaver(_CHECKPOINTER_CONN)
        return _CHECKPOINTER


def _lg_dest(to_id: str) -> str:
    return END if to_id == END_NODE else to_id


def _execution_thread_id(session_id: str, start: str, *, partial: bool) -> str:
    sid = (session_id or "unknown").strip() or "unknown"
    run_token = uuid.uuid4().hex[:12]
    if partial:
        return f"{sid}:from:{start}:{run_token}"
    return f"{sid}:run:{run_token}"


class LangGraphRunState(TypedDict, total=False):
    user_goal: str
    node_outputs: Annotated[Dict[str, str], _merge_str_dict]
    pre_node_reject_infos: Annotated[Dict[str, str], _merge_str_dict]
    node_iterations: Annotated[Dict[str, int], _merge_int_dict]
    node_routes: Annotated[Dict[str, str], _merge_str_dict]
    summary_parts: Annotated[List[str], operator.add]
    aborted: bool
    error_message: str


class LangGraphExecutor:

    @staticmethod
    def _resolve_start_node(graph: DirectExecGraph, start_node_id: Optional[str]) -> str:
        start = (start_node_id or graph.entry_node_id or "").strip()
        if not start or start not in graph.nodes:
            raise ValueError(f"起始节点不存在: {start or '(空)'}")
        return start

    @staticmethod
    def _validate_partial_start(plan_graph: PlanGraphState, graph: DirectExecGraph, start: str) -> None:
        if start == graph.entry_node_id:
            return
        missing = [
            nid for nid in sorted(graph.predecessors_for_partial_start(start))
            if nid in graph.nodes and nid not in plan_graph.node_outputs
        ]
        if not missing:
            return
        labels = [
            (graph.nodes[nid].label if nid in graph.nodes else None) or nid
            for nid in missing
        ]
        node = graph.nodes[start]
        label = node.label or start
        raise ValueError(
            f"无法从步骤「{label}」开始：上游步骤 {labels} 尚无产出，"
            "请先完整执行。"
        )

    @staticmethod
    async def run(
        plan_graph: PlanGraphState,
        agent_ctx: AgentContext,
        runtime_ctx: RuntimeContext,
        persist_plangraph_callback: Optional[PersistPlanGraphCallback] = None,
        judge_route_callback: Optional[JudgeRouteCallback] = None,
        expand_planner_callback: Optional[ExpandPlannerCallback] = None,
        start_node_id: Optional[str] = None,
    ) -> str:
        if runtime_ctx.is_aborted():
            raise ValueError("编排已中止")

        graph = plan_graph.resolve_graph()
        if graph is None:
            raise ValueError("编排方案无效或缺失，无法执行。")

        start = LangGraphExecutor._resolve_start_node(graph, start_node_id)

        partial = bool((start_node_id or "").strip()) and not graph.is_entry_node(start or "")
        if partial:
            LangGraphExecutor._validate_partial_start(plan_graph, graph, start)

        judge_cb = judge_route_callback or build_judge_callback()
        initial: LangGraphRunState = {
            "user_goal": plan_graph.user_goal,
            "node_outputs": dict(plan_graph.node_outputs),
            "pre_node_reject_infos": dict(plan_graph.pre_node_reject_infos),
            "node_iterations": dict(plan_graph.node_iterations),
            "node_routes": {},
            "summary_parts": [],
            "aborted": False,
            "error_message": "",
        }

        plan_graph.phase = PlanGraphPhase.EXECUTING
        start_label = graph.nodes[start].label or start
        if persist_plangraph_callback is not None:
            if partial and start != graph.entry_node_id:
                await persist_plangraph_callback(
                    plan_graph,
                    f"从步骤「{start_label}」开始执行编排方案…",
                )
            else:
                await persist_plangraph_callback(plan_graph, "正在执行编排方案…")

        compiled = LangGraphExecutor._build_workflow(
            plan_graph,
            agent_ctx,
            runtime_ctx,
            persist_plangraph_callback,
            judge_cb,
            expand_planner_callback=expand_planner_callback,
            start_node_id=start,
        ).compile(checkpointer=await _get_checkpointer())

        thread_id = _execution_thread_id(agent_ctx.session_id or "", start, partial=partial)
        final_result = await compiled.ainvoke(
            initial,
            {"configurable": {"thread_id": thread_id}},
        )

        if not isinstance(final_result, dict):
            return "(无执行结果)"
        plan_graph.node_outputs = dict(final_result.get("node_outputs") or {})
        plan_graph.pre_node_reject_infos = dict(final_result.get("pre_node_reject_infos") or {})
        plan_graph.node_iterations = dict(final_result.get("node_iterations") or {})
        plan_graph.running_node_ids = []
        if final_result.get("aborted"):
            plan_graph.phase = PlanGraphPhase.IDLE
        elif plan_graph.phase not in (PlanGraphPhase.AWAITING_HUMAN, PlanGraphPhase.AWAITING_EXPAND):
            plan_graph.phase = PlanGraphPhase.DONE
        if persist_plangraph_callback is not None:
            done_msg = "编排已中止。" if final_result.get("aborted") else "编排执行完成。"
            await persist_plangraph_callback(plan_graph, done_msg)

        if final_result.get("error_message"):
            raise ValueError(str(final_result["error_message"]))
        summary_parts = final_result.get("summary_parts") or []
        return "\n\n".join(summary_parts) if summary_parts else "(无执行结果)"

    @staticmethod
    def _build_workflow(
        plan_graph: PlanGraphState,
        agent_ctx: AgentContext,
        runtime_ctx: RuntimeContext,
        persist_plangraph_callback: Optional[PersistPlanGraphCallback],
        judge_route_callback: JudgeRouteCallback,
        expand_planner_callback: Optional[ExpandPlannerCallback] = None,
        start_node_id: Optional[str] = None,
    ) -> StateGraph:
        graph = plan_graph.resolve_graph()
        if graph is None:
            raise ValueError("编排方案无效或缺失，无法执行。")

        entry = LangGraphExecutor._resolve_start_node(graph, start_node_id)

        def route_after(node_id: str):
            def _route(run_state: LangGraphRunState) -> Any:
                if run_state.get("aborted"):
                    return END
                try:
                    routes = run_state.get("node_routes") or {}
                    route_value = routes.get(node_id) or EdgeCondition.ALWAYS.value
                    cond = EdgeCondition(route_value)
                except ValueError:
                    cond = EdgeCondition.ALWAYS
                next_ids = graph.resolve_next_node_ids(node_id, cond)
                if not next_ids:
                    return END
                dests = [_lg_dest(nid) for nid in next_ids]
                if len(dests) == 1:
                    return dests[0]
                return dests
            return _route

        workflow: StateGraph = StateGraph(LangGraphRunState)
        for graph_node in graph.nodes.values():
            workflow.add_node(
                graph_node.id,
                partial(
                    LangGraphExecutor._run_graph_node,
                    plan_graph=plan_graph,
                    graph_node=graph_node,
                    agent_ctx=agent_ctx,
                    runtime_ctx=runtime_ctx,
                    persist_plangraph_callback=persist_plangraph_callback,
                    judge_route_callback=judge_route_callback,
                    expand_planner_callback=expand_planner_callback,
                ),
            )
        workflow.add_edge(START, entry)
        for node_id in graph.nodes:
            out_edges = graph.outgoing_edges(node_id)
            if not out_edges:
                workflow.add_edge(node_id, END)
                continue
            if graph.has_review_outgoing_edges(node_id):
                path_map = {END: END}
                for edge in out_edges:
                    dest = _lg_dest(edge.to_id)
                    path_map[dest] = dest
                workflow.add_conditional_edges(node_id, route_after(node_id), path_map)
            else:
                for edge in out_edges:
                    workflow.add_edge(node_id, _lg_dest(edge.to_id))
        return workflow

    @staticmethod
    async def _run_graph_node(
        run_state: LangGraphRunState,
        plan_graph: PlanGraphState,
        graph_node: GraphNode,
        agent_ctx: AgentContext,
        runtime_ctx: RuntimeContext,
        persist_plangraph_callback: Optional[PersistPlanGraphCallback],
        judge_route_callback: JudgeRouteCallback,
        expand_planner_callback: Optional[ExpandPlannerCallback] = None,
    ) -> Dict[str, Any]:
        graph = plan_graph.resolve_graph()
        if graph is None:
            raise ValueError("编排方案无效或缺失，无法执行。")

        if runtime_ctx.is_aborted():
            return {"aborted": True, "error_message": "编排已中止"}

        current_node_id = graph_node.id
        iterations = dict(run_state.get("node_iterations") or {})
        node_iterations = iterations.get(current_node_id, 0) + 1
        if node_iterations > graph_node.max_iterations:
            plan_graph.node_iterations[current_node_id] = node_iterations
            async with _PLAN_RUNNING_LOCK:
                running_ids = list(plan_graph.running_node_ids or [])
                if current_node_id in running_ids:
                    running_ids.remove(current_node_id)
                _sync_plan_running(plan_graph, running_ids)
            msg = f"步骤「{graph_node.label}」超过最大重试 {graph_node.max_iterations} 次。"
            if persist_plangraph_callback is not None:
                await persist_plangraph_callback(plan_graph, f"{msg}编排已停止。")
            raise RuntimeError(msg)

        plan_graph.node_iterations[current_node_id] = node_iterations
        async with _PLAN_RUNNING_LOCK:
            running_ids = list(plan_graph.running_node_ids or [])
            if current_node_id not in running_ids:
                running_ids.append(current_node_id)
            _sync_plan_running(plan_graph, running_ids)
            plan_graph.phase = PlanGraphPhase.EXECUTING
            if graph_node.is_human():
                executor_label = "人工"
            elif graph_node.is_expand():
                executor_label = "任务分裂"
            elif graph_node.is_fork():
                executor_label = "分发"
            elif graph_node.is_cli():
                executor_label = "CLI"
            else:
                executor_label = "不支持"
            if persist_plangraph_callback is not None:
                await persist_plangraph_callback(
                    plan_graph,
                    f"正在执行步骤「{graph_node.label}」（{executor_label}）…",
                )

        node_outputs = dict(run_state.get("node_outputs") or {})
        pre_node_reject_infos = dict(run_state.get("pre_node_reject_infos") or {})
        pred_ids = graph.predecessor_ids(current_node_id)
        pre_outputs = (
            {pid: node_outputs[pid] for pid in pred_ids if pid in node_outputs}
            if pred_ids
            else {nid: out for nid, out in node_outputs.items() if nid != current_node_id}
        )

        if graph_node.is_human():
            if not graph.has_review_outgoing_edges(current_node_id):
                raise ValueError(f"人工节点「{graph_node.label}」需配置 pass / reject 出边")
            summary = LangGraphExecutor._build_human_review_summary(
                graph_node,
                run_state.get("user_goal") or "",
                pre_outputs,
                pre_node_reject_infos.get(current_node_id, ""),
                agent_ctx,
            )
            async with _PLAN_RUNNING_LOCK:
                running_ids = list(plan_graph.running_node_ids or [])
                if current_node_id in running_ids:
                    running_ids.remove(current_node_id)
                _sync_plan_running(plan_graph, running_ids)
            plan_graph.pending_gate = {
                "node_id": current_node_id,
                "label": graph_node.label or current_node_id,
                "summary": summary,
            }
            plan_graph.phase = PlanGraphPhase.AWAITING_HUMAN
            if persist_plangraph_callback is not None:
                await persist_plangraph_callback(
                    plan_graph,
                    f"步骤「{graph_node.label}」等待人工确认。\n\n{summary[:1200]}",
                )
            raise HumanGatePause(current_node_id)

        if graph_node.is_expand():
            expand_cfg = graph_node.executor.expand
            source_id = (expand_cfg.source_node_id if expand_cfg else "").strip()
            if uses_native_llm_planner(expand_cfg):
                if expand_planner_callback is None:
                    raise ValueError(f"分裂节点「{graph_node.label}」需要 LLM 扩展规划，但未配置模型")
                if persist_plangraph_callback is not None:
                    await persist_plangraph_callback(
                        plan_graph,
                        f"步骤「{graph_node.label}」正在调用 LLM 生成扩展计划…",
                    )
                source_output = await expand_planner_callback(
                    graph,
                    graph_node,
                    expand_cfg or GraphNodeExpandConfig(),
                    agent_ctx,
                    node_outputs,
                )
                plan_graph.node_outputs[current_node_id] = source_output
                source_id = current_node_id
            else:
                if not source_id:
                    if not pred_ids:
                        raise ValueError(f"分裂节点「{graph_node.label}」无法确定任务来源")
                    source_id = pred_ids[0]
                source_output = node_outputs.get(source_id) or pre_outputs.get(source_id) or ""
            expansion = parse_expansion_result(
                source_output,
                mode=(expand_cfg.mode if expand_cfg else "auto"),
                default_lane_template_id=(expand_cfg.default_lane_template_id if expand_cfg else ""),
            )
            async with _PLAN_RUNNING_LOCK:
                running_ids = list(plan_graph.running_node_ids or [])
                if current_node_id in running_ids:
                    running_ids.remove(current_node_id)
                _sync_plan_running(plan_graph, running_ids)
            expand_count = len(expansion.get("lanes") or expansion.get("tasks") or [])
            plan_graph.pending_expand = {
                "node_id": current_node_id,
                "source_node_id": source_id,
                "merge_label": (expand_cfg.merge_label if expand_cfg else "任务汇聚"),
                "mode": expansion.get("mode") or "task",
                "tasks": expansion.get("tasks") or [],
                "lanes": expansion.get("lanes") or [],
            }
            plan_graph.phase = PlanGraphPhase.AWAITING_EXPAND
            if persist_plangraph_callback is not None:
                await persist_plangraph_callback(
                    plan_graph,
                    f"步骤「{graph_node.label}」已解析 {expand_count} 个分支，等待确认分裂。",
                )
            raise ExpandPause(current_node_id)

        if graph_node.is_fork():
            output = "并行分发"
        else:
            output = await LangGraphExecutor.run_node(
                plan_graph,
                graph_node,
                run_state.get("user_goal") or "",
                agent_ctx,
                runtime_ctx,
                pre_outputs,
                pre_node_reject_infos.get(current_node_id, ""),
            )

        last_route = EdgeCondition.ALWAYS.value
        if graph.has_review_outgoing_edges(current_node_id) and not graph_node.is_human():
            route = await judge_route_callback(
                graph_node,
                output,
                pre_outputs,
                run_state.get("user_goal") or "",
            )
            last_route = route.value
            if route == EdgeCondition.REJECT:
                reject_msg = f"步骤「{graph_node.label}」驳回意见：\n{output}"
                for edge in graph.outgoing_edges(current_node_id, EdgeCondition.REJECT):
                    reject_target_id = edge.to_id
                    if reject_target_id in graph.nodes:
                        pre_node_reject_infos[reject_target_id] = reject_msg

        async with _PLAN_RUNNING_LOCK:
            running_ids = list(plan_graph.running_node_ids or [])
            if current_node_id in running_ids:
                running_ids.remove(current_node_id)
            _sync_plan_running(plan_graph, running_ids)
            plan_graph.node_outputs[current_node_id] = output
            plan_graph.node_iterations[current_node_id] = node_iterations
            plan_graph.pre_node_reject_infos = pre_node_reject_infos
            if persist_plangraph_callback is not None:
                done_snippet = output[:500] + ("…" if len(output) > 500 else "")
                await persist_plangraph_callback(
                    plan_graph,
                    f"步骤「{graph_node.label}」已完成。\n\n{done_snippet}",
                )

        result: LangGraphRunState = {
            "node_outputs": {current_node_id: output},
            "node_iterations": {current_node_id: node_iterations},
            "pre_node_reject_infos": pre_node_reject_infos,
            "summary_parts": [f"### {graph_node.label}\n{output[:2000]}"],
        }
        if graph.has_review_outgoing_edges(current_node_id):
            result["node_routes"] = {current_node_id: last_route}
        return result

    @staticmethod
    async def _emit_runtime_message(runtime_ctx: RuntimeContext, msg: Message) -> None:
        seen: set[int] = set()
        for cb in (runtime_ctx.push_history_callback, runtime_ctx.notify_user_callback):
            if cb is None or id(cb) in seen:
                continue
            seen.add(id(cb))
            await cb(msg)

    @staticmethod
    def _expand_session_text(text: str, agent_ctx: Optional[AgentContext]) -> str:
        if not text or agent_ctx is None:
            return text
        return expand_session_placeholders(
            text,
            workspace_path=agent_ctx.workspace_path,
            requirement_id=agent_ctx.requirement_id,
        )

    @staticmethod
    def _build_cli_task(
        graph_node: GraphNode,
        user_goal: str,
        pre_outputs: Dict[str, str],
        feedback: str = "",
        agent_ctx: Optional[AgentContext] = None,
    ) -> str:
        parts: List[str] = []
        goal = LangGraphExecutor._expand_session_text((user_goal or "").strip(), agent_ctx)
        label = (graph_node.label or "").strip()
        node_id = (graph_node.id or "").strip()
        step_task = LangGraphExecutor._expand_session_text((graph_node.task or "").strip(), agent_ctx)
        if goal:
            parts.append(f"用户目标：{goal}")
        if label or node_id:
            if label and node_id:
                parts.append(f"当前步骤：{label}（{node_id}）")
            else:
                parts.append(f"当前步骤：{label or node_id}")
        if step_task:
            parts.append(f"步骤说明：{step_task}")
        if pre_outputs:
            parts.append("前置步骤产出：")
            for nid, out in pre_outputs.items():
                parts.append(f"[{nid}]\n{out}")
        if feedback:
            parts.append(f"修订意见：\n{feedback}")
        return "\n\n".join(parts).strip() or step_task or goal

    @staticmethod
    def _build_human_review_summary(
        graph_node: GraphNode,
        user_goal: str,
        pre_outputs: Dict[str, str],
        feedback: str = "",
        agent_ctx: Optional[AgentContext] = None,
    ) -> str:
        parts = ["## 待人工确认"]
        parts.append(LangGraphExecutor._build_cli_task(
            graph_node, user_goal, pre_outputs, feedback, agent_ctx
        ))
        return "\n\n".join(parts).strip()

    @staticmethod
    async def run_node(
        plan_graph: PlanGraphState,
        graph_node: GraphNode,
        user_goal: str,
        agent_ctx: AgentContext,
        runtime_ctx: RuntimeContext,
        pre_outputs: Dict[str, str],
        feedback: str = "",
    ) -> str:
        if not graph_node.is_cli():
            raise ValueError(
                f"节点「{graph_node.label or graph_node.id}」未配置 CLI 执行器；"
                "MomaPipeline 仅支持 CLI 节点（Claude Code、Codex 等）。"
            )

        text_task = LangGraphExecutor._build_cli_task(
            graph_node, user_goal, pre_outputs, feedback, agent_ctx
        )
        cli_cfg = graph_node.executor.cli
        session_hint = ""
        if cli_cfg and cli_cfg.session.enabled:
            sid = (plan_graph.node_session_id.get(graph_node.id) or "").strip()
            session_hint = f"，CLI Session: {sid or '(新建)'}"
        mode = cli_cfg.run_mode() if cli_cfg else ""
        start_notice = f"开始执行步骤「{graph_node.label}」（CLI/{mode}{session_hint}）\n\n{text_task}"
        if runtime_ctx.push_history_callback:
            await runtime_ctx.push_history_callback(Message.assistant_message(start_notice))
        if runtime_ctx.notify_user_callback:
            await runtime_ctx.notify_user_callback(Message.assistant_message(start_notice))

        try:
            run_request = build_run_request(graph_node, plan_graph, text_task)
            run_result = await ThirdAgentDispatcher.run(
                run_request,
                agent_ctx,
                runtime_ctx,
            )
            result = apply_run_result(plan_graph, graph_node.id, run_result)
        except asyncio.CancelledError:
            raise
        except Exception:
            logging.exception("CLI node execution failed: %s", graph_node.id)
            raise

        stop_notice = f"步骤「{graph_node.label}」（CLI/{mode}）执行完毕\n\n{result}"
        await LangGraphExecutor._emit_runtime_message(
            runtime_ctx, Message.assistant_message(stop_notice)
        )
        return result

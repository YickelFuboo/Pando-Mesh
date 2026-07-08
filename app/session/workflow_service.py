import asyncio
import logging
from typing import Any, Dict, Optional
from app.runtime.abort import AbortReason, RunAbortController
from app.graph.execution_pause import ExpandPause, HumanGatePause
from app.graph.graph_expand import (
    apply_expansion_to_graph,
    dedupe_graph_edges,
    graph_has_disconnected_nodes,
    graph_has_duplicate_edges,
    graph_has_missing_node_refs,
    graph_needs_post_merge_restore,
    infer_lanes_from_expand_outputs,
    repair_lane_expand_graph,
    restore_post_merge_flow,
)
from app.graph.expand_planner import build_expand_planner_callback
from app.graph.langraph_executor import LangGraphExecutor
from app.graph.plan_graph import DirectExecGraph, EdgeCondition, PlanGraphPhase, PlanGraphState
from app.plan.planning import PlanningLLMService
from app.graph.judge import build_judge_callback
from app.runtime.context import AgentContext, RuntimeContext
from app.runtime.message import Message
from app.session.plan_mode import PlanMode, normalize_plan_mode
from app.session.session_plan import hydrate_session_graph
from app.session.template_store import WorkflowTemplateStore, apply_template_to_record
from app.session.workflow_store import WorkflowRecord, WorkflowStore
from app.maas.chat_models.models_config import models_config

logger = logging.getLogger(__name__)


class WorkflowService:
    def __init__(
        self,
        store: Optional[WorkflowStore] = None,
        template_store: Optional[WorkflowTemplateStore] = None,
    ) -> None:
        self._store = store or WorkflowStore()
        self._template_store = template_store or WorkflowTemplateStore()
        self._abort_controllers: Dict[str, RunAbortController] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    @property
    def store(self) -> WorkflowStore:
        return self._store

    async def _load_record(self, workflow_id: str) -> Optional[WorkflowRecord]:
        record = await self._store.get(workflow_id)
        if record is None:
            return None
        await hydrate_session_graph(record, self._template_store)
        return record

    def llm_status(self) -> Dict[str, Any]:
        from app.maas.chat_models.models_config import _models_path
        return {
            "available": models_config.is_available(),
            "models_file": str(_models_path()),
        }

    async def _append_message(self, record: WorkflowRecord, message: Message) -> None:
        record.messages.append(message.to_user_message())
        await self._store.save(record)

    async def _persist_plan_state(self, workflow_id: str, plan_state: PlanGraphState, summary: str) -> None:
        record = await self._store.get(workflow_id)
        if record is None:
            return
        record.plan_state = plan_state
        await self._store.save(record)
        text = (summary or "").strip()
        if text:
            await self._append_message(record, Message.assistant_message(text))

    def _planner_for(self, record: WorkflowRecord, abort: Optional[RunAbortController] = None) -> PlanningLLMService:
        async def on_delta(chunk: str) -> None:
            fresh = await self._store.get(record.workflow_id)
            if fresh is None:
                return
            last = fresh.messages[-1] if fresh.messages else None
            if last and last.get("role") == "assistant" and last.get("_streaming"):
                last["content"] = (last.get("content") or "") + chunk
            else:
                fresh.messages.append({
                    "role": "assistant",
                    "content": chunk,
                    "create_time": Message.assistant_message("").to_user_message()["create_time"],
                    "_streaming": True,
                })
            await self._store.save(fresh)

        return PlanningLLMService(
            provider=record.llm_provider or None,
            model=record.llm_model or None,
            abort_controller=abort,
            on_stream_delta=on_delta,
        )

    async def generate_graph(
        self,
        workflow_id: str,
        *,
        user_goal: Optional[str] = None,
        recreate: bool = False,
    ) -> WorkflowRecord:
        record = await self._load_record(workflow_id)
        if record is None:
            raise KeyError(workflow_id)
        if normalize_plan_mode(record.plan_mode) != PlanMode.DYNAMIC.value:
            raise ValueError("仅动态规划模式可使用 AI 生成拓扑")
        goal = (user_goal or record.user_goal or "").strip()
        if not goal:
            raise ValueError("请填写任务目标")
        planner = self._planner_for(record)
        if not planner.is_available():
            raise ValueError("LLM 未配置，请设置 data/models/chat_models.json 或环境变量 LLM_*")

        await self._append_message(record, Message.user_message(f"请为以下任务生成编排拓扑：\n{goal}"))
        explanation, graph = await planner.generate_graph(goal)
        if graph is None:
            raise ValueError("编排方案生成失败，请重试")
        if recreate:
            record.plan_state.clear_history()
        record.user_goal = goal
        record.plan_state = await planner.apply_generated_graph(record.plan_state, goal, explanation, graph)
        await self._store.save(record)
        summary = (
            "已生成编排方案，可在拓扑图中调整 CLI 配置。"
            f"\n\n{explanation}\n\n{graph.format_summary()}"
        )
        await self._append_message(record, Message.assistant_message(summary))
        fresh = await self._store.get(workflow_id)
        if fresh is None:
            raise KeyError(workflow_id)
        return fresh

    async def revise_node(
        self,
        workflow_id: str,
        node_id: str,
        *,
        feedback: str,
    ) -> WorkflowRecord:
        note = (feedback or "").strip()
        if not note:
            raise ValueError("请填写修正意见")
        if self.is_running(workflow_id):
            raise RuntimeError("工作流正在执行中")
        record = await self._load_record(workflow_id)
        if record is None:
            raise KeyError(workflow_id)
        phase = record.plan_state.phase
        if phase in (
            PlanGraphPhase.EXECUTING,
            PlanGraphPhase.AWAITING_HUMAN,
            PlanGraphPhase.AWAITING_EXPAND,
        ):
            raise ValueError("当前状态不可修正重跑，请先处理待确认事项")
        graph = record.plan_state.resolve_graph()
        if graph is None:
            raise ValueError("请先配置有效拓扑")
        key = (node_id or "").strip()
        graph_node = graph.nodes.get(key)
        if graph_node is None:
            raise ValueError(f"节点不存在: {node_id}")
        if not graph_node.is_cli():
            raise ValueError("仅 CLI 步骤支持修正重跑")
        previous_output = (record.plan_state.node_outputs.get(key) or "").strip()
        label = graph_node.label or key
        revision_text = f"人工修正意见：\n{note}"
        if previous_output:
            revision_text = f"{revision_text}\n\n上一次执行结果：\n{previous_output}"
        record.plan_state.clear_execution_from_node(key)
        record.plan_state.pre_node_reject_infos[key] = revision_text
        record.plan_state.phase = PlanGraphPhase.IDLE
        await self._append_message(
            record,
            Message.user_message(f"【修正步骤 {label}】\n{note}"),
        )
        await self._store.save(record)
        await self.execute(workflow_id, start_node_id=key)
        fresh = await self._store.get(workflow_id)
        if fresh is None:
            raise KeyError(workflow_id)
        return fresh

    async def init_from_template(self, workflow_id: str, template_id: str) -> WorkflowRecord:
        tpl_id = (template_id or "").strip()
        if not tpl_id:
            raise ValueError("template_id 不能为空")
        if self.is_running(workflow_id):
            raise RuntimeError("工作流正在执行中，请先停止后再初始化")
        template = await self._template_store.get(tpl_id)
        if template is None:
            raise KeyError(tpl_id)
        record = await self._store.get(workflow_id)
        if record is None:
            raise KeyError(workflow_id)
        if record.plan_state.phase == PlanGraphPhase.EXECUTING:
            raise RuntimeError("工作流正在执行中，请先停止后再初始化")
        apply_template_to_record(record, template)
        record.template_id = tpl_id
        record.plan_mode = PlanMode.TEMPLATE.value
        await self._store.save(record)
        fresh = await self._store.get(workflow_id)
        if fresh is None:
            raise KeyError(workflow_id)
        return fresh

    async def get_node_output(self, workflow_id: str, node_id: str) -> Dict[str, Any]:
        record = await self._load_record(workflow_id)
        if record is None:
            raise KeyError(workflow_id)
        graph = record.plan_state.resolve_graph()
        if graph is None:
            raise ValueError("拓扑无效")
        key = (node_id or "").strip()
        graph_node = graph.nodes.get(key)
        if graph_node is None:
            raise ValueError(f"节点不存在: {node_id}")
        output = (record.plan_state.node_outputs.get(key) or "").strip()
        revision = (record.plan_state.pre_node_reject_infos.get(key) or "").strip()
        return {
            "node_id": key,
            "label": graph_node.label or key,
            "output": output,
            "revision_note": revision,
            "iterations": record.plan_state.node_iterations.get(key, 0),
            "is_cli": graph_node.is_cli(),
        }

    async def get_workflow(self, workflow_id: str) -> Optional[WorkflowRecord]:
        record = await self._load_record(workflow_id)
        if record is None:
            return None
        return await self._ensure_graph_integrity(record)

    async def _resolve_template_reference_graph(self, record: WorkflowRecord) -> Optional[DirectExecGraph]:
        template_id = (record.template_id or "").strip()
        if not template_id:
            return None
        template = await self._template_store.get(template_id)
        if template is None:
            return None
        return DirectExecGraph.from_dict(template.graph)

    async def _ensure_graph_integrity(self, record: WorkflowRecord) -> WorkflowRecord:
        graph = record.plan_state.resolve_graph()
        if graph is None:
            return record
        changed = False
        lanes = infer_lanes_from_expand_outputs(record.plan_state.node_outputs)
        if graph_has_missing_node_refs(graph):
            if not lanes:
                raise ValueError("拓扑中 Lane 节点引用缺失，且无法从 expand 产出恢复，请重新确认分裂")
            graph = repair_lane_expand_graph(
                graph,
                lanes=lanes,
                global_placeholders={
                    "requirement_id": record.requirement_id or "",
                    "workspace": record.workspace_path or "",
                },
            )
            changed = True
        elif graph_has_duplicate_edges(graph):
            graph = dedupe_graph_edges(graph)
            changed = True
        if lanes and (graph_has_disconnected_nodes(graph) or graph_needs_post_merge_restore(graph)):
            reference = await self._resolve_template_reference_graph(record)
            if reference is not None:
                restored = restore_post_merge_flow(graph, reference)
                if restored.to_dict() != graph.to_dict():
                    graph = restored
                    changed = True
        if changed:
            record.plan_state.plan_graph = graph
            await self._store.save(record)
        return record

    async def execute(
        self,
        workflow_id: str,
        *,
        start_node_id: Optional[str] = None,
        clear_history: bool = False,
    ) -> None:
        async with self._lock:
            if workflow_id in self._running_tasks and not self._running_tasks[workflow_id].done():
                raise RuntimeError("工作流正在执行中")
            record = await self._load_record(workflow_id)
            if record is None:
                raise KeyError(workflow_id)
            record = await self._ensure_graph_integrity(record)
            graph = record.plan_state.resolve_graph()
            if graph is None:
                raise ValueError("请先配置有效拓扑")
            plan_state = record.plan_state
            if not self.is_running(workflow_id) and plan_state.phase == PlanGraphPhase.EXECUTING:
                plan_state.phase = PlanGraphPhase.IDLE
                plan_state.running_node_ids = []
            if start_node_id:
                plan_state.pending_gate = {}
                plan_state.pending_expand = {}
                if plan_state.phase in (
                    PlanGraphPhase.AWAITING_HUMAN,
                    PlanGraphPhase.AWAITING_EXPAND,
                ):
                    plan_state.phase = PlanGraphPhase.IDLE
                await self._store.save(record)
            elif clear_history:
                plan_state.pending_gate = {}
                plan_state.pending_expand = {}
                await self._store.save(record)
            abort = RunAbortController()
            self._abort_controllers[workflow_id] = abort
            task = asyncio.create_task(
                self._run_execution(workflow_id, record, abort, start_node_id, clear_history)
            )
            self._running_tasks[workflow_id] = task

    async def abort(self, workflow_id: str) -> bool:
        ctrl = self._abort_controllers.get(workflow_id)
        if ctrl is None:
            return False
        ctrl.request_abort(AbortReason.USER_INTERRUPT, "用户中止")
        task = self._running_tasks.get(workflow_id)
        if task is not None and not task.done():
            task.cancel()
        return True

    async def _run_execution(
        self,
        workflow_id: str,
        record: WorkflowRecord,
        abort: RunAbortController,
        start_node_id: Optional[str],
        clear_history: bool,
    ) -> None:
        plan_state = record.plan_state
        if clear_history and not start_node_id:
            plan_state.clear_history(clear_session_id=False)
        elif start_node_id:
            graph = plan_state.resolve_graph()
            if graph and not graph.is_entry_node(start_node_id):
                plan_state.clear_execution_from_node(start_node_id)

        agent_ctx = AgentContext(
            user_id="local",
            session_id=workflow_id,
            workspace_path=record.workspace_path,
            requirement_id=record.requirement_id,
        )

        async def notify(msg: Message) -> None:
            fresh = await self._store.get(workflow_id)
            if fresh is not None:
                await self._append_message(fresh, msg)

        runtime_ctx = RuntimeContext(
            abort_controller=abort,
            actor_id=f"workflow:{workflow_id}",
            notify_user_callback=notify,
            push_history_callback=notify,
        )

        async def persist(state: PlanGraphState, summary: str) -> None:
            await self._persist_plan_state(workflow_id, state, summary)

        judge_cb = build_judge_callback(
            judge_mode=record.judge_mode or None,
            llm_provider=record.llm_provider or None,
            llm_model=record.llm_model or None,
            abort_controller=abort,
        )
        expand_planner_cb = build_expand_planner_callback(
            llm_provider=record.llm_provider or None,
            llm_model=record.llm_model or None,
            abort_controller=abort,
        )

        resume_start: Optional[str] = start_node_id
        try:
            while True:
                try:
                    await LangGraphExecutor.run(
                        plan_state,
                        agent_ctx,
                        runtime_ctx,
                        persist_plangraph_callback=persist,
                        judge_route_callback=judge_cb,
                        expand_planner_callback=expand_planner_cb,
                        start_node_id=resume_start,
                    )
                    break
                except HumanGatePause as pause:
                    fresh = await self._store.get(workflow_id)
                    if fresh is None:
                        return
                    next_id = await self._try_auto_human_gate_apply(fresh, pause.node_id)
                    if not next_id:
                        fresh.plan_state.running_node_ids = []
                        fresh.plan_state.phase = PlanGraphPhase.AWAITING_HUMAN
                        await self._store.save(fresh)
                        return
                    plan_state = fresh.plan_state
                    graph = plan_state.resolve_graph()
                    if graph and not graph.is_entry_node(next_id):
                        plan_state.clear_execution_from_node(next_id)
                    resume_start = next_id
                    continue
                except ExpandPause as pause:
                    fresh = await self._store.get(workflow_id)
                    if fresh is None:
                        return
                    fork_id = await self._try_auto_expand_apply(fresh, pause.node_id)
                    if not fork_id:
                        fresh.plan_state.running_node_ids = []
                        fresh.plan_state.phase = PlanGraphPhase.AWAITING_EXPAND
                        await self._store.save(fresh)
                        return
                    plan_state = fresh.plan_state
                    graph = plan_state.resolve_graph()
                    if graph and not graph.is_entry_node(fork_id):
                        plan_state.clear_execution_from_node(fork_id)
                    resume_start = fork_id
                    continue
        except asyncio.CancelledError:
            fresh = await self._store.get(workflow_id)
            if fresh is not None:
                fresh.plan_state.phase = PlanGraphPhase.IDLE
                fresh.plan_state.running_node_ids = []
                await self._store.save(fresh)
                await self._append_message(fresh, Message.assistant_message("编排已中止。"))
            return
        except Exception as e:
            logger.exception("Workflow execution failed: %s", workflow_id)
            plan_state.phase = PlanGraphPhase.IDLE
            plan_state.running_node_ids = []
            await self._persist_plan_state(workflow_id, plan_state, f"编排失败：{e}")
        finally:
            self._abort_controllers.pop(workflow_id, None)
            self._running_tasks.pop(workflow_id, None)
            abort.clear()

    def is_running(self, workflow_id: str) -> bool:
        task = self._running_tasks.get(workflow_id)
        return task is not None and not task.done()

    def get_pending(self, record: WorkflowRecord) -> Dict[str, Any]:
        state = record.plan_state
        return {
            "phase": state.phase.value,
            "gate": dict(state.pending_gate or {}),
            "expand": dict(state.pending_expand or {}),
        }

    async def gate_decision(
        self,
        workflow_id: str,
        *,
        approve: bool,
        comment: str = "",
    ) -> WorkflowRecord:
        record = await self._load_record(workflow_id)
        if record is None:
            raise KeyError(workflow_id)
        if record.plan_state.phase != PlanGraphPhase.AWAITING_HUMAN:
            raise ValueError("当前无待人工确认节点")
        pending = record.plan_state.pending_gate or {}
        node_id = str(pending.get("node_id") or "").strip()
        graph = record.plan_state.resolve_graph()
        if graph is None or node_id not in graph.nodes:
            raise ValueError("人工卡点状态无效")
        human_node = graph.nodes[node_id]
        summary = str(pending.get("summary") or "").strip()
        note = (comment or "").strip()
        if approve:
            output = summary
            if note:
                output = f"{output}\n\n人工意见：{note}".strip()
            record.plan_state.node_outputs[node_id] = output
            record.plan_state.pending_gate = {}
            record.plan_state.phase = PlanGraphPhase.IDLE
            next_ids = graph.resolve_next_node_ids(node_id, EdgeCondition.PASS)
            if not next_ids:
                raise ValueError("人工节点缺少 pass 出边")
            await self._store.save(record)
            await self._append_message(
                record,
                Message.assistant_message(f"人工确认通过步骤「{human_node.label}」，继续执行。"),
            )
            await self.execute(workflow_id, start_node_id=next_ids[0])
        else:
            if not note:
                raise ValueError("驳回时请填写意见")
            reject_targets = graph.resolve_next_node_ids(node_id, EdgeCondition.REJECT)
            if not reject_targets:
                raise ValueError("人工节点缺少 reject 出边")
            reject_msg = f"步骤「{human_node.label}」人工驳回：{note}"
            for target_id in reject_targets:
                record.plan_state.pre_node_reject_infos[target_id] = reject_msg
            record.plan_state.node_outputs[node_id] = reject_msg
            record.plan_state.pending_gate = {}
            record.plan_state.phase = PlanGraphPhase.IDLE
            await self._store.save(record)
            await self._append_message(record, Message.assistant_message(reject_msg))
            await self.execute(workflow_id, start_node_id=reject_targets[0])
        fresh = await self._store.get(workflow_id)
        if fresh is None:
            raise KeyError(workflow_id)
        return fresh

    async def _try_auto_human_gate_apply(self, record: WorkflowRecord, human_node_id: str) -> Optional[str]:
        graph = record.plan_state.resolve_graph()
        if graph is None or human_node_id not in graph.nodes:
            return None
        human_node = graph.nodes[human_node_id]
        human_cfg = human_node.executor.human
        if human_cfg is None or not human_cfg.auto_confirm:
            return None
        pending = record.plan_state.pending_gate or {}
        if str(pending.get("node_id") or "").strip() != human_node_id:
            return None
        summary = str(pending.get("summary") or "").strip()
        record.plan_state.node_outputs[human_node_id] = summary
        record.plan_state.pending_gate = {}
        record.plan_state.phase = PlanGraphPhase.IDLE
        next_ids = graph.resolve_next_node_ids(human_node_id, EdgeCondition.PASS)
        if not next_ids:
            raise ValueError("人工节点缺少 pass 出边")
        await self._store.save(record)
        await self._append_message(
            record,
            Message.assistant_message(f"已自动确认步骤「{human_node.label}」，继续执行。"),
        )
        return next_ids[0]

    async def _try_auto_expand_apply(self, record: WorkflowRecord, expand_node_id: str) -> Optional[str]:
        graph = record.plan_state.resolve_graph()
        if graph is None or expand_node_id not in graph.nodes:
            return None
        expand_cfg = graph.nodes[expand_node_id].executor.expand
        if expand_cfg is None or not expand_cfg.is_auto_confirm():
            return None
        pending = record.plan_state.pending_expand or {}
        if str(pending.get("node_id") or "").strip() != expand_node_id:
            return None
        fork_id = self._apply_pending_expand(record, pending)
        branch_count = len(pending.get("lanes") or []) if str(pending.get("mode") or "") == "lane" else len(pending.get("tasks") or [])
        branch_label = "Lane" if str(pending.get("mode") or "") == "lane" else "子任务"
        await self._store.save(record)
        await self._append_message(
            record,
            Message.assistant_message(f"已自动确认分裂 {branch_count} 个{branch_label}，拓扑已更新并继续执行。"),
        )
        return fork_id

    def _apply_pending_expand(self, record: WorkflowRecord, pending: Dict[str, Any]) -> str:
        expand_node_id = str(pending.get("node_id") or "").strip()
        mode = str(pending.get("mode") or "task").strip().lower()
        tasks = pending.get("tasks") or []
        lanes = pending.get("lanes") or []
        if not expand_node_id or (mode == "lane" and not lanes) or (mode != "lane" and not tasks):
            raise ValueError("待分裂任务无效")
        graph = record.plan_state.resolve_graph()
        if graph is None:
            raise ValueError("拓扑无效")
        merge_label = str(pending.get("merge_label") or "任务汇聚")
        global_placeholders = {
            "requirement_id": record.requirement_id or "",
            "workspace": record.workspace_path or "",
        }
        expansion = {"mode": mode, "tasks": tasks, "lanes": lanes}
        new_graph, fork_id = apply_expansion_to_graph(
            graph,
            expand_node_id=expand_node_id,
            expansion=expansion,
            merge_label=merge_label,
            global_placeholders=global_placeholders,
        )
        record.plan_state.plan_graph = new_graph
        record.plan_state.pending_expand = {}
        record.plan_state.phase = PlanGraphPhase.IDLE
        return fork_id

    async def expand_apply(self, workflow_id: str) -> WorkflowRecord:
        record = await self._load_record(workflow_id)
        if record is None:
            raise KeyError(workflow_id)
        if record.plan_state.phase != PlanGraphPhase.AWAITING_EXPAND:
            raise ValueError("当前无待确认的任务分裂")
        pending = record.plan_state.pending_expand or {}
        fork_id = self._apply_pending_expand(record, pending)
        branch_count = len(pending.get("lanes") or []) if str(pending.get("mode") or "") == "lane" else len(pending.get("tasks") or [])
        branch_label = "Lane" if str(pending.get("mode") or "") == "lane" else "子任务"
        await self._store.save(record)
        await self._append_message(
            record,
            Message.assistant_message(f"已确认分裂 {branch_count} 个{branch_label}，即将并行执行。"),
        )
        await self.execute(workflow_id, start_node_id=fork_id)
        fresh = await self._store.get(workflow_id)
        if fresh is None:
            raise KeyError(workflow_id)
        return fresh

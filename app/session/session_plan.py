from typing import Any, Dict, TYPE_CHECKING
from app.graph.plan_graph import DirectExecGraph
from app.session.plan_mode import PlanMode, normalize_plan_mode
from app.session.workflow_store import WorkflowRecord

if TYPE_CHECKING:
    from app.session.template_store import WorkflowTemplateStore


async def hydrate_session_graph(
    record: WorkflowRecord,
    template_store: "WorkflowTemplateStore",
) -> None:
    mode = normalize_plan_mode(record.plan_mode)
    if mode == PlanMode.DYNAMIC.value:
        return
    template_id = str(record.template_id or "").strip()
    if not template_id:
        return
    existing = record.plan_state.resolve_graph()
    if existing is not None and len(existing.nodes) > 0:
        return
    template = await template_store.get(template_id)
    if template is None:
        return
    graph = DirectExecGraph.from_dict(template.graph)
    if graph is not None:
        record.plan_state.plan_graph = graph
    if template.judge_mode:
        record.judge_mode = template.judge_mode


def session_plan_info(record: WorkflowRecord, template_name: str = "") -> Dict[str, Any]:
    return {
        "plan_mode": normalize_plan_mode(record.plan_mode),
        "template_id": str(record.template_id or "").strip(),
        "template_name": template_name,
    }

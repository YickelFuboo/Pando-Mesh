import pytest
from app.graph.plan_graph import END_NODE, START_NODE
from app.graph.plan_graph import PlanGraphPhase, PlanGraphState
from app.session.template_store import (
    WorkflowTemplateStore,
    apply_template_to_record,
    template_from_workflow,
)
from app.session.workflow_service import WorkflowService
from app.session.workflow_store import WorkflowRecord, WorkflowStore


@pytest.fixture
def sample_graph():
    return {
        "nodes": [
            {
                "id": "step_a",
                "label": "开发",
                "executor": {"kind": "cli", "cli": {"commands": [{"command": "echo", "args": ["ok"]}]}},
            }
        ],
        "edges": [
            {"from": START_NODE, "to": "step_a", "condition": "always"},
            {"from": "step_a", "to": END_NODE, "condition": "always"},
        ],
        "entry": "step_a",
    }


@pytest.mark.asyncio
async def test_template_crud(tmp_path, sample_graph):
    store = WorkflowTemplateStore(root_dir=str(tmp_path / "data"))
    created = await store.create(
        name="标准流程",
        description="测试",
        graph=sample_graph,
        judge_mode="auto",
        category="编码实现",
    )
    assert created.template_id.startswith("tpl_")
    assert created.node_count() == 1
    assert created.category == "编码实现"
    loaded = await store.get(created.template_id)
    assert loaded is not None
    assert loaded.name == "标准流程"
    assert loaded.category == "编码实现"
    items = await store.list_all()
    assert len(items) == 1
    updated = await store.update(created.template_id, name="更新流程", category="需求分析")
    assert updated.name == "更新流程"
    assert updated.category == "需求分析"
    assert await store.delete(created.template_id)
    assert await store.get(created.template_id) is None


@pytest.mark.asyncio
async def test_save_and_apply_template(tmp_path, sample_graph):
    wf_store = WorkflowStore(root_dir=str(tmp_path / "data"))
    tpl_store = WorkflowTemplateStore(root_dir=str(tmp_path / "data"))
    record = await wf_store.create(
        name="req-a",
        plan_mode="dynamic",
        graph_spec=sample_graph,
        user_goal="goal",
    )
    record.judge_mode = "llm"
    record.plan_state.phase = PlanGraphPhase.DONE
    record.plan_state.node_outputs = {"step_a": "done"}
    await wf_store.save(record)
    draft = template_from_workflow(record, name="from session", description="desc")
    template = await tpl_store.create(
        name=draft.name,
        description=draft.description,
        user_goal=draft.user_goal,
        judge_mode=draft.judge_mode,
        graph=draft.graph,
        source_workflow_id=record.workflow_id,
    )
    apply_template_to_record(record, template)
    assert record.plan_state.phase == PlanGraphPhase.IDLE
    assert record.plan_state.node_outputs == {}
    assert record.judge_mode == "llm"


@pytest.mark.asyncio
async def test_init_from_template_service(tmp_path, sample_graph):
    wf_store = WorkflowStore(root_dir=str(tmp_path / "data"))
    tpl_store = WorkflowTemplateStore(root_dir=str(tmp_path / "data"))
    service = WorkflowService(store=wf_store, template_store=tpl_store)
    multi_graph = {
        **sample_graph,
        "nodes": sample_graph["nodes"] + [
            {
                "id": "step_b",
                "label": "检查",
                "executor": {"kind": "cli", "cli": {"commands": [{"command": "echo", "args": ["check"]}]}},
            },
        ],
        "edges": [
            {"from": START_NODE, "to": "step_a", "condition": "always"},
            {"from": "step_a", "to": "step_b", "condition": "always"},
            {"from": "step_b", "to": END_NODE, "condition": "always"},
        ],
    }
    template = await tpl_store.create(name="双节点", description="", graph=multi_graph, judge_mode="auto")
    record = await wf_store.create(
        name="req-b",
        plan_mode="template",
        template_id=template.template_id,
        graph_spec=sample_graph,
    )
    record.plan_state.node_outputs = {"step_a": "done"}
    record.plan_state.phase = PlanGraphPhase.DONE
    await wf_store.save(record)
    updated = await service.init_from_template(record.workflow_id, template.template_id)
    assert updated.template_id == template.template_id
    assert updated.plan_mode == "template"
    assert updated.plan_state.phase == PlanGraphPhase.IDLE
    assert updated.plan_state.node_outputs == {}
    graph = updated.plan_state.resolve_graph()
    assert graph is not None
    assert len(graph.nodes) == 2


@pytest.mark.asyncio
async def test_init_from_template_clears_awaiting_pending(tmp_path, sample_graph):
    wf_store = WorkflowStore(root_dir=str(tmp_path / "data"))
    tpl_store = WorkflowTemplateStore(root_dir=str(tmp_path / "data"))
    service = WorkflowService(store=wf_store, template_store=tpl_store)
    template = await tpl_store.create(name="标准流程", description="", graph=sample_graph, judge_mode="auto")
    record = await wf_store.create(
        name="req-pending",
        plan_mode="template",
        template_id=template.template_id,
        graph_spec=sample_graph,
    )
    record.plan_state.phase = PlanGraphPhase.AWAITING_HUMAN
    record.plan_state.pending_gate = {"node_id": "step_a", "label": "确认", "summary": "待确认"}
    record.plan_state.node_outputs = {"step_a": "partial"}
    await wf_store.save(record)
    updated = await service.init_from_template(record.workflow_id, template.template_id)
    assert updated.plan_state.phase == PlanGraphPhase.IDLE
    assert updated.plan_state.pending_gate == {}
    assert updated.plan_state.pending_expand == {}
    assert updated.plan_state.node_outputs == {}


@pytest.mark.asyncio
async def test_create_session_applies_template_graph(tmp_path, sample_graph):
    wf_store = WorkflowStore(root_dir=str(tmp_path / "data"))
    tpl_store = WorkflowTemplateStore(root_dir=str(tmp_path / "data"))
    template = await tpl_store.create(name="标准流程", description="", graph=sample_graph, judge_mode="auto")
    record = await wf_store.create(
        name="req-new",
        workspace_path=str(tmp_path),
        requirement_id="req-new",
        plan_mode="template",
        template_id=template.template_id,
    )
    apply_template_to_record(record, template)
    await wf_store.save(record)
    loaded = await wf_store.get(record.workflow_id)
    assert loaded is not None
    assert loaded.template_id == template.template_id
    graph = loaded.plan_state.resolve_graph()
    assert graph is not None
    assert len(graph.nodes) == 1
    assert loaded.judge_mode == "auto"

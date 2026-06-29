import pytest
from app.graph.plan_graph import END_NODE, START_NODE
from app.session.plan_mode import PlanMode, normalize_plan_mode
from app.session.session_plan import hydrate_session_graph, session_plan_info
from app.session.template_store import WorkflowTemplateStore
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


def test_normalize_plan_mode():
    assert normalize_plan_mode("template") == PlanMode.TEMPLATE.value
    assert normalize_plan_mode("dynamic") == PlanMode.DYNAMIC.value
    assert normalize_plan_mode("") == PlanMode.TEMPLATE.value
    assert normalize_plan_mode("unknown") == PlanMode.TEMPLATE.value


@pytest.mark.asyncio
async def test_hydrate_template_session(tmp_path, sample_graph):
    tpl_store = WorkflowTemplateStore(root_dir=str(tmp_path / "data"))
    wf_store = WorkflowStore(root_dir=str(tmp_path / "data"))
    template = await tpl_store.create(
        name="标准流程",
        graph=sample_graph,
        judge_mode="llm",
    )
    record = await wf_store.create(
        name="req-a",
        plan_mode="template",
        template_id=template.template_id,
    )
    assert record.plan_state.resolve_graph() is None or not record.plan_state.resolve_graph().nodes
    await hydrate_session_graph(record, tpl_store)
    graph = record.plan_state.resolve_graph()
    assert graph is not None
    assert "step_a" in graph.nodes
    assert record.judge_mode == "llm"


@pytest.mark.asyncio
async def test_hydrate_skips_existing_graph(tmp_path, sample_graph):
    tpl_store = WorkflowTemplateStore(root_dir=str(tmp_path / "data"))
    wf_store = WorkflowStore(root_dir=str(tmp_path / "data"))
    template = await tpl_store.create(name="标准流程", graph=sample_graph)
    other_graph = {
        "nodes": [
            {
                "id": "other",
                "label": "其他",
                "executor": {"kind": "cli", "cli": {"commands": [{"command": "echo", "args": ["x"]}]}},
            }
        ],
        "edges": [
            {"from": START_NODE, "to": "other", "condition": "always"},
            {"from": "other", "to": END_NODE, "condition": "always"},
        ],
        "entry": "other",
    }
    record = await wf_store.create(
        name="req-a",
        plan_mode="template",
        template_id=template.template_id,
    )
    from app.graph.plan_graph import DirectExecGraph
    record.plan_state.plan_graph = DirectExecGraph.from_dict(other_graph)
    await wf_store.save(record)
    await hydrate_session_graph(record, tpl_store)
    graph = record.plan_state.resolve_graph()
    assert graph is not None
    assert "other" in graph.nodes
    assert "step_a" not in graph.nodes


@pytest.mark.asyncio
async def test_template_mode_blocks_topology_update(tmp_path, sample_graph):
    wf_store = WorkflowStore(root_dir=str(tmp_path / "data"))
    record = await wf_store.create(
        name="req-a",
        plan_mode="template",
        template_id="tpl_missing",
    )
    with pytest.raises(ValueError, match="模板管理"):
        await wf_store.update_topology(record.workflow_id, sample_graph)


def test_session_plan_info():
    record = WorkflowRecord(
        workflow_id="wf_test",
        plan_mode="template",
        template_id="tpl_demo",
    )
    info = session_plan_info(record, template_name="演示模板")
    assert info["plan_mode"] == "template"
    assert info["template_id"] == "tpl_demo"
    assert info["template_name"] == "演示模板"

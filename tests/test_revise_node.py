import pytest
from app.session.workflow_store import WorkflowStore
from app.session.workflow_service import WorkflowService
from app.graph.node_config import GraphNodeCliConfig, GraphNodeExecutor
from app.graph.plan_graph import DirectExecGraph, END_NODE, EdgeCondition, GraphEdge, GraphNode, PlanGraphPhase, START_NODE


def _demo_graph():
    cli = GraphNodeCliConfig.from_dict({
        "commands": [{"command": "python", "args": ["-c", "print('ok')"]}],
        "input": "arg",
        "cwd": "{workspace}",
        "output_mode": "stdout",
    })
    nodes = {
        "step_a": GraphNode(
            id="step_a",
            label="开发",
            task="do work",
            executor=GraphNodeExecutor.from_cli(cli),
        ),
    }
    edges = [
        GraphEdge(from_id=START_NODE, to_id="step_a", condition=EdgeCondition.ALWAYS),
        GraphEdge(from_id="step_a", to_id=END_NODE, condition=EdgeCondition.ALWAYS),
    ]
    return DirectExecGraph(nodes=nodes, edges=edges, entry_node_id="step_a")


@pytest.mark.asyncio
async def test_revise_node_injects_feedback_and_clears_downstream(tmp_path):
    store = WorkflowStore(root_dir=str(tmp_path))
    service = WorkflowService(store=store)
    record = await store.create(
        name="demo",
        workspace_path=str(tmp_path),
        plan_mode="dynamic",
        graph_spec=_demo_graph().to_dict(),
    )
    record.plan_state.node_outputs["step_a"] = "old result"
    record.plan_state.phase = PlanGraphPhase.DONE
    await store.save(record)

    await service.revise_node(record.workflow_id, "step_a", feedback="请改成返回 hello")

    saved = await store.get(record.workflow_id)
    assert saved is not None
    assert "人工修正意见" in saved.plan_state.pre_node_reject_infos.get("step_a", "")
    assert "old result" in saved.plan_state.pre_node_reject_infos.get("step_a", "")
    assert "step_a" not in saved.plan_state.node_outputs
    assert any("修正步骤" in (m.get("content") or "") for m in saved.messages)

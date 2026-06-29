from pathlib import Path

from app.graph.langraph_executor import LangGraphExecutor
from app.graph.plan_graph import GraphNode
from app.runtime.context import AgentContext


def test_build_cli_task_expands_node_task_placeholders(tmp_path: Path):
    ws = tmp_path / "project"
    req_dir = ws / "requirements" / "req1"
    req_dir.mkdir(parents=True)
    ctx = AgentContext(workspace_path=str(ws), requirement_id="req1")
    node = GraphNode(
        id="analyze",
        label="需求分析",
        task="请使用{workspace}/skill/xxx这个skill，对{workspace}/requirements/{requirement_id}这个需求进行分析",
    )
    result = LangGraphExecutor._build_cli_task(node, "", {}, agent_ctx=ctx)
    assert str(ws.resolve()) in result
    assert "requirements/req1" in result.replace("\\", "/")
    assert "{workspace}" not in result
    assert "{requirement_id}" not in result

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


def test_build_cli_task_includes_goal_step_and_task(tmp_path: Path):
    ws = tmp_path / "project"
    req_dir = ws / "requirements" / "req1"
    req_dir.mkdir(parents=True)
    ctx = AgentContext(workspace_path=str(ws), requirement_id="req1")
    node = GraphNode(
        id="step_req_analysis",
        label="① 需求澄清与分析",
        task="请使用{workspace}/skills/01-fwd-req-analysis 这个 skill，阅读 {requirement_id} 的原始需求描述",
    )
    result = LangGraphExecutor._build_cli_task(
        node, "对原始需求进行 需求澄清-特性影响分析", {}, agent_ctx=ctx,
    )
    assert "用户目标：对原始需求进行 需求澄清-特性影响分析" in result
    assert "当前步骤：① 需求澄清与分析（step_req_analysis）" in result
    assert "步骤说明：" in result
    assert "01-fwd-req-analysis" in result
    assert "req1" in result

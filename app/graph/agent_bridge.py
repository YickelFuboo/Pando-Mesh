"""Graph 与第三方 Agent 执行器之间的桥接层。"""
from app.graph.plan_graph import GraphNode, PlanGraphState
from app.third_agent.executor.types import AgentHistoryRequest, AgentRunRequest, AgentRunResult


def build_run_request(
    graph_node: GraphNode,
    plan_graph: PlanGraphState,
    task: str,
) -> AgentRunRequest:
    cli_cfg = graph_node.executor.cli
    session_id = ""
    if cli_cfg is not None and cli_cfg.session.enabled:
        session_id = (plan_graph.node_session_id.get(graph_node.id) or "").strip()
    return AgentRunRequest(
        task=task,
        cli=cli_cfg,
        session_id=session_id,
        registered_agent_id=(graph_node.executor.registered_agent_id or "").strip(),
        node_id=graph_node.id,
        node_label=(graph_node.label or graph_node.id or "").strip(),
    )


def apply_run_result(
    plan_graph: PlanGraphState,
    node_id: str,
    run_result: AgentRunResult,
) -> str:
    if run_result.session_id:
        plan_graph.node_session_id[node_id] = run_result.session_id
    return run_result.result


def build_history_request(
    graph_node: GraphNode,
    cli_session_id: str,
    workspace_path: str,
) -> AgentHistoryRequest:
    return AgentHistoryRequest(
        cli=graph_node.executor.cli,
        session_id=(cli_session_id or "").strip(),
        workspace_path=(workspace_path or "").strip(),
        registered_agent_id=(graph_node.executor.registered_agent_id or "").strip(),
        is_cli=graph_node.is_cli(),
    )

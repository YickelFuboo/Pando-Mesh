import pytest
from app.graph.judge import judge_route_from_output
from app.graph.plan_graph import EdgeCondition, GraphNode
from app.graph.node_config import GraphNodeExecutor


def _review_node():
    return GraphNode(id="review", label="审查", executor=GraphNodeExecutor.from_react())


def test_judge_pass_from_json():
    route = judge_route_from_output(_review_node(), '{"verdict": "pass"}', {}, "")
    assert route == EdgeCondition.PASS


def test_judge_reject_from_json():
    route = judge_route_from_output(_review_node(), '{"verdict": "reject"}', {}, "")
    assert route == EdgeCondition.REJECT


def test_judge_default_pass():
    route = judge_route_from_output(_review_node(), "done without verdict", {}, "")
    assert route == EdgeCondition.PASS

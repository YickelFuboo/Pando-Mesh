from langgraph.channels.binop import BinaryOperatorAggregate
from langgraph.graph.state import _get_channels
from app.graph.langraph_executor import LangGraphRunState


def test_node_routes_uses_merge_reducer():
    channels, _, _ = _get_channels(LangGraphRunState)
    node_routes = channels.get("node_routes")
    assert isinstance(node_routes, BinaryOperatorAggregate)
    assert "last_route" not in channels

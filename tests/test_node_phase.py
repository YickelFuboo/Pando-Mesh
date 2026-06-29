from app.graph.plan_graph import DirectExecGraph, END_NODE, START_NODE


def test_graph_node_phase_roundtrip():
    graph = DirectExecGraph.from_dict({
        "nodes": [
            {
                "id": "step_a",
                "label": "设计",
                "phase": "设计阶段",
                "executor": {"kind": "cli", "cli": {"commands": [{"command": "echo", "args": ["ok"]}]}},
            },
            {
                "id": "step_b",
                "label": "开发",
                "phase": "开发阶段",
                "executor": {"kind": "cli", "cli": {"commands": [{"command": "echo", "args": ["ok"]}]}},
            },
        ],
        "edges": [
            {"from": START_NODE, "to": "step_a", "condition": "always"},
            {"from": "step_a", "to": "step_b", "condition": "always"},
            {"from": "step_b", "to": END_NODE, "condition": "always"},
        ],
        "entry": "step_a",
    })
    assert graph is not None
    assert graph.nodes["step_a"].phase == "设计阶段"
    payload = graph.to_dict()
    by_id = {n["id"]: n for n in payload["nodes"]}
    assert by_id["step_a"]["phase"] == "设计阶段"
    assert by_id["step_b"]["phase"] == "开发阶段"

from app.graph.graph_parse import parse_planning_llm_response, prose_without_json_blob
from app.utils import extract_json_object


SAMPLE_GRAPH_JSON = """
先说明一下方案。

```json
{
  "nodes": [
    {"id": "step_a", "label": "开发", "task": "实现功能", "max_iterations": 3,
     "executor": {"kind": "react", "agent_type": "dev"}}
  ],
  "edges": [
    {"from": "START", "to": "step_a", "condition": "always"},
    {"from": "step_a", "to": "END", "condition": "always"}
  ],
  "entry": "step_a"
}
```
"""


def test_extract_json_object_from_fence():
    parsed = extract_json_object(SAMPLE_GRAPH_JSON)
    assert parsed is not None
    assert parsed.get("entry") == "step_a"


def test_parse_planning_llm_response():
    explanation, graph = parse_planning_llm_response(SAMPLE_GRAPH_JSON)
    assert graph is not None
    assert "step_a" in graph.nodes
    assert explanation.startswith("先说明")


def test_prose_without_json_blob():
    text = prose_without_json_blob(SAMPLE_GRAPH_JSON)
    assert "step_a" not in text
    assert "先说明" in text

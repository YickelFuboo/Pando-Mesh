import re
from typing import Any, Dict, Optional, Tuple
from app.common.json_utils import extract_json_object
from app.graph.node_config import GraphNodeCliConfig, GraphNodeExecutor
from app.graph.plan_graph import DirectExecGraph

_PARTIAL_START_RE = re.compile(
    r"(?:从(?:节点)?|start(?:\s+from(?:\s+node)?)?\s+)"
    r"[`'\"]?([A-Za-z][A-Za-z0-9_-]*)[`'\"]?"
    r"(?:\s*开始)?(?:\s*执行)?",
    re.IGNORECASE,
)


def parse_partial_start_node_id(
    question: str,
    graph: DirectExecGraph,
) -> Tuple[Optional[str], bool, Optional[str]]:
    """
    解析部分重跑起点。
    返回 (start_node_id, matched, token)：
    - matched=False：全量从 entry 执行，token 为 None
    - matched=True 且 start_node_id 有值：解析成功
    - matched=True 且 start_node_id 为 None：用户指定了节点但未找到，token 为原始输入
    """
    text = (question or "").strip()
    if not text:
        return None, False, None
    match = _PARTIAL_START_RE.search(text)
    if not match:
        return None, False, None
    token = (match.group(1) or "").strip()
    if not token:
        return None, True, None
    return graph.resolve_node_id(token), True, token


def prose_without_json_blob(text: str) -> str:
    """去掉回复中的 JSON 代码块或最外层对象，保留模型文字说明。"""
    stripped = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped, re.IGNORECASE)
    if fence:
        return (stripped[: fence.start()] + stripped[fence.end() :]).strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        return (stripped[:start] + stripped[end + 1 :]).strip()
    return stripped


def parse_planning_llm_response(raw: str) -> Tuple[str, Optional[DirectExecGraph]]:
    """
    从建图 LLM 全文解析 (文字说明, 执行图)。
    说明为 JSON 外的叙述；图为 extract_json_object + DirectExecGraph 校验后的结果。
    """
    text = (raw or "").strip()
    if not text:
        return "", None
    parsed = extract_json_object(text)
    if not parsed:
        return text, None
    graph = DirectExecGraph.from_dict(parsed)
    if graph is None:
        return text, None
    return prose_without_json_blob(text), graph


def default_cli_executor_dict() -> Dict[str, Any]:
    return {
        "kind": "cli",
        "cli": {
            "commands": [
                {
                    "command": "claude",
                    "args": [
                        "-p",
                        "--output-format",
                        "json",
                        "--dangerously-skip-permissions",
                        "--disallowedTools",
                        "AskUserQuestion",
                    ],
                }
            ],
            "input": "arg",
            "cwd": "{workspace}",
            "timeout_sec": 3600,
            "output_mode": "json",
            "result_json_key": "result",
            "session": {
                "enabled": True,
                "resume_args": ["--resume", "{cli_session_id}"],
                "read_session_id_from_json": True,
                "session_id_json_key": "session_id",
            },
        },
    }


def normalize_graph_cli_executors(graph: DirectExecGraph) -> DirectExecGraph:
    """将 LLM 生成的 react 节点转为默认 CLI 配置（MOMA-Developer 以 CLI 为主）。"""
    default_cli = GraphNodeCliConfig.from_dict(default_cli_executor_dict()["cli"])
    if default_cli is None:
        return graph
    for node in graph.nodes.values():
        if node.is_cli():
            continue
        node.executor = GraphNodeExecutor.from_cli(default_cli)
    return graph

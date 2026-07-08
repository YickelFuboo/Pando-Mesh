from dataclasses import dataclass
from typing import Optional
from app.graph.node_config import GraphNodeCliConfig


@dataclass
class AgentRunResult:
    result: str
    session_id: Optional[str] = None


@dataclass
class AgentRunRequest:
    task: str
    cli: GraphNodeCliConfig
    session_id: str = ""
    registered_agent_id: str = ""
    node_id: str = ""
    node_label: str = ""


@dataclass
class AgentHistoryRequest:
    cli: GraphNodeCliConfig
    session_id: str
    workspace_path: str
    registered_agent_id: str = ""
    is_cli: bool = True

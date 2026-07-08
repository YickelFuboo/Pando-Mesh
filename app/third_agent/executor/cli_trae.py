from typing import List
from app.runtime.message import Message
from app.third_agent.executor.types import AgentHistoryRequest


class CliTrae:
    @staticmethod
    async def get_history(request: AgentHistoryRequest) -> List[Message]:
        return []

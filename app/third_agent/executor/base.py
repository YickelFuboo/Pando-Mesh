from abc import ABC, abstractmethod
from typing import List
from app.runtime.context import AgentContext, RuntimeContext
from app.runtime.message import Message
from app.third_agent.executor.types import AgentHistoryRequest, AgentRunRequest, AgentRunResult


class ThirdAgentExecutor(ABC):
    """第三方 Agent 执行器基类。"""
    agent_kind: str = ""

    @classmethod
    @abstractmethod
    async def run(
        cls,
        request: AgentRunRequest,
        agent_ctx: AgentContext,
        runtime_ctx: RuntimeContext,
    ) -> AgentRunResult:
        raise NotImplementedError

    @classmethod
    @abstractmethod
    async def get_history(cls, request: AgentHistoryRequest) -> List[Message]:
        raise NotImplementedError

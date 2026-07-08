from typing import List, Type
from app.runtime.context import AgentContext, RuntimeContext
from app.runtime.message import Message
from app.third_agent.executor.base import ThirdAgentExecutor
from app.third_agent.executor.cli import CliAgentExecutor
from app.third_agent.executor.types import AgentHistoryRequest, AgentRunRequest, AgentRunResult
from app.third_agent.register.types import AgentKind

_CLI_KINDS = frozenset({
    AgentKind.CLAUDE_CODE_CLI.value,
    AgentKind.CODEX_CLI.value,
    AgentKind.TREA_CLI.value,
})


class ThirdAgentDispatcher:
    """按 Agent 类型分发到执行器。"""

    @staticmethod
    def resolve_for_run(request: AgentRunRequest) -> Type[ThirdAgentExecutor]:
        agent_id = (request.registered_agent_id or "").strip()
        if agent_id:
            from app.third_agent.register.register import AgentRegistry
            reg = AgentRegistry().get(agent_id)
            if reg is not None and reg.kind.value in _CLI_KINDS:
                return CliAgentExecutor
        if ThirdAgentDispatcher._looks_like_cli(request.cli):
            return CliAgentExecutor
        return CliAgentExecutor

    @staticmethod
    def resolve_for_history(request: AgentHistoryRequest) -> Type[ThirdAgentExecutor]:
        agent_id = (request.registered_agent_id or "").strip()
        if agent_id:
            from app.third_agent.register.register import AgentRegistry
            reg = AgentRegistry().get(agent_id)
            if reg is not None and reg.kind.value in _CLI_KINDS:
                return CliAgentExecutor
        if request.is_cli or ThirdAgentDispatcher._looks_like_cli(request.cli):
            return CliAgentExecutor
        return CliAgentExecutor

    @staticmethod
    async def run(
        request: AgentRunRequest,
        agent_ctx: AgentContext,
        runtime_ctx: RuntimeContext,
    ) -> AgentRunResult:
        executor = ThirdAgentDispatcher.resolve_for_run(request)
        return await executor.run(request, agent_ctx, runtime_ctx)

    @staticmethod
    async def get_history(request: AgentHistoryRequest) -> List[Message]:
        executor = ThirdAgentDispatcher.resolve_for_history(request)
        return await executor.get_history(request)

    @staticmethod
    def _looks_like_cli(cli_cfg) -> bool:
        if cli_cfg is None:
            return False
        if cli_cfg.commands or cli_cfg.shell:
            return True
        return False

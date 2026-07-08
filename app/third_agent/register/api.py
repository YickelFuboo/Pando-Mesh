from typing import Any, Dict
from fastapi import APIRouter, HTTPException
from app.third_agent.register.register import AgentRegistry
from app.third_agent.register.schemas import AgentRegisterRequest, AgentUpdateRequest
from app.third_agent.register.utils import extract_history_config, extract_session_config

router = APIRouter(prefix="/agents")
_registry = AgentRegistry()


@router.get("", summary="Agent 列表")
async def list_agents():
    return [_agent_info(a) for a in _registry.list(enabled_only=False)]


@router.get("/catalog", summary="Agent 目录文本（供 Plan 使用）")
async def agent_catalog():
    return {"catalog": _registry.catalog_text()}


@router.get("/meta/kind-defaults/{kind}", summary="按类型返回默认 Executor 模板")
async def kind_defaults(kind: str):
    try:
        template = _registry.default_template(kind)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {
        "kind": kind.strip().lower(),
        "executor_template": template,
        "session_config": extract_session_config(template),
        "history_config": extract_history_config(template),
    }


@router.get("/{agent_id}", summary="Agent 详情")
async def get_agent(agent_id: str):
    reg = _registry.get(agent_id)
    if reg is None:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    return _agent_info(reg)


@router.post("", summary="注册 Agent")
async def register_agent(body: AgentRegisterRequest):
    try:
        saved = _registry.register(
            agent_id=body.agent_id.strip(),
            name=body.name.strip(),
            kind=body.kind,
            description=body.description.strip(),
            executor_template=body.executor_template,
            session_config=body.session_config,
            history_config=body.history_config,
            enabled=body.enabled,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return _agent_info(saved)


@router.patch("/{agent_id}", summary="更新 Agent")
async def update_agent(agent_id: str, body: AgentUpdateRequest):
    aid = agent_id.strip()
    if _registry.get(aid) is None:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=400, detail="未提供可更新字段")
    try:
        updated = _registry.update(aid, **fields)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if updated is None:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    return _agent_info(updated)


@router.post("/{agent_id}/reset", summary="恢复内置 Agent 为出厂默认")
async def reset_builtin_agent(agent_id: str):
    restored = _registry.reset_builtin(agent_id.strip())
    if restored is None:
        raise HTTPException(status_code=400, detail="仅内置 Agent 可恢复默认")
    return _agent_info(restored)


@router.delete("/{agent_id}", summary="注销自定义 Agent")
async def unregister_agent(agent_id: str):
    if not _registry.unregister(agent_id):
        raise HTTPException(status_code=400, detail="无法注销内置 Agent 或不存在的 Agent")
    return {"ok": True, "agent_id": agent_id}


def _agent_info(reg) -> Dict[str, Any]:
    payload = reg.to_api_dict()
    if reg.builtin:
        payload["modified"] = _registry.is_factory_modified(reg.agent_id)
    return payload

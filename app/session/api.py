from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query
from app.graph.cli_history import CliHistoryReader
from app.graph.plan_graph import PLAN_GRAPH_METADATA_KEY, PlanGraphState
from app.session.node_doc import load_node_doc, load_requirement_readme
from app.session.workspace_ref import resolve_workspace_ref_path
from app.session.plan_mode import PlanMode, normalize_plan_mode
from app.session.session_plan import hydrate_session_graph, session_plan_info
from app.session.requirements import list_requirements, normalize_workspace_path, requirement_path
from app.session.template_store import WorkflowTemplateStore, apply_template_to_record
from app.session.workflow_service import WorkflowService

router = APIRouter(prefix="/workflows")
_service = WorkflowService()
_template_store = WorkflowTemplateStore()


class WorkflowCreateRequest(BaseModel):
    name: str = ""
    description: str = ""
    workspace_path: str = ""
    requirement_id: str = ""
    user_goal: str = ""
    plan_mode: str = Field(default="template", description="template | dynamic")
    template_id: str = ""
    graph: Optional[Dict[str, Any]] = Field(default=None, description="拓扑 JSON（nodes/edges/entry）")


class RequirementSessionRequest(BaseModel):
    workspace_path: str = Field(..., min_length=1)
    user_goal: str = ""
    plan_mode: str = Field(default="template", description="template | dynamic")
    template_id: str = ""
    graph: Optional[Dict[str, Any]] = None


class TemplateDuplicateRequest(BaseModel):
    name: str = ""


class TemplateCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = ""
    user_goal: str = ""
    judge_mode: str = ""
    graph: Optional[Dict[str, Any]] = None


class TemplateUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    user_goal: Optional[str] = None
    judge_mode: Optional[str] = None
    graph: Optional[Dict[str, Any]] = None


class SaveAsTemplateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = ""


class WorkflowUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    workspace_path: Optional[str] = None
    user_goal: Optional[str] = None
    plan_mode: Optional[str] = Field(default=None, description="template | dynamic")
    template_id: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    judge_mode: Optional[str] = Field(default=None, description="auto | llm | json")


class TopologyUpdateRequest(BaseModel):
    graph: Dict[str, Any]


class ExecuteRequest(BaseModel):
    start_node_id: Optional[str] = None
    clear_history: bool = False


class GenerateGraphRequest(BaseModel):
    user_goal: Optional[str] = None
    recreate: bool = False


class GateDecisionRequest(BaseModel):
    comment: str = ""


class LlmConfigUpdateRequest(BaseModel):
    config: Dict[str, Any] = Field(..., description="chat_models.json 结构（api_key 未修改时可传 ********）")


class NodeReviseRequest(BaseModel):
    feedback: str = Field(..., min_length=1, description="修正意见，将注入该步骤重新执行")


class InitFromTemplateRequest(BaseModel):
    template_id: str = Field(..., min_length=1, description="Workflow 模板 ID")


async def _workflow_info(record) -> Dict[str, Any]:
    await hydrate_session_graph(record, _template_store)
    payload = record.to_dict()
    payload["running"] = _service.is_running(record.workflow_id)
    payload["pending"] = _service.get_pending(record)
    template_name = ""
    if record.template_id:
        tpl = await _template_store.get(record.template_id)
        if tpl is not None:
            template_name = tpl.name
    payload.update(session_plan_info(record, template_name))
    return payload


def _template_info(item) -> Dict[str, Any]:
    payload = item.to_dict()
    payload["node_count"] = item.node_count()
    return payload


@router.get("/meta/llm-status", summary="LLM 配置状态")
async def llm_status():
    return _service.llm_status()


@router.get("/meta/llm-config", summary="LLM 模型配置（API Key 已脱敏）")
async def get_llm_config():
    from app.maas.chat_models.models_config import models_config
    return models_config.to_public_dict()


@router.put("/meta/llm-config", summary="更新 LLM 模型配置")
async def update_llm_config(body: LlmConfigUpdateRequest):
    from app.maas.chat_models.models_config import models_config
    try:
        return models_config.apply_update(body.config)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/meta/requirements", summary="Workspace 需求列表")
async def list_workspace_requirements(workspace_path: str):
    ws = normalize_workspace_path(workspace_path)
    if not ws:
        raise HTTPException(status_code=400, detail="workspace_path 不能为空")
    try:
        items = list_requirements(ws)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    payload: List[Dict[str, Any]] = []
    for item in items:
        row = item.to_dict()
        record = await _service.store.find_by_requirement(ws, item.requirement_id)
        row["workspace_path"] = ws
        row["workflow_id"] = record.workflow_id if record else None
        row["has_session"] = record is not None
        row["running"] = _service.is_running(record.workflow_id) if record else False
        payload.append(row)
    return payload


@router.post("/requirements/{requirement_id}/session", summary="打开或创建需求 Workflow Session")
async def open_requirement_session(requirement_id: str, body: RequirementSessionRequest):
    ws = normalize_workspace_path(body.workspace_path)
    if not ws:
        raise HTTPException(status_code=400, detail="workspace_path 不能为空")
    try:
        req_dir = requirement_path(ws, requirement_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    existing = await _service.store.find_by_requirement(ws, requirement_id)
    if existing is not None:
        return await _workflow_info(existing)
    summary = ""
    for item in list_requirements(ws):
        if item.requirement_id == requirement_id:
            summary = item.summary
            break
    plan_mode = normalize_plan_mode(body.plan_mode)
    template_id = str(body.template_id or "").strip()
    user_goal = (body.user_goal or summary or "").strip()
    judge_mode = ""
    graph_spec = None
    template = None
    if plan_mode == PlanMode.TEMPLATE.value:
        if not template_id:
            raise HTTPException(status_code=400, detail="模板模式须选择 template_id")
        template = await _template_store.get(template_id)
        if template is None:
            raise HTTPException(status_code=404, detail="模板不存在")
        if template.user_goal and not user_goal:
            user_goal = template.user_goal
        judge_mode = template.judge_mode or ""
    else:
        graph_spec = body.graph
    try:
        record = await _service.store.create(
            name=requirement_id,
            description=str(req_dir),
            workspace_path=ws,
            requirement_id=requirement_id,
            plan_mode=plan_mode,
            template_id=template_id,
            user_goal=user_goal,
            graph_spec=graph_spec,
        )
        if template is not None:
            apply_template_to_record(record, template)
            await _service.store.save(record)
        elif judge_mode:
            record.judge_mode = judge_mode
            await _service.store.save(record)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return await _workflow_info(record)


@router.get("/templates", summary="Workflow 模板列表")
async def list_workflow_templates():
    items = await _template_store.list_all()
    return [_template_info(t) for t in items]


@router.get("/templates/{template_id}", summary="Workflow 模板详情")
async def get_workflow_template(template_id: str):
    item = await _template_store.get(template_id)
    if item is None:
        raise HTTPException(status_code=404, detail="模板不存在")
    return _template_info(item)


@router.post("/templates", summary="创建 Workflow 模板")
async def create_workflow_template(body: TemplateCreateRequest):
    try:
        item = await _template_store.create(
            name=body.name,
            description=body.description,
            user_goal=body.user_goal,
            judge_mode=body.judge_mode,
            graph=body.graph,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return _template_info(item)


@router.put("/templates/{template_id}", summary="更新 Workflow 模板")
async def update_workflow_template(template_id: str, body: TemplateUpdateRequest):
    try:
        item = await _template_store.update(
            template_id,
            name=body.name,
            description=body.description,
            user_goal=body.user_goal,
            judge_mode=body.judge_mode,
            graph=body.graph,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="模板不存在") from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return _template_info(item)


@router.post("/templates/{template_id}/duplicate", summary="复制 Workflow 模板")
async def duplicate_workflow_template(template_id: str, body: TemplateDuplicateRequest = TemplateDuplicateRequest()):
    src = await _template_store.get(template_id)
    if src is None:
        raise HTTPException(status_code=404, detail="模板不存在")
    name = str(body.name or "").strip() or f"{src.name} 副本"
    try:
        item = await _template_store.create(
            name=name,
            description=src.description,
            user_goal=src.user_goal,
            judge_mode=src.judge_mode,
            graph=src.graph,
            source_workflow_id=template_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return _template_info(item)


@router.delete("/templates/{template_id}", summary="删除 Workflow 模板")
async def delete_workflow_template(template_id: str):
    if not await _template_store.delete(template_id):
        raise HTTPException(status_code=404, detail="模板不存在")
    return {"ok": True, "template_id": template_id}


@router.post("", summary="创建工作流")
async def create_workflow(body: WorkflowCreateRequest):
    plan_mode = normalize_plan_mode(body.plan_mode)
    template_id = str(body.template_id or "").strip()
    graph_spec = body.graph
    if plan_mode == PlanMode.TEMPLATE.value:
        if not template_id:
            raise HTTPException(status_code=400, detail="模板模式须选择 template_id")
        template = await _template_store.get(template_id)
        if template is None:
            raise HTTPException(status_code=404, detail="模板不存在")
    try:
        record = await _service.store.create(
            name=body.name,
            description=body.description,
            workspace_path=body.workspace_path,
            requirement_id=body.requirement_id,
            plan_mode=plan_mode,
            template_id=template_id,
            user_goal=body.user_goal,
            graph_spec=graph_spec,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return await _workflow_info(record)


@router.get("", summary="工作流列表")
async def list_workflows():
    records = await _service.store.list_all()
    return [await _workflow_info(r) for r in records]


@router.get("/{workflow_id}", summary="获取工作流")
async def get_workflow(workflow_id: str):
    record = await _service.store.get(workflow_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return await _workflow_info(record)


@router.put("/{workflow_id}", summary="更新工作流元数据")
async def update_workflow(workflow_id: str, body: WorkflowUpdateRequest):
    record = await _service.store.get(workflow_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    updates = body.model_dump(exclude_unset=True)
    if "name" in updates and updates["name"] is not None:
        record.name = updates["name"]
    if "description" in updates and updates["description"] is not None:
        record.description = updates["description"]
    if "workspace_path" in updates and updates["workspace_path"] is not None:
        record.workspace_path = updates["workspace_path"]
    if "user_goal" in updates and updates["user_goal"] is not None:
        record.user_goal = updates["user_goal"]
        record.plan_state.user_goal = updates["user_goal"]
    if "plan_mode" in updates and updates["plan_mode"] is not None:
        raise HTTPException(status_code=400, detail="编排方式在创建 Session 时选定，不可修改")
    if "template_id" in updates and updates["template_id"] is not None:
        raise HTTPException(status_code=400, detail="模板在创建 Session 时选定，请在模板管理中编辑")
    if "llm_provider" in updates and updates["llm_provider"] is not None:
        record.llm_provider = updates["llm_provider"]
    if "llm_model" in updates and updates["llm_model"] is not None:
        record.llm_model = updates["llm_model"]
    if "judge_mode" in updates and updates["judge_mode"] is not None:
        record.judge_mode = updates["judge_mode"]
    await _service.store.save(record)
    return await _workflow_info(record)


@router.post("/{workflow_id}/save-as-template", summary="（已废弃）将当前 Session 保存为模板")
async def save_workflow_as_template(workflow_id: str, body: SaveAsTemplateRequest):
    raise HTTPException(
        status_code=400,
        detail="请在模板管理中编辑拓扑；可从已有模板复制后修改",
    )


@router.post("/{workflow_id}/init-from-template", summary="用模板重新初始化 Session 工作流")
async def init_workflow_from_template(workflow_id: str, body: InitFromTemplateRequest):
    try:
        record = await _service.init_from_template(workflow_id, body.template_id)
    except KeyError as e:
        key = str(e.args[0]) if e.args else workflow_id
        if key == workflow_id:
            raise HTTPException(status_code=404, detail="Workflow not found") from None
        raise HTTPException(status_code=404, detail="模板不存在") from None
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return await _workflow_info(record)


@router.post("/{workflow_id}/apply-template/{template_id}", summary="（兼容）将模板应用到当前 Session")
async def apply_template_to_workflow(workflow_id: str, template_id: str):
    return await init_workflow_from_template(workflow_id, InitFromTemplateRequest(template_id=template_id))


@router.put("/{workflow_id}/topology", summary="更新拓扑")
async def update_topology(workflow_id: str, body: TopologyUpdateRequest):
    try:
        record = await _service.store.update_topology(workflow_id, body.graph)
    except KeyError:
        raise HTTPException(status_code=404, detail="Workflow not found") from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return await _workflow_info(record)


@router.post("/{workflow_id}/generate-graph", summary="LLM 生成编排拓扑")
async def generate_graph(workflow_id: str, body: GenerateGraphRequest):
    try:
        record = await _service.generate_graph(
            workflow_id,
            user_goal=body.user_goal,
            recreate=body.recreate,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Workflow not found") from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"message": "编排拓扑已生成", "workflow": await _workflow_info(record)}


@router.post("/{workflow_id}/execute", summary="执行工作流")
async def execute_workflow(workflow_id: str, body: ExecuteRequest):
    try:
        await _service.execute(
            workflow_id,
            start_node_id=body.start_node_id,
            clear_history=body.clear_history,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Workflow not found") from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    record = await _service.store.get(workflow_id)
    return {"message": "执行已启动", "workflow": await _workflow_info(record)}


@router.post("/{workflow_id}/abort", summary="中止执行")
async def abort_workflow(workflow_id: str):
    ok = await _service.abort(workflow_id)
    if not ok:
        raise HTTPException(status_code=404, detail="无进行中的执行")
    return {"message": "已发送中止信号"}


@router.get("/{workflow_id}/pending", summary="待人工确认 / 待分裂任务")
async def get_pending(workflow_id: str):
    record = await _service.store.get(workflow_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    await hydrate_session_graph(record, _template_store)
    return _service.get_pending(record)


@router.post("/{workflow_id}/gate/approve", summary="人工卡点：通过")
async def gate_approve(workflow_id: str, body: GateDecisionRequest):
    try:
        record = await _service.gate_decision(workflow_id, approve=True, comment=body.comment)
    except KeyError:
        raise HTTPException(status_code=404, detail="Workflow not found") from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return {"message": "已通过，继续执行", "workflow": await _workflow_info(record)}


@router.post("/{workflow_id}/gate/reject", summary="人工卡点：驳回")
async def gate_reject(workflow_id: str, body: GateDecisionRequest):
    try:
        record = await _service.gate_decision(workflow_id, approve=False, comment=body.comment)
    except KeyError:
        raise HTTPException(status_code=404, detail="Workflow not found") from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return {"message": "已驳回，返回返工步骤", "workflow": await _workflow_info(record)}


@router.post("/{workflow_id}/expand/apply", summary="确认任务分裂并继续执行")
async def expand_apply(workflow_id: str):
    try:
        record = await _service.expand_apply(workflow_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Workflow not found") from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return {"message": "任务分裂已应用", "workflow": await _workflow_info(record)}


@router.get("/{workflow_id}/doc/requirement", summary="需求目录 Markdown 说明")
async def get_requirement_doc(workflow_id: str):
    record = await _service.store.get(workflow_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if not record.requirement_id:
        raise HTTPException(status_code=404, detail="当前 Session 未绑定需求")
    doc = load_requirement_readme(record.workspace_path, record.requirement_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="未找到需求说明 Markdown")
    return doc.to_dict()


@router.get("/{workflow_id}/nodes/{node_id}/doc", summary="节点相关 Markdown 文档")
async def get_node_doc(workflow_id: str, node_id: str):
    record = await _service.store.get(workflow_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    await hydrate_session_graph(record, _template_store)
    graph = record.plan_state.resolve_graph()
    if graph is None:
        raise HTTPException(status_code=404, detail="Planning graph not found")
    output = str(record.plan_state.node_outputs.get(node_id) or "")
    try:
        doc = load_node_doc(
            workspace_path=record.workspace_path,
            requirement_id=record.requirement_id,
            graph=graph,
            node_id=node_id,
            node_output=output,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}") from None
    return doc.to_dict()


_WORKSPACE_FILE_MAX_BYTES = 2 * 1024 * 1024


@router.get("/{workflow_id}/workspace-file", summary="读取 Workspace 文本文件")
async def read_workspace_file(workflow_id: str, path: str = Query(..., min_length=1)):
    record = await _service.store.get(workflow_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    ws = normalize_workspace_path(record.workspace_path)
    if not ws:
        raise HTTPException(status_code=400, detail="Workspace 未配置")
    resolved = resolve_workspace_ref_path(ws, record.requirement_id, path)
    if resolved is None:
        raise HTTPException(status_code=400, detail="路径无效或超出 Workspace")
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    try:
        size = resolved.stat().st_size
    except OSError as e:
        raise HTTPException(status_code=404, detail="无法读取文件") from e
    if size > _WORKSPACE_FILE_MAX_BYTES:
        raise HTTPException(status_code=413, detail="文件过大，暂不支持在线预览")
    try:
        text = resolved.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise HTTPException(status_code=415, detail="无法以文本方式读取该文件") from e
    return {
        "path": path,
        "resolved_path": str(resolved.resolve()),
        "name": resolved.name,
        "content": text,
    }


@router.get("/{workflow_id}/nodes/{node_id}/output", summary="节点执行产出")
async def get_node_output(workflow_id: str, node_id: str):
    try:
        return await _service.get_node_output(workflow_id, node_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Workflow not found") from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{workflow_id}/nodes/{node_id}/revise", summary="修正意见并重跑节点")
async def revise_node(workflow_id: str, node_id: str, body: NodeReviseRequest):
    try:
        record = await _service.revise_node(workflow_id, node_id, feedback=body.feedback)
    except KeyError:
        raise HTTPException(status_code=404, detail="Workflow not found") from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return {"message": "已提交修正并重跑", "workflow": await _workflow_info(record)}


@router.get("/{workflow_id}/messages", summary="执行消息")
async def get_messages(workflow_id: str):
    record = await _service.store.get(workflow_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return record.messages


@router.get("/{workflow_id}/node-messages/{node_id}", summary="CLI 节点外部会话历史")
async def get_node_messages(workflow_id: str, node_id: str):
    record = await _service.store.get(workflow_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    metadata = {PLAN_GRAPH_METADATA_KEY: record.plan_state.to_metadata()}
    plan_state = PlanGraphState.from_metadata(metadata)
    if plan_state is None:
        raise HTTPException(status_code=404, detail="Planning graph not found")
    graph = plan_state.resolve_graph()
    if graph is None:
        raise HTTPException(status_code=404, detail="Planning graph not found")
    key = (node_id or "").strip()
    graph_node = graph.nodes.get(key)
    if graph_node is None:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")
    if not graph_node.is_cli():
        raise HTTPException(status_code=400, detail="Node is not CLI executor")
    cli_session_id = (plan_state.node_session_id.get(key) or "").strip()
    if not cli_session_id:
        return []
    try:
        msgs = await CliHistoryReader.fetch_node_messages(
            graph_node,
            cli_session_id,
            record.workspace_path or "",
        )
    except ValueError:
        return []
    except FileNotFoundError:
        return []
    return [msg.to_user_message() for msg in msgs]


@router.delete("/{workflow_id}", summary="删除工作流")
async def delete_workflow(workflow_id: str):
    if not await _service.store.delete(workflow_id):
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"message": "deleted"}

import pytest
from app.session.subject_schema import (
    SUBJECT_KIND_REQUIREMENT,
    SUBJECT_KIND_WORKSPACE,
    SUBJECT_TYPE_FEATURE,
    SUBJECT_TYPE_REPO,
    infer_subject_schema_from_template,
    normalize_subject_schema,
    schema_to_subject_type,
    template_matches_subject_type,
)
from app.session.template_store import WorkflowTemplate
from app.session.workflow_store import (
    WorkflowRecord,
    WorkflowStore,
    hydrate_record_subject,
    record_global_placeholders,
    sync_record_subject_fields,
)


def test_normalize_subject_schema_defaults():
    schema = normalize_subject_schema({})
    assert schema["kind"] == SUBJECT_KIND_REQUIREMENT
    assert schema["granularity"] == "ir"


def test_infer_workspace_subject_from_user_goal():
    schema = infer_subject_schema_from_template(user_goal="对 {workspace} 下 repos/ 完成逆向")
    assert schema["kind"] == SUBJECT_KIND_WORKSPACE
    assert schema["granularity"] == "workspace"


def test_infer_requirement_sr_subject():
    schema = infer_subject_schema_from_template(
        user_goal="对 {requirement_id} 的 {sr_id} 完成架构分析",
    )
    assert schema["kind"] == SUBJECT_KIND_REQUIREMENT
    assert schema["granularity"] == "sr"


def test_hydrate_legacy_requirement_record():
    record = WorkflowRecord(workflow_id="wf_test", requirement_id="REQ-001")
    hydrate_record_subject(record)
    assert record.subject_kind == SUBJECT_KIND_REQUIREMENT
    assert record.subject_id == "REQ-001"


def test_sync_workspace_record_clears_requirement_id():
    record = WorkflowRecord(workflow_id="wf_test", requirement_id="REQ-001")
    sync_record_subject_fields(record, subject_kind=SUBJECT_KIND_WORKSPACE, subject_id="")
    assert record.subject_kind == SUBJECT_KIND_WORKSPACE
    assert record.requirement_id == ""


def test_record_global_placeholders_includes_subject_refs():
    record = WorkflowRecord(
        workflow_id="wf_test",
        workspace_path="/tmp/ws",
        requirement_id="REQ-001",
        subject_kind=SUBJECT_KIND_REQUIREMENT,
        subject_id="REQ-001",
        subject_refs={"sr_id": "SR-001"},
    )
    placeholders = record_global_placeholders(record)
    assert placeholders["workspace"] == "/tmp/ws"
    assert placeholders["requirement_id"] == "REQ-001"
    assert placeholders["sr_id"] == "SR-001"


@pytest.mark.asyncio
async def test_find_by_subject_workspace_template(tmp_path):
    store = WorkflowStore(root_dir=str(tmp_path / "data"))
    created = await store.create(
        name="Workspace",
        workspace_path=str(tmp_path),
        subject_kind=SUBJECT_KIND_WORKSPACE,
        subject_id="",
        template_id="tpl_rev_repo",
    )
    found = await store.find_by_subject(
        str(tmp_path),
        SUBJECT_KIND_WORKSPACE,
        "",
        template_id="tpl_rev_repo",
    )
    assert found is not None
    assert found.workflow_id == created.workflow_id
    missing = await store.find_by_subject(
        str(tmp_path),
        SUBJECT_KIND_WORKSPACE,
        "",
        template_id="tpl_rev_arch",
    )
    assert missing is None


def test_template_from_dict_reads_subject_schema():
    item = WorkflowTemplate.from_dict({
        "template_id": "tpl_demo",
        "name": "demo",
        "category": "逆向",
        "subject_schema": {"kind": "workspace", "granularity": "workspace"},
        "graph": {},
    })
    assert item.subject_schema["kind"] == SUBJECT_KIND_WORKSPACE


def test_schema_to_subject_type_all_kinds():
    assert schema_to_subject_type({"kind": "feature", "granularity": "feature"}) == SUBJECT_TYPE_FEATURE
    assert schema_to_subject_type({"kind": "repo", "granularity": "repo"}) == SUBJECT_TYPE_REPO


def test_template_matches_subject_type_repo():
    tpl = WorkflowTemplate.from_dict({
        "template_id": "tpl_ar_to_code",
        "name": "AR to code",
        "subject_schema": {"kind": "repo", "granularity": "repo"},
        "graph": {},
    })
    assert template_matches_subject_type(tpl, SUBJECT_TYPE_REPO)
    assert not template_matches_subject_type(tpl, SUBJECT_TYPE_FEATURE)

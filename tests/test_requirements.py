import pytest
from app.workspace.paths import normalize_workspace_path
from app.workspace.requirements import list_requirements, requirement_path
from app.session.workflow_store import WorkflowStore


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "project"
    req_root = ws / "requirements"
    (req_root / "feat-login").mkdir(parents=True)
    (req_root / "feat-login" / "README.md").write_text("# 用户登录功能\n实现 OAuth 登录", encoding="utf-8")
    (req_root / "feat-pay").mkdir(parents=True)
    return ws


@pytest.mark.asyncio
async def test_list_requirements(workspace):
    items = list_requirements(str(workspace))
    assert [i.requirement_id for i in items] == ["feat-login", "feat-pay"]
    assert "登录" in items[0].summary


@pytest.mark.asyncio
async def test_find_by_requirement(workspace, tmp_path):
    store = WorkflowStore(root_dir=str(tmp_path / "data"))
    ws = normalize_workspace_path(str(workspace))
    created = await store.create(
        name="feat-login",
        workspace_path=ws,
        requirement_id="feat-login",
        user_goal="登录",
    )
    found = await store.find_by_requirement(str(workspace), "feat-login")
    assert found is not None
    assert found.workflow_id == created.workflow_id
    assert await store.find_by_requirement(str(workspace), "feat-pay") is None


def test_requirement_path(workspace):
    path = requirement_path(str(workspace), "feat-login")
    assert path.name == "feat-login"

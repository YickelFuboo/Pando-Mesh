import json

from app.llms.chat_models.models_config import API_KEY_MASK, ModelsConfig


def test_apply_update_preserves_api_key_when_masked(tmp_path, monkeypatch):
    models_dir = tmp_path / "data" / "models"
    models_dir.mkdir(parents=True)
    path = models_dir / "chat_models.json"
    path.write_text(json.dumps({
        "default": {"provider": "deepseek", "model": "deepseek-chat"},
        "fallback": {"provider": "openai", "model": "gpt-4o-mini"},
        "models": {
            "deepseek": {
                "description": "DeepSeek",
                "base_url": "https://api.deepseek.com/v1",
                "api_key": "secret-key-123",
                "is_valid": 1,
                "instances": {"deepseek-chat": {}},
            },
        },
    }, ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(
        "app.llms.chat_models.models_config._models_path",
        lambda: path,
    )
    cfg = ModelsConfig()
    public = cfg.to_public_dict()
    assert public["config"]["models"]["deepseek"]["api_key"] == API_KEY_MASK
    assert public["config"]["models"]["deepseek"]["api_key_set"] is True

    result = cfg.apply_update({
        "config": {
            "default": {"provider": "deepseek", "model": "deepseek-chat"},
            "models": {
                "deepseek": {
                    "base_url": "https://api.deepseek.com/v1",
                    "is_valid": 1,
                    "api_key": API_KEY_MASK,
                },
            },
        },
    })
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["models"]["deepseek"]["api_key"] == "secret-key-123"
    assert result["available"] is True


def test_apply_update_writes_new_api_key(tmp_path, monkeypatch):
    models_dir = tmp_path / "data" / "models"
    models_dir.mkdir(parents=True)
    path = models_dir / "chat_models.json"
    path.write_text(json.dumps({
        "default": {"provider": "openai", "model": "gpt-4o-mini"},
        "models": {
            "openai": {
                "base_url": "https://api.openai.com/v1",
                "api_key": "",
                "is_valid": 0,
                "instances": {"gpt-4o-mini": {}},
            },
        },
    }), encoding="utf-8")

    monkeypatch.setattr(
        "app.llms.chat_models.models_config._models_path",
        lambda: path,
    )
    cfg = ModelsConfig()
    cfg.apply_update({
        "config": {
            "models": {
                "openai": {
                    "api_key": "sk-new-key",
                    "is_valid": 1,
                },
            },
        },
    })
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["models"]["openai"]["api_key"] == "sk-new-key"
    assert saved["models"]["openai"]["is_valid"] == 1

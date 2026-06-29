import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from app.config.settings import settings

logger = logging.getLogger(__name__)

API_KEY_MASK = "********"


def _models_path() -> Path:
    return settings.models_path


def _mask_api_key(key: str) -> str:
    return API_KEY_MASK if str(key or "").strip() else ""


class ModelsConfig:
    def __init__(self) -> None:
        self._config: Dict[str, Any] = {}
        self.reload()

    def reload(self) -> None:
        path = _models_path()
        if not path.is_file():
            self._config = {}
            return
        try:
            self._config = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Invalid LLM config %s: %s", path, e)
            self._config = {}

    def is_available(self) -> bool:
        try:
            self.resolve_model()
            return True
        except (ValueError, FileNotFoundError):
            return False

    def resolve_model(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Tuple[str, str, str, str]:
        """返回 (provider, model, api_key, base_url)。"""
        env_provider = (settings.llm_provider or "").strip()
        env_model = (settings.llm_model or "").strip()
        env_key = (settings.llm_api_key or "").strip()
        env_base = (settings.llm_base_url or "").strip()

        prov = (provider or env_provider or "").strip()
        mdl = (model or env_model or "").strip()

        if not self._config:
            if env_key and env_base and mdl:
                return prov or "openai", mdl, env_key, env_base
            raise FileNotFoundError(f"LLM 配置不存在: {_models_path()}")

        default = self._config.get("default") or {}
        if not prov:
            prov = str(default.get("provider") or "").strip()
        if not mdl:
            mdl = str(default.get("model") or "").strip()

        models = self._config.get("models") or {}
        provider_cfg = models.get(prov) if prov else None
        if provider_cfg is None:
            for name, cfg in models.items():
                if cfg.get("is_valid", 0) == 1:
                    provider_cfg = cfg
                    prov = name
                    break
        if provider_cfg is None:
            raise ValueError("无可用 LLM provider，请配置 data/models/chat_models.json")

        api_key = str(provider_cfg.get("api_key") or "").strip()
        base_url = str(provider_cfg.get("base_url") or "").strip()
        if not api_key:
            api_key = env_key
        if not base_url:
            base_url = env_base
        if not api_key or not base_url:
            raise ValueError(f"LLM provider「{prov}」缺少 api_key 或 base_url")
        if not mdl:
            instances = provider_cfg.get("instances") or {}
            if instances:
                mdl = next(iter(instances.keys()))
        if not mdl:
            raise ValueError(f"LLM provider「{prov}」未指定 model")
        return prov, mdl, api_key, base_url

    def fallback_pairs(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> List[Tuple[str, str]]:
        """按优先级返回 (provider, model) 列表，供 call_with_llm_fallback 依次尝试。

        顺序：显式参数 → default → chat_models.json 的 fallback 段。
        """
        pairs: List[Tuple[str, str]] = []
        if provider or model:
            try:
                prov, mdl, _, _ = self.resolve_model(provider, model)
                pairs.append((prov, mdl))
            except (ValueError, FileNotFoundError):
                pass
        try:
            prov, mdl, _, _ = self.resolve_model()
            if (prov, mdl) not in pairs:
                pairs.append((prov, mdl))
        except (ValueError, FileNotFoundError):
            pass
        fb = self._config.get("fallback") or {}
        fb_prov = str(fb.get("provider") or "").strip()
        fb_mdl = str(fb.get("model") or "").strip()
        if fb_prov and fb_mdl and (fb_prov, fb_mdl) not in pairs:
            pairs.append((fb_prov, fb_mdl))
        return pairs

    def resolved_default(self) -> Dict[str, str]:
        try:
            prov, mdl, _, _ = self.resolve_model()
            return {"provider": prov, "model": mdl}
        except (ValueError, FileNotFoundError):
            default = self._config.get("default") or {}
            return {
                "provider": str(default.get("provider") or ""),
                "model": str(default.get("model") or ""),
            }

    def to_public_dict(self) -> Dict[str, Any]:
        self.reload()
        path = _models_path()
        raw: Dict[str, Any] = {}
        if path.is_file():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                raw = {}
        public = json.loads(json.dumps(raw))
        models = public.get("models") or {}
        for prov in models.values():
            key = str(prov.get("api_key") or "").strip()
            prov["api_key_set"] = bool(key)
            prov["api_key"] = _mask_api_key(key)
        return {
            "available": self.is_available(),
            "models_file": str(path),
            "config": public,
            "resolved": self.resolved_default(),
        }

    def apply_update(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.reload()
        path = _models_path()
        if not path.is_file():
            raise FileNotFoundError(f"LLM 配置不存在: {path}")
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            raise ValueError(f"无法读取 LLM 配置: {e}") from e
        incoming = payload.get("config") if isinstance(payload.get("config"), dict) else payload
        if not isinstance(incoming, dict):
            raise ValueError("配置格式无效")
        if isinstance(incoming.get("default"), dict):
            current["default"] = {
                **(current.get("default") or {}),
                **incoming["default"],
            }
        if isinstance(incoming.get("fallback"), dict):
            current["fallback"] = {
                **(current.get("fallback") or {}),
                **incoming["fallback"],
            }
        incoming_models = incoming.get("models")
        if isinstance(incoming_models, dict):
            current_models = current.setdefault("models", {})
            for prov_id, prov_in in incoming_models.items():
                if prov_id not in current_models or not isinstance(prov_in, dict):
                    continue
                prov_cur = current_models[prov_id]
                for key, value in prov_in.items():
                    if key == "api_key":
                        new_key = str(value or "").strip()
                        if new_key in ("", API_KEY_MASK):
                            continue
                        prov_cur["api_key"] = new_key
                    elif key in ("description", "base_url", "is_valid"):
                        prov_cur[key] = value
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.reload()
        return self.to_public_dict()


models_config = ModelsConfig()

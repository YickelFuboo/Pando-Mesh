import logging
from typing import Any, AsyncIterator, Dict, List, Optional
from openai import AsyncOpenAI
from app.maas.chat_models.models_config import models_config

logger = logging.getLogger(__name__)


class ChatModel:
    def __init__(self, provider: str, model: str, api_key: str, base_url: str) -> None:
        self.provider = provider
        self.model = model
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url, max_retries=0)

    def _build_messages(
        self,
        system_prompt: str,
        user_question: str,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []
        if system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt.strip()})
        if history:
            for item in history:
                if isinstance(item, dict) and item.get("role") in {"user", "assistant", "system"}:
                    messages.append({"role": item["role"], "content": str(item.get("content") or "")})
        if user_question.strip():
            messages.append({"role": "user", "content": user_question.strip()})
        if not messages:
            raise ValueError("messages 为空")
        return messages

    async def chat(
        self,
        *,
        system_prompt: str,
        user_question: str,
        history: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
    ) -> str:
        messages = self._build_messages(system_prompt, user_question, history)
        resp = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        choice = resp.choices[0] if resp.choices else None
        return str(choice.message.content or "") if choice and choice.message else ""

    async def chat_stream(
        self,
        *,
        system_prompt: str,
        user_question: str,
        history: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        messages = self._build_messages(system_prompt, user_question, history)
        stream = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            stream=True,
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content


def create_chat_model(provider: Optional[str] = None, model: Optional[str] = None) -> ChatModel:
    prov, mdl, api_key, base_url = models_config.resolve_model(provider, model)
    return ChatModel(prov, mdl, api_key, base_url)

import asyncio
import logging
from typing import Any, Awaitable, Callable, List, Optional, Tuple
from app.llms.chat_models.client import ChatModel, create_chat_model
from app.llms.chat_models.models_config import models_config

logger = logging.getLogger(__name__)


async def call_with_llm_fallback(
    model_pairs: List[Tuple[str, str]],
    fn: Callable[[ChatModel], Awaitable[Any]],
) -> Tuple[Any, ChatModel]:
    if not model_pairs:
        model_pairs = models_config.fallback_pairs()
    if not model_pairs:
        raise RuntimeError("未配置 LLM，请设置 data/models/chat_models.json 或环境变量")
    last_error: Optional[Exception] = None
    for i, (provider, model) in enumerate(model_pairs):
        llm = create_chat_model(provider or None, model or None)
        try:
            result = await fn(llm)
            if i > 0:
                logger.info("LLM fallback succeeded: %s/%s", provider, model)
            return result, llm
        except asyncio.CancelledError:
            raise
        except Exception as e:
            last_error = e
            if i >= len(model_pairs) - 1:
                raise
            logger.warning("LLM call failed (%s/%s), retry: %s", provider, model, e)
    if last_error:
        raise last_error
    raise RuntimeError("call_with_llm_fallback: no model pairs")

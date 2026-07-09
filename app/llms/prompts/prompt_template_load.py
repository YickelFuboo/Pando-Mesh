import logging
from typing import Any, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.config.settings import settings

logger = logging.getLogger(__name__)


def get_prompt_template(path: str, file_name: str, params: Optional[dict[str, Any]] = None) -> str:
    prompt_path = path if path else str(settings.prompts_dir)
    try:
        env = Environment(
            loader=FileSystemLoader(prompt_path),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        template = env.get_template(file_name)
        if params:
            return template.render(**params)
        return template.render()
    except Exception as e:
        logger.error("Error loading template %s from %s: %s", file_name, prompt_path, e)
        raise RuntimeError(f"无法加载 prompt 模板 {file_name}（目录: {prompt_path}）") from e

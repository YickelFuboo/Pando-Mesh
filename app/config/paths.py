from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
ENV_FILE = PROJECT_ROOT / ".env"


def _resolve_under_project(path: str | Path, *, base: Path = PROJECT_ROOT) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = base / p
    return p.resolve()


def resolve_data_dir(runtime_data_dir: str) -> Path:
    return _resolve_under_project(runtime_data_dir)


def resolve_prompts_dir(runtime_data_dir: str) -> Path:
    configured = resolve_data_dir(runtime_data_dir) / "prompts"
    if configured.is_dir():
        return configured
    return DEFAULT_DATA_DIR / "prompts"


def resolve_models_path(llm_models_file: str, runtime_data_dir: str) -> Path:
    configured = (llm_models_file or "").strip()
    if configured:
        return _resolve_under_project(configured)
    return resolve_data_dir(runtime_data_dir) / "models" / "chat_models.json"

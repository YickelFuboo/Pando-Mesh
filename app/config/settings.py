from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.config.paths import (
    DEFAULT_DATA_DIR,
    ENV_FILE,
    PROJECT_ROOT,
    resolve_data_dir,
    resolve_models_path,
    resolve_prompts_dir,
)


class Settings(BaseSettings):
    service_host: str = Field(default="0.0.0.0", alias="SERVICE_HOST")
    service_port: int = Field(default=8100, alias="SERVICE_PORT")
    debug: bool = Field(default=False, alias="DEBUG")
    runtime_data_dir: str = Field(default=str(DEFAULT_DATA_DIR), alias="RUNTIME_DATA_DIR")
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")
    llm_models_file: str = Field(default="", alias="LLM_MODELS_FILE")
    llm_provider: str = Field(default="", alias="LLM_PROVIDER")
    llm_model: str = Field(default="", alias="LLM_MODEL")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_base_url: str = Field(default="", alias="LLM_BASE_URL")
    judge_mode: str = Field(default="auto", alias="JUDGE_MODE")

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        populate_by_name=True,
        extra="ignore",
    )

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    @property
    def data_dir(self) -> Path:
        return resolve_data_dir(self.runtime_data_dir)

    @property
    def prompts_dir(self) -> Path:
        return resolve_prompts_dir(self.runtime_data_dir)

    @property
    def models_path(self) -> Path:
        return resolve_models_path(self.llm_models_file, self.runtime_data_dir)


settings = Settings()

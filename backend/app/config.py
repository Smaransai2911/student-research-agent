from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name:    str  = Field(default="Student Research Agent")
    app_version: str  = Field(default="1.0.0")
    debug:       bool = Field(default=False)
    host:        str  = Field(default="0.0.0.0")
    port:        int  = Field(default=8000)

    upload_dir:      str = Field(default="backend/data/uploads")
    vectorstore_dir: str = Field(default="backend/vectorstore")
    log_dir:         str = Field(default="backend/logs")

    max_file_size_mb:   int = Field(default=20)
    allowed_extensions: str = Field(default=".pdf")
    embedding_model:    str = Field(default="all-MiniLM-L6-v2")

    generation_strategy: str = Field(default="hf_inference_api")
    hf_api_token:        str = Field(default="")
    hf_model_id:         str = Field(default="mistralai/Mistral-7B-Instruct-v0.3")

    retrieval_top_k:           int   = Field(default=5)
    retrieval_score_threshold: float = Field(default=0.35)
    allowed_origins:           str   = Field(default="*")
    backend_url:               str   = Field(default="http://localhost:8000")

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def upload_path(self) -> Path:
        return Path(self.upload_dir)

    @property
    def vectorstore_path(self) -> Path:
        return Path(self.vectorstore_dir)

    @property
    def log_path(self) -> Path:
        return Path(self.log_dir)

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()

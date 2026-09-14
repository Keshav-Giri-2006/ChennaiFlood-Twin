"""Application configuration.

All environment-specific values come from environment variables (or a local
``backend/.env`` file). No machine-specific absolute paths are embedded here:
defaults are derived from the repository layout relative to this file, so the
same code works on a Windows workstation and inside a Linux container.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> parents[3] is the repository root.
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_REPO_ROOT = _BACKEND_DIR.parent

APP_VERSION = "0.1.0"
SERVICE_NAME = "chennaiflood-twin-api"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # --- Project data locations (read-only inputs) -----------------------
    data_dir: Path = Field(default=_REPO_ROOT, alias="DATA_DIR")
    raw_data_dir: Path | None = Field(default=None, alias="RAW_DATA_DIR")
    processed_data_dir: Path | None = Field(default=None, alias="PROCESSED_DATA_DIR")
    gis_dir: Path | None = Field(default=None, alias="GIS_DIR")
    model_dir: Path | None = Field(default=None, alias="MODEL_DIR")
    registry_dir: Path = Field(default=_BACKEND_DIR / "config", alias="REGISTRY_DIR")

    # --- Runtime locations (written by the application) ------------------
    runtime_dir: Path = Field(default=_BACKEND_DIR / "runtime", alias="RUNTIME_DIR")
    simulation_workdir: Path | None = Field(default=None, alias="SIMULATION_WORKDIR")
    results_dir: Path | None = Field(default=None, alias="RESULTS_DIR")
    web_assets_dir: Path | None = Field(default=None, alias="WEB_ASSETS_DIR")
    database_url: str | None = Field(default=None, alias="DATABASE_URL")

    # --- Simulation engine ------------------------------------------------
    # Path to the SWMM command-line executable (runswmm). If unset, the
    # executable is looked up on PATH. Never taken from API requests.
    swmm_executable: str | None = Field(default=None, alias="SWMM_EXECUTABLE")
    swmm_timeout_seconds: int = Field(default=900, alias="SWMM_TIMEOUT_SECONDS", ge=10)
    simulation_max_concurrent: int = Field(default=1, alias="SIMULATION_MAX_CONCURRENT", ge=1, le=4)

    model_version: str = Field(default="ward176-hydraulic-reconstructed-v1", alias="MODEL_VERSION")
    processing_version: str = Field(default="swmm-results-v1", alias="PROCESSING_VERSION")
    gis_processing_version: str = Field(default="web-gis-v1", alias="GIS_PROCESSING_VERSION")
    flood_processing_version: str = Field(default="flood-processing-v1", alias="FLOOD_PROCESSING_VERSION")

    # --- API ----------------------------------------------------------------
    cors_allow_origins: list[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        alias="CORS_ALLOW_ORIGINS",
    )

    # --- Future AWS settings (not used by the local MVP) --------------------
    aws_region: str | None = Field(default=None, alias="AWS_REGION")
    s3_data_bucket: str | None = Field(default=None, alias="S3_DATA_BUCKET")
    s3_results_bucket: str | None = Field(default=None, alias="S3_RESULTS_BUCKET")

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("["):
                return value  # JSON list, let pydantic parse it
            return [v.strip() for v in value.split(",") if v.strip()]
        return value

    # Resolved paths ------------------------------------------------------------
    @property
    def raw_dir(self) -> Path:
        return (self.raw_data_dir or self.data_dir / "data_raw").resolve()

    @property
    def processed_dir(self) -> Path:
        return (self.processed_data_dir or self.data_dir / "data_processed").resolve()

    @property
    def gis_source_dir(self) -> Path:
        return (self.gis_dir or self.data_dir / "gis").resolve()

    @property
    def models_dir(self) -> Path:
        return (self.model_dir or self.data_dir / "simulation").resolve()

    @property
    def workdir(self) -> Path:
        return (self.simulation_workdir or self.runtime_dir / "simulation_runs").resolve()

    @property
    def results_root(self) -> Path:
        return (self.results_dir or self.runtime_dir / "results").resolve()

    @property
    def web_assets_root(self) -> Path:
        return (self.web_assets_dir or self.runtime_dir / "web_assets").resolve()

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        db_path = (self.runtime_dir / "chennaiflood.sqlite3").resolve()
        return f"sqlite:///{db_path.as_posix()}"

    def ensure_runtime_dirs(self) -> None:
        for path in (self.runtime_dir, self.workdir, self.results_root, self.web_assets_root):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()

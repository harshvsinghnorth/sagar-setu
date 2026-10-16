from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
STATIC_DIR = DATA_DIR / "static"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
CACHE_DIR = DATA_DIR / "cache"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    # -- LLM: the only paid-or-free-tier component. "auto" picks gemini > anthropic > none.
    llm_provider: str = "auto"  # auto | gemini | anthropic | ollama | none
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"  # verified 2026-09-16; free tier, Tamil OK
    # Tried in order when the model above is out of its daily free quota (429) or overloaded
    # (503). Free-tier quotas are per model, so each fallback has its own daily allowance.
    gemini_fallback_models: str = "gemini-3.5-flash-lite,gemini-3.1-flash-lite"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-5"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    llm_timeout_s: float = 20.0
    copernicus_username: str = ""
    copernicus_password: str = ""
    imd_api_key: str = ""
    bhashini_user_id: str = ""
    bhashini_api_key: str = ""

    # Any single fetch slower than this falls down the source chain (CLAUDE.md rule 3).
    fetch_timeout_s: float = 2.0
    # Sources that are slow by nature (WFS downloads) get this budget in the snapshot job only.
    snapshot_timeout_s: float = 60.0


settings = Settings()

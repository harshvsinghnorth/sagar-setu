from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
STATIC_DIR = DATA_DIR / "static"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
CACHE_DIR = DATA_DIR / "cache"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    anthropic_api_key: str = ""
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

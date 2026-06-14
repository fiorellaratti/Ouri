from __future__ import annotations

from enum import Enum
from pathlib import Path

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
FIXTURES_DIR = DATA_DIR / "fixtures"
ASSETS_DIR = PROJECT_ROOT / "assets"
OURI_HOME = Path.home() / ".ouri"
TOKENS_PATH = OURI_HOME / "tokens.json"
DAY_STATE_PATH = OURI_HOME / "day_state.json"


class DataSource(str, Enum):
    FIXTURE = "fixture"
    SANDBOX = "sandbox"
    LIVE = "live"


class DisplayMode(str, Enum):
    EMULATOR = "emulator"
    HARDWARE = "hardware"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    oura_client_id: str = ""
    oura_client_secret: str = ""
    oura_redirect_uri: str = "http://localhost:8080/callback"

    ouri_data_source: DataSource = DataSource.FIXTURE
    ouri_display: DisplayMode = DisplayMode.EMULATOR
    ouri_fixture: str = ""

    display_width: int = 128
    display_height: int = 64
    display_scale: int = 4
    fps: int = 12


def load_thresholds() -> dict:
    path = CONFIG_DIR / "thresholds.yaml"
    with path.open() as f:
        return yaml.safe_load(f)


def load_schedule() -> dict:
    path = CONFIG_DIR / "schedule.yaml"
    with path.open() as f:
        return yaml.safe_load(f)


settings = Settings()

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

APP_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = APP_ROOT.parent

load_dotenv(APP_ROOT / ".env")
load_dotenv()


def default_data_root() -> Path:
    if (APP_ROOT / "books").exists():
        return APP_ROOT
    if (PROJECT_ROOT / "books").exists():
        return PROJECT_ROOT
    return APP_ROOT


def load_config(path: str | Path | None = None) -> dict:
    config_path = Path(path) if path else Path(__file__).with_name("config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    def expand(obj):
        if isinstance(obj, str):
            if "${COACHING_DATA_DIR}" in obj and not os.getenv("COACHING_DATA_DIR"):
                obj = obj.replace("${COACHING_DATA_DIR}", str(default_data_root()))
            return os.path.expandvars(obj)
        if isinstance(obj, dict):
            return {k: expand(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [expand(i) for i in obj]
        return obj

    return expand(raw)


CONFIG = load_config()
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")

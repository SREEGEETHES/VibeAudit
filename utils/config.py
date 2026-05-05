import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".vibeaudit"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "provider": "ollama",
    "api_key": "",
    "ollama_model": "llama3",
    "ollama_url": "http://localhost:11434",
    "kimi_model": "moonshot-v1-32k",
    "openai_model": "gpt-4o",
    "anthropic_model": "claude-3-5-sonnet-20241022",
    "minimax_model": "abab6.5-chat",
    "max_file_size_kb": 500,
    "auto_save_reports": False,
    "reports_dir": str(Path.home() / "VibeAuditReports"),
    "obsidian_path": ""
}

def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r") as f:
            saved = json.load(f)
        config = DEFAULT_CONFIG.copy()
        config.update(saved)
        return config
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
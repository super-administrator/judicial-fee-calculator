"""
settings.py
用户配置读写。配置文件保存在程序外部，适配 PyInstaller 单文件打包场景。
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict


DEFAULT_FEE_BASES = {
    "divorce_base": 200.0,
    "personality_base": 100.0,
}


def get_config_path() -> Path:
    custom_path = os.environ.get("JUDICIAL_FEE_CONFIG_PATH")
    if custom_path:
        return Path(custom_path).expanduser()

    if getattr(sys, "frozen", False) and sys.platform.startswith("linux"):
        return Path(sys.executable).resolve().parent / "config.json"

    app_name = "司法速算器"

    if sys.platform == "darwin":
        config_dir = Path.home() / "Library" / "Application Support" / app_name
    elif sys.platform.startswith("win"):
        root = os.environ.get("APPDATA")
        config_dir = Path(root) / app_name if root else Path.home() / app_name
    else:
        root = os.environ.get("XDG_CONFIG_HOME")
        config_dir = Path(root) / app_name if root else Path.home() / ".config" / app_name

    return config_dir / "config.json"


def fee_config_exists() -> bool:
    return get_config_path().exists()


def load_fee_bases() -> Dict[str, float]:
    config_path = get_config_path()
    values = DEFAULT_FEE_BASES.copy()

    try:
        with config_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return values

    if not isinstance(data, dict):
        return values

    for key, default_value in DEFAULT_FEE_BASES.items():
        try:
            value = float(data.get(key, default_value))
        except (TypeError, ValueError):
            continue
        if value >= 0:
            values[key] = value

    return values


def save_fee_bases(values: Dict[str, float]) -> Path:
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    data = DEFAULT_FEE_BASES.copy()
    data.update(values)

    with config_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    return config_path

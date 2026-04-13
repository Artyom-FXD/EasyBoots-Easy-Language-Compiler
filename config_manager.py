# config_manager.py
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

class ConfigManager:
    DEFAULT_CONFIG = {
        "compiler": {
            "path": None,           # путь к исполняемому файлу компилятора
            "optimization": "hard", # none, soft, hard
            "debug": False
        }
    }

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.global_config_dir = Path.home() / ".ely"
        self.global_config_path = self.global_config_dir / "config.json"
        self.local_config_path = self.project_root / ".ely_config"

    def _load_file(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_file(self, path: Path, data: Dict[str, Any]):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def get_global_config(self) -> Dict[str, Any]:
        return self._load_file(self.global_config_path)

    def get_local_config(self) -> Dict[str, Any]:
        return self._load_file(self.local_config_path)

    def get_merged_config(self) -> Dict[str, Any]:
        """Объединяет глобальный и локальный конфиги (локальный приоритетнее)."""
        global_cfg = self.get_global_config()
        local_cfg = self.get_local_config()
        merged = {}
        # Рекурсивное слияние словарей
        def merge_dict(base: dict, override: dict) -> dict:
            result = base.copy()
            for k, v in override.items():
                if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                    result[k] = merge_dict(result[k], v)
                else:
                    result[k] = v
            return result
        merged = merge_dict(global_cfg, local_cfg)
        # Применяем значения по умолчанию
        return merge_dict(self.DEFAULT_CONFIG.copy(), merged)

    def set_global(self, key: str, value: Any):
        cfg = self.get_global_config()
        parts = key.split('.')
        current = cfg
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
        self._save_file(self.global_config_path, cfg)

    def set_local(self, key: str, value: Any):
        cfg = self.get_local_config()
        parts = key.split('.')
        current = cfg
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
        self._save_file(self.local_config_path, cfg)

    def reset_global(self):
        if self.global_config_path.exists():
            self.global_config_path.unlink()

    def reset_local(self):
        if self.local_config_path.exists():
            self.local_config_path.unlink()
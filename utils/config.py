from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_PROMPT = """
请对图片中的女性人物进行写实风格的人像美颜修图，将其优化为成年女性的抖音网红自拍风格。
要求保留原人物身份、基本五官比例、脸型特征、发型、表情、姿态、服装、拍摄角度和画面构图。
不要换脸，不要生成另一个人，只在原图基础上进行自然、精致、真实的美颜增强。

整体风格：抖音网红感、白皙奶油肌、小V脸、精致五官、大眼卧蚕、清透底妆、甜美清纯、柔光滤镜、自拍美颜相机质感、干净明亮、柔和自然，保持成年女性气质。

严格限制：不要换脸，不要改变人物年龄为未成年人，不要过度磨皮，不要生成暴露、性感、挑逗、暧昧或低俗效果。
本图像编辑请求仅用于普通人像美颜、肤色优化、五官精修和背景人物虚化。
""".strip()


DEFAULT_CONFIG: dict[str, Any] = {
    "image_root_dir": r"G:\cannon\2025.5.1萤火虫",
    "fixed_prompt": DEFAULT_PROMPT,
    "chrome": {
        "version_main": 147,
        "profile_dir": "config/test_profile",
        "driver_exe_path": r"C:\Users\Administrator\AppData\Roaming\undetected_chromedriver\undetected_chromedriver.exe",
    },
    "output": {
        "root_dir": "output/images",
        "result_json_path": None,
        "image_location": "source",
    },
    "task": {
        "skip_policy_failed": True,
    },
    "human_like_interaction": {
        "enabled": True,
        "before_new_chat_ms": [1500, 4000],
        "before_upload_ms": [1200, 3500],
        "after_upload_ms": [2000, 5000],
        "before_prompt_input_ms": [800, 2200],
        "before_send_ms": [1500, 4000],
        "after_send_ms": [1000, 2500],
        "before_wait_response_ms": [800, 1800],
        "before_download_ms": [1000, 3000],
        "after_rename_ms": [1000, 3000],
        "between_tasks_ms": [5000, 15000],
        "retry_backoff_ms": [2000, 6000],
    },
}


def read_json(path: Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def merge_with_defaults(current: Any, default: Any) -> Any:
    if isinstance(default, dict) and not isinstance(current, dict):
        return deepcopy(default)
    if isinstance(current, dict) and isinstance(default, dict):
        merged: dict[str, Any] = {}
        for key, default_value in default.items():
            if key in current:
                merged[key] = merge_with_defaults(current[key], default_value)
            else:
                merged[key] = deepcopy(default_value)
        return merged
    return current


@dataclass
class ConfigSet:
    config_dir: Path = Path("config")
    config_name: str = "config.json"

    def __post_init__(self) -> None:
        self.config_dir = Path(self.config_dir)
        self.config_path = self.config_dir / self.config_name
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.ensure_file()
        self.config: dict[str, Any] = {}
        self.reload()

    def ensure_file(self) -> None:
        if not self.config_path.exists():
            write_json(self.config_path, DEFAULT_CONFIG)
            return

        try:
            current = read_json(self.config_path)
            write_json(self.config_path, merge_with_defaults(current, DEFAULT_CONFIG))
        except Exception:
            write_json(self.config_path, deepcopy(DEFAULT_CONFIG))

    def reload(self) -> None:
        self.config = read_json(self.config_path)

    def get(self, key: str, default: Any = None) -> Any:
        self.reload()
        value: Any = self.config
        for part in key.split("."):
            if not isinstance(value, dict) or part not in value:
                return default
            value = value[part]
        return value

    def set(self, key: str, value: Any) -> None:
        self.reload()
        target = self.config
        parts = key.split(".")
        for part in parts[:-1]:
            next_value = target.setdefault(part, {})
            if not isinstance(next_value, dict):
                next_value = {}
                target[part] = next_value
            target = next_value
        target[parts[-1]] = value
        self.save()

    def save(self) -> None:
        write_json(self.config_path, merge_with_defaults(self.config, DEFAULT_CONFIG))


def check_config(config_dir: Path = Path("config"), config_name: str = "config.json") -> ConfigSet:
    return ConfigSet(config_dir=config_dir, config_name=config_name)


def optional_path(value: str | None) -> Path | None:
    return Path(value) if value else None


config = check_config()

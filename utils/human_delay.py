from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any

from utils.logger import logger


DEFAULT_DELAY_RANGES: dict[str, tuple[int, int]] = {
    "before_new_chat": (1500, 4000),
    "before_upload": (1200, 3500),
    "after_upload": (2000, 5000),
    "before_prompt_input": (800, 2200),
    "before_send": (1500, 4000),
    "after_send": (1000, 2500),
    "before_wait_response": (800, 1800),
    "before_download": (1000, 3000),
    "after_rename": (1000, 3000),
    "between_tasks": (5000, 15000),
    "retry_backoff": (2000, 6000),
}


def parse_ms_range(value: Any, default: tuple[int, int]) -> tuple[int, int]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return default

    try:
        low = int(value[0])
        high = int(value[1])
    except (TypeError, ValueError):
        return default

    low = max(0, low)
    high = max(0, high)

    if low > high:
        low, high = high, low

    return low, high


@dataclass
class HumanDelay:
    enabled: bool = True
    ranges: dict[str, tuple[int, int]] = field(
        default_factory=lambda: DEFAULT_DELAY_RANGES.copy()
    )

    @classmethod
    def from_config(cls, config_set) -> "HumanDelay":
        enabled = bool(config_set.get("human_like_interaction.enabled", True))
        ranges: dict[str, tuple[int, int]] = {}

        for step_name, default_range in DEFAULT_DELAY_RANGES.items():
            raw_value = config_set.get(
                f"human_like_interaction.{step_name}_ms",
                list(default_range),
            )
            ranges[step_name] = parse_ms_range(raw_value, default_range)

        return cls(enabled=enabled, ranges=ranges)

    def sleep(self, step_name: str, reason: str = "") -> int:
        if not self.enabled:
            return 0

        delay_range = self.ranges.get(step_name)
        if delay_range is None:
            logger.warning(f"Unknown delay step: {step_name}")
            return 0

        low, high = delay_range
        if high <= 0:
            return 0

        delay_ms = random.randint(low, high)
        message = f"Delay {delay_ms}ms {step_name}"
        if reason:
            message = f"{message}: {reason}"
        logger.info(message)
        time.sleep(delay_ms / 1000)
        return delay_ms

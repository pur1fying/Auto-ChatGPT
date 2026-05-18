import re
from datetime import datetime
from typing import Any, Dict, Optional


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def get_page_text(driver) -> str:
    try:
        return driver.find_element("tag name", "body").text
    except Exception:
        return ""


def detect_policy_failed(page_text: str) -> Optional[str]:
    normalized = page_text.lower().replace("’", "'")

    patterns = [
        "we're so sorry, but the image we created may violate our content policies",
        "may violate our content policies",
        "content policies",
    ]

    for pattern in patterns:
        if pattern in normalized:
            return pattern

    return None


def detect_limit_reached(page_text: str) -> Optional[Dict[str, Any]]:
    text = page_text.replace("’", "'")
    normalized = text.lower()

    limit_keywords = [
        "hit the plus plan limit",
        "limit for image generations",
        "image generations requests",
        "create more images when the limit resets",
        "limit resets in",
    ]

    if not any(keyword in normalized for keyword in limit_keywords):
        return None

    reset_after_text = None

    match = re.search(
        r"limit resets in\s+([^.\n\r]+)",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        reset_after_text = match.group(1).strip()

    reset_after_minutes = parse_reset_after_minutes(reset_after_text)

    return {
        "raw_message": extract_limit_message(text),
        "reset_after_text": reset_after_text,
        "reset_after_minutes": reset_after_minutes,
        "detected_at": now_iso(),
    }


def detect_request_too_frequent(page_text: str) -> Optional[Dict[str, Any]]:
    text = page_text
    normalized = text.lower()

    rate_limit_keywords = [
        "\u8bf7\u6c42\u8fc7\u4e8e\u9891\u7e41",
        "\u4f60\u7684\u8bf7\u6c42\u8fc7\u4e8e\u9891\u7e41",
        "\u6682\u65f6\u9650\u5236\u4f60\u8bbf\u95ee\u5bf9\u8bdd\u8bb0\u5f55",
        "\u8bf7\u7a0d\u7b49\u51e0\u5206\u949f\u540e\u518d\u91cd\u8bd5",
        "too frequent",
        "too many requests",
    ]

    if not any(keyword in normalized for keyword in rate_limit_keywords):
        return None

    return {
        "raw_message": extract_rate_limit_message(text),
        "detected_at": now_iso(),
    }


def parse_reset_after_minutes(reset_after_text: Optional[str]) -> Optional[int]:
    if not reset_after_text:
        return None

    hours = 0
    minutes = 0

    h_match = re.search(
        r"(\d+)\s*hour",
        reset_after_text,
        flags=re.IGNORECASE,
    )
    m_match = re.search(
        r"(\d+)\s*minute",
        reset_after_text,
        flags=re.IGNORECASE,
    )

    if h_match:
        hours = int(h_match.group(1))

    if m_match:
        minutes = int(m_match.group(1))

    return hours * 60 + minutes


def extract_limit_message(text: str) -> str:
    normalized = " ".join(text.split())
    lower_text = normalized.lower()

    candidates = [
        "you've hit",
        "hit the plus plan limit",
        "limit for image generations",
    ]

    start_idx = -1
    for candidate in candidates:
        start_idx = lower_text.find(candidate)
        if start_idx >= 0:
            break

    if start_idx < 0:
        return normalized[:600]

    end_idx = min(len(normalized), start_idx + 600)
    return normalized[start_idx:end_idx]


def extract_rate_limit_message(text: str) -> str:
    normalized = " ".join(text.split())
    lower_text = normalized.lower()

    candidates = [
        "\u8bf7\u6c42\u8fc7\u4e8e\u9891\u7e41",
        "\u4f60\u7684\u8bf7\u6c42\u8fc7\u4e8e\u9891\u7e41",
        "too frequent",
        "too many requests",
    ]

    start_idx = -1
    for candidate in candidates:
        start_idx = lower_text.find(candidate)
        if start_idx >= 0:
            break

    if start_idx < 0:
        return normalized[:600]

    end_idx = min(len(normalized), start_idx + 600)
    return normalized[start_idx:end_idx]

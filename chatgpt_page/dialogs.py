from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException

from utils.Exception import AutoChatGPTInternalError
from utils.logger import logger
from utils.selenium_utils import safe_click, visible_elements


class RequestTooFrequentError(AutoChatGPTInternalError):
    """Raised when ChatGPT shows the request-too-frequent safety dialog."""


BLOCKING_DIALOG_SELECTORS = [
    'div[data-state="open"].fixed.inset-0',
    '[role="dialog"][data-state="open"]',
    '[data-radix-dialog-content][data-state="open"]',
]

DIALOG_CLOSE_BUTTON_SELECTORS = [
    '[role="dialog"][data-state="open"] button[aria-label*="Close" i]',
    '[role="dialog"][data-state="open"] button[aria-label*="关闭" i]',
    '[role="dialog"][data-state="open"] button[aria-label*="取消" i]',
    '[role="dialog"][data-state="open"] button[aria-label*="Cancel" i]',
    '[data-radix-dialog-content][data-state="open"] button[aria-label*="Close" i]',
    '[data-radix-dialog-content][data-state="open"] button[aria-label*="关闭" i]',
    '[data-radix-dialog-content][data-state="open"] button[aria-label*="取消" i]',
    '[data-radix-dialog-content][data-state="open"] button[aria-label*="Cancel" i]',
]

DIALOG_CLOSE_BUTTON_TEXTS = {
    "close",
    "cancel",
    "not now",
    "got it",
    "ok",
    "关闭",
    "取消",
    "知道了",
    "稍后",
    "明白了",
}

REQUEST_TOO_FREQUENT_DIALOG_TEXTS = (
    "\u8bf7\u6c42\u8fc7\u4e8e\u9891\u7e41",
    "\u4f60\u7684\u8bf7\u6c42\u8fc7\u4e8e\u9891\u7e41",
    "\u6682\u65f6\u9650\u5236\u4f60\u8bbf\u95ee\u5bf9\u8bdd\u8bb0\u5f55",
    "\u8bf7\u7a0d\u7b49\u51e0\u5206\u949f\u540e\u518d\u91cd\u8bd5",
    "too frequent",
    "too many requests",
)


def get_visible_dialogs(driver):
    return visible_elements(driver, BLOCKING_DIALOG_SELECTORS)


def has_blocking_dialog(driver):
    return bool(get_visible_dialogs(driver))


def is_request_too_frequent_dialog(dialog) -> bool:
    try:
        text = (dialog.text or "").strip().lower()
    except Exception:
        return False

    return any(pattern in text for pattern in REQUEST_TOO_FREQUENT_DIALOG_TEXTS)


def detect_request_too_frequent_dialog(driver):
    for dialog in get_visible_dialogs(driver):
        if is_request_too_frequent_dialog(dialog):
            return dialog
    return None


def raise_if_request_too_frequent(driver):
    dialog = detect_request_too_frequent_dialog(driver)
    if dialog is not None:
        raise RequestTooFrequentError(
            "Request too frequent dialog is visible; stop batch instead of dismissing it."
        )


def wait_blocking_dialog_closed(driver, timeout=2):
    try:
        WebDriverWait(driver, timeout, poll_frequency=0.2).until(
            lambda d: not has_blocking_dialog(d)
        )
        return True
    except TimeoutException:
        return False


def _send_escape(driver):
    try:
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        return True
    except WebDriverException:
        try:
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            return True
        except Exception:
            return False


def _click_dialog_close_button(driver):
    for selector in DIALOG_CLOSE_BUTTON_SELECTORS:
        for button in visible_elements(driver, selector):
            try:
                if button.is_enabled():
                    safe_click(button, driver=driver)
                    return True
            except Exception:
                continue

    for dialog in get_visible_dialogs(driver):
        try:
            buttons = dialog.find_elements(By.CSS_SELECTOR, "button")
        except Exception:
            continue

        for button in buttons:
            try:
                label = (button.get_attribute("aria-label") or "").strip().lower()
                text = (button.text or "").strip().lower()
                if not button.is_displayed() or not button.is_enabled():
                    continue
                if label in DIALOG_CLOSE_BUTTON_TEXTS or text in DIALOG_CLOSE_BUTTON_TEXTS:
                    safe_click(button, driver=driver)
                    return True
            except Exception:
                continue

    return False


def dismiss_blocking_dialog_if_present(driver, timeout=3):
    dialogs = get_visible_dialogs(driver)
    if not dialogs:
        return False

    raise_if_request_too_frequent(driver)

    logger.warning("Blocking ChatGPT dialog/overlay detected; attempting to dismiss it.")

    if _send_escape(driver) and wait_blocking_dialog_closed(driver, timeout=timeout):
        logger.info("Blocking dialog dismissed with Escape.")
        return True

    if _click_dialog_close_button(driver) and wait_blocking_dialog_closed(driver, timeout=timeout):
        logger.info("Blocking dialog dismissed with close/cancel button.")
        return True

    raise AutoChatGPTInternalError(
        "Blocking ChatGPT dialog/overlay is still visible and could not be dismissed."
    )

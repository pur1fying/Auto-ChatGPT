import time
from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    TimeoutException,
    WebDriverException,
)

from utils.Exception import AutoChatGPTInternalError
from utils.selenium_utils import wait_clickable, wait_first_present, get_element_text
from utils.logger import logger
from chatgpt_page.common import get_composer_root, get_prompt_input_selectors
from chatgpt_page.response import get_chat_turn_cnts


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
}

REQUEST_TOO_FREQUENT_DIALOG_TEXTS = (
    "请求过于频繁",
    "你的请求过于频繁",
    "暂时限制你访问对话记录",
    "请稍等几分钟后再重试",
    "too frequent",
)


def _sleep_delay(delay, step_name, reason=""):
    if delay is not None:
        delay.sleep(step_name, reason)


def get_prompt_input(driver, timeout=3):
    return wait_clickable(
        driver,
        get_prompt_input_selectors(),
        timeout=timeout
    )[0]


def _visible_elements(driver, selectors):
    if isinstance(selectors, str):
        selectors = [selectors]

    visible = []
    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
        except Exception:
            continue

        for element in elements:
            try:
                if element.is_displayed():
                    visible.append(element)
            except Exception:
                continue

    return visible


def get_visible_blocking_dialogs(driver):
    return _visible_elements(driver, BLOCKING_DIALOG_SELECTORS)


def has_blocking_dialog(driver):
    return len(get_visible_blocking_dialogs(driver)) > 0


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
        for button in _visible_elements(driver, selector):
            try:
                if button.is_enabled():
                    button.click()
                    return True
            except Exception:
                try:
                    driver.execute_script("arguments[0].click();", button)
                    return True
                except Exception:
                    continue

    for dialog in get_visible_blocking_dialogs(driver):
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
                    button.click()
                    return True
            except Exception:
                try:
                    driver.execute_script("arguments[0].click();", button)
                    return True
                except Exception:
                    continue

    return False


def is_request_too_frequent_dialog(dialog) -> bool:
    try:
        text = (dialog.text or "").strip().lower()
    except Exception:
        return False

    return any(pattern in text for pattern in REQUEST_TOO_FREQUENT_DIALOG_TEXTS)


def dismiss_blocking_dialog_if_present(driver, timeout=3):
    dialogs = get_visible_blocking_dialogs(driver)
    if not dialogs:
        return False

    if any(is_request_too_frequent_dialog(dialog) for dialog in dialogs):
        raise AutoChatGPTInternalError(
            "Request too frequent dialog is visible; stop batch instead of dismissing it."
        )

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


def preprocess_prompt(prompt: str) -> str:
    """
    Replace all line breaks with spaces before send_keys.
    Avoid multi-line prompts submitted unexpectedly.
    """
    new_prompt = (
        str(prompt)
        .replace("\r\n", " ")
        .replace("\n", " ")
        .replace("\r", " ")
    )

    return " ".join(new_prompt.split())


def set_prompt_text(
    _input,
    prompt,
    check=True,
    driver=None,
    input_getter=None,
    max_attempts=3,
    delay=None,
):
    logger.info("<<< Set prompt text >>>")
    prompt = preprocess_prompt(prompt)

    logger.info(f"Text length : {len(prompt)}")

    if driver is None:
        driver = getattr(_input, "_parent", None)

    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            if driver is not None:
                dismiss_blocking_dialog_if_present(driver)

            if input_getter is not None:
                _input = input_getter()

            try:
                _input.click()
            except ElementClickInterceptedException:
                raise
            except Exception:
                if driver is None:
                    raise
                driver.execute_script("arguments[0].focus(); arguments[0].click();", _input)

            _input.clear()
            _input.send_keys(prompt)
            break

        except ElementClickInterceptedException as e:
            last_error = e
            logger.warning(
                f"Prompt input click intercepted, attempt={attempt}/{max_attempts}."
            )
            if driver is None:
                raise
            dismiss_blocking_dialog_if_present(driver)
            if attempt >= max_attempts:
                raise AutoChatGPTInternalError(
                    "Prompt input click was repeatedly intercepted by a page overlay."
                ) from e
            _sleep_delay(delay, "retry_backoff", f"set prompt text retry attempt={attempt}")
        except Exception as e:
            last_error = e
            if attempt >= max_attempts:
                raise
            logger.warning(
                f"Failed to set prompt text, attempt={attempt}/{max_attempts}, error={e}"
            )
            if delay is not None:
                _sleep_delay(delay, "retry_backoff", f"set prompt text retry attempt={attempt}")
            else:
                time.sleep(0.5)
    else:
        raise AutoChatGPTInternalError("Failed to set prompt text.") from last_error

    if check:
        logger.info("Verify Input Text.")
        text = get_element_text(_input)
        if text != prompt:
            logger.error(
                f"Input text verification failed. "
                f"Expected length={len(prompt)}, actual length={len(text)}"
            )
            raise AutoChatGPTInternalError(
                "Input Text Verification Failed: expected prompt text does not match actual text. "
                f"In: {prompt}\nOut: {text}"
            )

    return True


def get_send_button(driver, timeout=30):
    button = wait_clickable(
        driver,
        ['#composer-submit-button'],
        timeout=timeout
    )[0]
    return button


def get_uploaded_image_count(driver):
    composer = get_composer_root(driver)
    if composer is None:
        return 0
    count = 0
    imgs = composer.find_elements(
        By.CSS_SELECTOR,
        'button[aria-label*="打开图片"] img, '
        'button[aria-label*="open image" i] img, '
        'img'
    )

    for img in imgs:
        try:
            src = img.get_attribute("src") or ""
            if "backend-api/estuary/content" in src and "id=file_" in src:
                count += 1
        except:
            continue

    return count


def wait_for_file_uploaded(driver, timeout=600):
    before_cnt = get_uploaded_image_count(driver)

    logger.info(f"Before Image Cnt : {before_cnt}")

    wait = WebDriverWait(driver, timeout)

    def _uploaded(d):
        composer = get_composer_root(d)

        if composer is None:
            return False

        imgs = composer.find_elements(
            By.CSS_SELECTOR,
            'button[aria-label*="打开图片"] img, '
            'button[aria-label*="open image" i] img, '
            'img'
        )
        has_blob_preview = False
        now_count = 0
        for img in imgs:
            try:
                if not img.is_displayed():
                    continue
                src = img.get_attribute("src") or ""
                if src.startswith("blob:"):
                    has_blob_preview = True
                    continue
                if "backend-api/estuary/content" in src and "id=file_" in src:
                    now_count += 1
            except Exception:
                continue
        if now_count > before_cnt and not has_blob_preview:
            return True
        return False
    try:
        wait.until(_uploaded)
        after_cnt = get_uploaded_image_count(driver)
        logger.info(f"After Image Cnt  : {after_cnt}")
        return True

    except TimeoutException:
        return False


def get_current_attachment_count(driver):
    composer = get_composer_root(driver)

    if composer is None:
        logger.debug("Composer root not found while counting attachments")
        return 0

    count = len(composer.find_elements(By.CSS_SELECTOR, 'img'))

    count += len(
        composer.find_elements(
            By.CSS_SELECTOR,
            '[data-testid*="attachment"], '
            'button[aria-label*="Remove" i], '
            'button[aria-label*="移除" i], '
            'button[aria-label*="删除" i]'
        )
    )

    logger.debug(f"Current attachment count: {count}")
    return count


def upload_image(driver, image_path):
    if not image_path:
        return False

    image_path = Path(image_path)

    if not image_path.exists():
        return False

    logger.info("<<< Set File Image >>>")
    logger.info(f"Image : {image_path.name}")
    file_input = wait_first_present(
        driver,
        [
            'input[type="file"]',
            'form input[type="file"]',
            'main input[type="file"]',
        ],
        timeout=20
    )

    file_input.send_keys(str(image_path.resolve()))
    ret =  wait_for_file_uploaded(driver)

    if ret:
        logger.info(f"Image uploaded successfully: {image_path.name}")
    else:
        logger.warning(f"Failed to upload Image")
    return ret


def set_prompt_and_image(driver, prompt, image_path=None, delay=None):
    """
    Set prompt and optionally upload an image
    """
    logger.info("<<< Send Prompt And Image >>>")

    logger.info("Preparing composer input")
    get_prompt_input(driver, timeout=30)

    if image_path:
        _sleep_delay(delay, "before_upload", "upload image")
        upload_image(driver, image_path)
        _sleep_delay(delay, "after_upload", "wait after image upload")
    else:
        logger.info("No image attached for this prompt")

    _sleep_delay(delay, "before_prompt_input", "set prompt text")
    set_prompt_text(
        get_prompt_input(driver, timeout=30),
        prompt,
        driver=driver,
        input_getter=lambda: get_prompt_input(driver, timeout=30),
        delay=delay,
    )
    return True


def send_message(
    driver,
    snapshot,
    timeout=60,
    retry_interval=5,
    delay=None,
):
    logger.info("<<< Send Message >>>")

    def _user_turn_added(d):
        current = get_chat_turn_cnts(d)
        return current["user"] > snapshot["user"]

    end_time = time.time() + timeout
    click_count = 0

    while time.time() < end_time:
        click_count += 1

        try:
            _sleep_delay(delay, "before_send", f"send message attempt={click_count}")
            send_btn = get_send_button(driver, timeout=10)
            send_btn.click()
            logger.info(f"Clicked send button, attempt={click_count}")
            _sleep_delay(delay, "after_send", f"send message attempt={click_count}")
        except Exception as e:
            logger.warning(f"Failed to click send button, attempt={click_count}, error={e}")

        remaining = max(1, int(end_time - time.time()))
        wait_timeout = min(retry_interval, remaining)

        try:
            WebDriverWait(driver, wait_timeout).until(_user_turn_added)

            current = get_chat_turn_cnts(driver)
            logger.info(
                f"User message appeared. user={snapshot['user']} -> {current['user']}"
            )
            return True

        except TimeoutException:
            logger.warning(
                f"User message not detected after click, retrying... attempt={click_count}"
            )
            _sleep_delay(delay, "retry_backoff", f"send retry attempt={click_count}")

    logger.warning(f"Timeout while waiting user message after sending, timeout={timeout}s")
    return False

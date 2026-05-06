from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

from utils.selenium_utils import wait_clickable, wait_first_present, get_element_text
from .common import get_composer_root, get_prompt_input_selectors


def get_prompt_input(driver, timeout=30):
    return wait_clickable(
        driver,
        get_prompt_input_selectors(),
        timeout=timeout
    )[0]

def preprocess_prompt(prompt: str) -> str:
    """
        Replace all line breaks with spaces before send_keys.
        This avoids multi-line prompts being treated as Enter/submit by the page.
    """
    _old = str(prompt)

    newline_count = (
        _old.count("\r\n")
        + _old.count("\n")
        + _old.count("\r")
    )

    _new = (
        _old
        .replace("\r\n", " ")
        .replace("\n", " ")
        .replace("\r", " ")
    )

    # Optional: collapse repeated spaces caused by blank lines.
    _new = " ".join(_new.split())

    if newline_count > 0:
        print(
            f"Prompt normalize: replaced {newline_count} newline(s) with spaces "
            f"before send_keys. length {len(_old)} -> {len(_new)}"
        )
    else:
        print("Prompt normalize: no newline found before send_keys")

    return _new

def set_prompt_text(_input, prompt, check=True):
    prompt = preprocess_prompt(prompt)
    _input.click()
    _input.clear()
    _input.send_keys(prompt)
    if check:
        text = get_element_text(_input)
        if text != prompt:
            raise ValueError(f"Input Text Verification Failed: expected prompt text does not match actual text. In : {prompt} \n Out: {text}")
    return True

def get_send_button(driver, timeout=30):
    return wait_clickable(
        driver,
        ['#composer-submit-button'],
        timeout=timeout
    )[0]

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
        except Exception:
            continue

    return count

def wait_for_file_uploaded(driver, timeout=180):
    _before_cnt = get_uploaded_image_count(driver)
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
        _now_cnt = 0
        for img in imgs:
            try:
                if not img.is_displayed():
                    continue
                src = img.get_attribute("src") or ""
                if src.startswith("blob:"):
                    has_blob_preview = True
                    continue
                if "backend-api/estuary/content" in src and "id=file_" in src:
                    _now_cnt += 1
            except Exception:
                continue
        if _now_cnt > _before_cnt and not has_blob_preview:
            return True
        return False
    try:
        wait.until(_uploaded)
        print("Image upload complete")
    except TimeoutException:
        print("Warning: timeout while waiting for image upload complete")


def get_current_attachment_count(driver):
    composer = get_composer_root(driver)

    if composer is None:
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

    return count


def upload_image_needed(driver, image_path):
    if not image_path:
        return

    image_path = Path(image_path)

    if not image_path.exists():
        print(f"Warning: image not found: {image_path}")
        return

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
    wait_for_file_uploaded(driver)


def send_prompt_and_image(driver, prompt, image_path=None):
    """Type the prompt and optionally upload an image, then send."""
    # Locate the input box
    _input = get_prompt_input(driver, timeout=30)

    # Upload image if path is valid
    upload_image_needed(driver, image_path)

    # Enter prompt text
    set_prompt_text(_input, prompt)

    send_btn = get_send_button(driver, timeout=30)
    send_btn.click()

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait

from utils.logger import logger


def normalize_selectors(selectors):
    if isinstance(selectors, str):
        return [selectors]
    return list(selectors)


def find_all(search_context, selectors, by=By.CSS_SELECTOR):
    elements = []

    for selector in normalize_selectors(selectors):
        try:
            found = search_context.find_elements(by, selector)
        except Exception:
            continue

        try:
            elements.extend(found)
        except TypeError:
            continue

    return elements


def visible_elements(search_context, selectors, by=By.CSS_SELECTOR):
    visible = []

    for element in find_all(search_context, selectors, by=by):
        try:
            if element.is_displayed():
                visible.append(element)
        except Exception:
            continue

    return visible


def any_visible(search_context, selectors, by=By.CSS_SELECTOR) -> bool:
    return bool(visible_elements(search_context, selectors, by=by))


def is_visible(driver, selector: str) -> bool:
    return any_visible(driver, selector)


def wait_visible(driver, selectors, timeout=20, by=By.CSS_SELECTOR):
    wait = WebDriverWait(driver, timeout)

    def _find_visible(d):
        elements = visible_elements(d, selectors, by=by)
        if elements:
            return elements[0]

        return False

    return wait.until(_find_visible)


def wait_first_visible(driver, selectors, timeout=20):
    return wait_visible(driver, selectors, timeout=timeout)


def wait_present(driver, selectors, timeout=20, by=By.CSS_SELECTOR):
    wait = WebDriverWait(driver, timeout)

    def _find_present(d):
        elements = find_all(d, selectors, by=by)
        if elements:
            return elements[-1]

        return False

    return wait.until(_find_present)


def wait_first_present(driver, selectors, timeout=20):
    return wait_present(driver, selectors, timeout=timeout)


def wait_clickable(driver, selectors, timeout=20):
    """
    Wait until one of the CSS selectors matches a clickable element.

    Returns:
        (element, selector_index)
    """
    selectors = normalize_selectors(selectors)

    wait = WebDriverWait(driver, timeout)

    def _find_clickable(d):
        for index, selector in enumerate(selectors):
            for element in find_all(d, selector):
                try:
                    if element.is_displayed() and element.is_enabled():
                        return element, index
                except:
                    continue
        return False

    return wait.until(_find_clickable)


def safe_click(element, driver=None, scroll=True, js_fallback=True):
    if driver is None:
        driver = getattr(element, "_parent", None)

    if scroll and driver is not None:
        try:
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});",
                element,
            )
        except Exception:
            pass

    try:
        element.click()
        return True
    except Exception:
        if not js_fallback or driver is None:
            raise

    driver.execute_script("arguments[0].click();", element)
    return True


def click_by_text(
    driver,
    texts,
    *,
    selectors='[role="menuitem"], [cmdk-item], button, div[role="option"]',
    timeout=10,
    by=By.CSS_SELECTOR,
):
    texts = [text.lower() for text in normalize_selectors(texts)]
    wait = WebDriverWait(driver, timeout)

    def _click_item(d):
        for item in find_all(d, selectors, by=by):
            try:
                text = item.text.strip()
                aria = item.get_attribute("aria-label") or ""
                combined = f"{text} {aria}"

                for target in texts:
                    if target in combined.lower():
                        if item.is_displayed() and item.is_enabled():
                            safe_click(item, driver=d)
                            return True
            except Exception:
                continue

        return False

    return wait.until(_click_item)


def click_menu_item_by_text(driver, texts, timeout=10):
    return click_by_text(driver, texts, timeout=timeout)


import setuptools  # noqa: F401 - provides distutils compatibility for undetected_chromedriver on Python 3.12+
import undetected_chromedriver as uc


def create_driver(
        profile_dir,
        version_main: int = 147,
        driver_exe_path = None,
        script_timeout: int = 120,
):
    logger.info("<<< Create Driver >>>")
    logger.info(f"Profile Dir: {profile_dir}")
    logger.info(f"Chrome Ver : {version_main}")
    logger.info(f"Driver exe : {driver_exe_path}")
    logger.info(f"Script Timeout: {script_timeout}s")

    options = uc.ChromeOptions()

    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-popup-blocking")

    driver = uc.Chrome(
        version_main=version_main,
        options=options,
        driver_executable_path=driver_exe_path
    )
    driver.set_script_timeout(script_timeout)

    return driver


def get_element_text(element):
    assert isinstance(element, WebElement)
    tag_name = element.tag_name.lower()
    if tag_name in ('input', 'textarea'):
        return element.get_attribute('value') or ''
    else:
        return element.text or ''

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait


def is_visible(driver, selector: str) -> bool:
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)

        for element in elements:
            try:
                if element.is_displayed():
                    return True
            except Exception:
                continue

        return False
    except Exception:
        return False


def wait_first_visible(driver, selectors, timeout=20):
    wait = WebDriverWait(driver, timeout)

    def _find_visible(d):
        for selector in selectors:
            try:
                elements = d.find_elements(By.CSS_SELECTOR, selector)
            except Exception:
                continue

            for element in elements:
                try:
                    if element.is_displayed():
                        return element
                except Exception:
                    continue

        return False

    return wait.until(_find_visible)


def wait_first_present(driver, selectors, timeout=20):
    wait = WebDriverWait(driver, timeout)

    def _find_present(d):
        for selector in selectors:
            try:
                elements = d.find_elements(By.CSS_SELECTOR, selector)
            except Exception:
                continue

            if elements:
                return elements[-1]

        return False

    return wait.until(_find_present)


from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


def wait_clickable(driver, selectors, timeout=20):
    """
    Wait until one of the CSS selectors matches a clickable element.

    Returns:
        (element, selector_index)
    """
    if isinstance(selectors, str):
        selectors = [selectors]

    wait = WebDriverWait(driver, timeout)

    def _find_clickable(d):
        for index, selector in enumerate(selectors):
            try:
                elements = d.find_elements(By.CSS_SELECTOR, selector)
            except:
                continue

            for element in elements:
                try:
                    if element.is_displayed() and element.is_enabled():
                        return element, index
                except:
                    continue
        return False

    return wait.until(_find_clickable)


def click_menu_item_by_text(driver, texts, timeout=10):
    wait = WebDriverWait(driver, timeout)

    def _click_item(d):
        menu_items = d.find_elements(
            By.CSS_SELECTOR,
            '[role="menuitem"], [cmdk-item], button, div[role="option"]'
        )

        for item in menu_items:
            try:
                text = item.text.strip()
                aria = item.get_attribute("aria-label") or ""
                combined = f"{text} {aria}"

                for target in texts:
                    if target.lower() in combined.lower():
                        if item.is_displayed() and item.is_enabled():
                            item.click()
                            return True
            except Exception:
                continue

        return False

    return wait.until(_click_item)

import undetected_chromedriver as uc


def create_driver(profile_dir, version_main: int = 147):
    options = uc.ChromeOptions()

    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-popup-blocking")

    driver = uc.Chrome(
        version_main=version_main,
        options=options,
        driver_executable_path="C:\\Users\\Administrator\\AppData\\Roaming\\undetected_chromedriver\\undetected_chromedriver.exe"
    )

    return driver


def get_element_text(element):
    assert isinstance(element, WebElement)
    tag_name = element.tag_name.lower()
    if tag_name in ('input', 'textarea'):
        return element.get_attribute('value') or ''
    else:
        return element.text or ''

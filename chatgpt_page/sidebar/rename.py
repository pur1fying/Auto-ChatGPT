import time

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
from selenium.webdriver.support.ui import WebDriverWait

from utils.path_utils import safe_filename


def get_current_chat_id(driver):
    """
    Get current chat id from current URL.
    Example:
        https://chatgpt.com/c/xxxx
        -> xxxx
    """
    url = driver.current_url

    if "/c/" not in url:
        return ""

    return url.split("/c/", 1)[1].split("?", 1)[0].split("#", 1)[0].strip("/")


def get_active_sidebar_chat_item(driver, timeout=30):
    """
    Get active conversation item from sidebar history.

    Based on current ChatGPT sidebar HTML:
        <a data-active="" data-sidebar-item="true" href="/c/...">
    """
    wait = WebDriverWait(driver, timeout)

    selectors = [
        '#history a[data-sidebar-item="true"][data-active]',
        'a[data-sidebar-item="true"][data-active]',
    ]

    def _find_item(d):
        for selector in selectors:
            try:
                items = d.find_elements(By.CSS_SELECTOR, selector)

                for item in items:
                    try:
                        if item.is_displayed():
                            return item
                    except Exception:
                        continue
            except Exception:
                continue

        return False

    return wait.until(_find_item)


def get_sidebar_chat_item_by_url(driver, timeout=30):
    """
    Fallback: get current sidebar item by current chat id in URL.
    """
    chat_id = get_current_chat_id(driver)

    if not chat_id:
        raise RuntimeError("Current URL does not contain chat id")

    selector = f'#history a[data-sidebar-item="true"][href*="/c/{chat_id}"]'

    wait = WebDriverWait(driver, timeout)

    def _find_item(d):
        items = d.find_elements(By.CSS_SELECTOR, selector)

        for item in items:
            try:
                if item.is_displayed():
                    return item
            except Exception:
                continue

        return False

    return wait.until(_find_item)


def get_current_sidebar_chat_item(driver, timeout=30):
    """
    Prefer active sidebar item, fallback to URL matching.
    """
    try:
        return get_active_sidebar_chat_item(driver, timeout=timeout)
    except Exception:
        return get_sidebar_chat_item_by_url(driver, timeout=timeout)


def get_chat_options_button(driver, chat_item, timeout=10):
    """
    Get the ... options button for the current sidebar chat item.

    Based on current HTML:
        button[data-trailing-button]
        button[data-testid="history-item-0-options"]
        button[data-conversation-options-trigger="..."]
    """
    wait = WebDriverWait(driver, timeout)

    chat_id = get_current_chat_id(driver)

    # Hover first, otherwise the trailing ... button may not be visible/clickable.
    try:
        ActionChains(driver).move_to_element(chat_item).pause(0.5).perform()
    except Exception:
        pass

    selectors_in_item = [
        'button[data-trailing-button]',
        'button[data-testid^="history-item-"][data-testid$="-options"]',
        'button[aria-label*="对话选项"]',
        'button[aria-haspopup="menu"]',
    ]

    def _find_button(d):
        # 1. Prefer button inside current active sidebar item.
        for selector in selectors_in_item:
            try:
                buttons = chat_item.find_elements(By.CSS_SELECTOR, selector)

                for btn in buttons:
                    try:
                        if btn.is_displayed() and btn.is_enabled():
                            return btn
                    except Exception:
                        continue
            except Exception:
                continue

        # 2. Fallback: search by conversation id globally.
        if chat_id:
            try:
                btn = d.find_element(
                    By.CSS_SELECTOR,
                    f'button[data-conversation-options-trigger="{chat_id}"]'
                )

                if btn.is_displayed() and btn.is_enabled():
                    return btn
            except Exception:
                pass

        return False

    return wait.until(_find_button)


def open_current_chat_options_menu(driver, timeout=30):
    """
    Hover current sidebar chat item and open its ... menu.
    """
    chat_item = get_current_sidebar_chat_item(driver, timeout=timeout)
    options_btn = get_chat_options_button(driver, chat_item, timeout=10)

    options_btn.click()

    WebDriverWait(driver, 10).until(
        lambda d: len(d.find_elements(
            By.CSS_SELECTOR,
            '[role="menu"], [data-radix-menu-content], div[data-state="open"]'
        )) > 0
    )

    return True


def click_rename_menu_item(driver, timeout=10):
    """
    Click Rename item from opened menu.
    """
    print("Clicking rename menu item...")

    wait = WebDriverWait(driver, timeout)

    xpath_list = [
        "//div[@role='menu']//div[@role='menuitem' and contains(normalize-space(.), '重命名')]",
        "//div[@role='menu']//div[@role='menuitem' and contains(normalize-space(.), 'Rename')]",
        "//*[@data-radix-menu-content]//*[@role='menuitem' and contains(normalize-space(.), '重命名')]",
        "//*[@data-radix-menu-content]//*[@role='menuitem' and contains(normalize-space(.), 'Rename')]",
    ]

    def _click(d):
        for xpath in xpath_list:
            try:
                items = d.find_elements(By.XPATH, xpath)

                for item in items:
                    if item.is_displayed() and item.is_enabled():
                        d.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});",
                            item,
                        )
                        time.sleep(0.2)

                        try:
                            item.click()
                        except Exception:
                            d.execute_script("arguments[0].click();", item)
                        print("Rename menu item clicked")
                        return True
            except Exception:
                continue

        return False

    return wait.until(_click)

def get_sidebar_rename_editor(driver, timeout=10):
    """
    Find rename editor only inside #history.

    Never return ChatGPT composer input.
    """
    wait = WebDriverWait(driver, timeout)

    selectors = [
        '#history input[name="title-editor"][aria-label="聊天标题"]',
        '#history input[name="title-editor"]',
        '#history input[aria-label="聊天标题"]',
    ]

    def _find_editor(d):
        for selector in selectors:
            try:
                elements = d.find_elements(By.CSS_SELECTOR, selector)

                for element in elements:
                    try:
                        if element.is_displayed() and element.is_enabled():
                            return element
                    except Exception:
                        continue
            except Exception:
                continue

        return False

    return wait.until(_find_editor)

def set_sidebar_rename_editor_text(driver, new_title, timeout=10):
    """
    Set title only into sidebar rename editor.
    """
    editor = get_sidebar_rename_editor(driver, timeout=timeout)

    editor.click()
    editor.send_keys(Keys.CONTROL, "a")
    editor.send_keys(new_title)
    editor.send_keys(Keys.ENTER)

    return True

def rename_current_chat(driver, new_title):
    """Rename current conversation to the relative image name."""
    print(f"Renaming chat to: {new_title}")

    new_title = safe_filename(new_title, max_len=100)

    try:
        open_current_chat_options_menu(driver, timeout=30)
        click_rename_menu_item(driver, timeout=10)
        set_sidebar_rename_editor_text(driver, new_title, timeout=10)

        if wait_chat_title_updated(driver, new_title, timeout=10):
            print("Rename confirmed")
        else:
            print("Rename attempted, but title update was not confirmed")

        return True

    except Exception as e:
        print(f"Warning: failed to rename chat: {e}")
        return False

def wait_chat_title_updated(driver, new_title, timeout=10):
    """
    Wait until active sidebar item title updates.
    """
    expected = safe_filename(new_title, max_len=100)

    try:
        WebDriverWait(driver, timeout).until(
            lambda d: expected in (
                get_active_sidebar_chat_item(d, timeout=1).get_attribute("aria-label") or ""
            )
        )
        return True
    except Exception:
        return False


def rename_current_chat(driver, new_title):
    """Rename current conversation to the relative image name."""
    print(f"Renaming chat to: {new_title}")

    new_title = safe_filename(new_title, max_len=100)

    try:
        open_current_chat_options_menu(driver, timeout=30)
        click_rename_menu_item(driver, timeout=10)
        set_sidebar_rename_editor_text(driver, new_title, timeout=10)
        if wait_chat_title_updated(driver, new_title, timeout=10):
            print("Rename confirmed")
        else:
            print("Rename attempted, but title update was not confirmed")

        return True

    except Exception as e:
        print(f"Warning: failed to rename chat: {e}")
        return False


from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from utils.logger import logger
from utils.path_utils import safe_filename
from utils.selenium_utils import find_all, safe_click, wait_clickable, wait_visible


CHAT_TITLE_LABEL = "\u804a\u5929\u6807\u9898"
RENAME_TEXT = "\u91cd\u547d\u540d"
CONVERSATION_OPTIONS_LABEL = "\u5bf9\u8bdd\u9009\u9879"


def get_current_chat_id(driver):
    url = driver.current_url

    if "/c/" not in url:
        return ""

    return url.split("/c/", 1)[1].split("?", 1)[0].split("#", 1)[0].strip("/")


def get_active_sidebar_chat_item(driver, timeout=30):
    selectors = [
        '#history a[data-sidebar-item="true"][data-active]',
        'a[data-sidebar-item="true"][data-active]',
    ]
    return wait_visible(driver, selectors, timeout=timeout)


def get_sidebar_chat_item_by_url(driver, timeout=30):
    chat_id = get_current_chat_id(driver)

    if not chat_id:
        raise RuntimeError("Current URL does not contain chat id")

    selector = f'#history a[data-sidebar-item="true"][href*="/c/{chat_id}"]'
    return wait_visible(driver, selector, timeout=timeout)


def get_current_sidebar_chat_item(driver, timeout=30):
    try:
        return get_active_sidebar_chat_item(driver, timeout=timeout)
    except Exception:
        return get_sidebar_chat_item_by_url(driver, timeout=timeout)


def get_chat_options_button(driver, chat_item, timeout=10):
    chat_id = get_current_chat_id(driver)

    try:
        ActionChains(driver).move_to_element(chat_item).pause(0.5).perform()
    except Exception:
        pass

    selectors_in_item = [
        'button[data-trailing-button]',
        'button[data-testid^="history-item-"][data-testid$="-options"]',
        f'button[aria-label*="{CONVERSATION_OPTIONS_LABEL}"]',
        'button[aria-haspopup="menu"]',
    ]

    wait = WebDriverWait(driver, timeout)

    def _find_button(d):
        for selector in selectors_in_item:
            for btn in find_all(chat_item, selector):
                try:
                    if btn.is_displayed() and btn.is_enabled():
                        return btn
                except Exception:
                    continue

        if chat_id:
            for btn in find_all(d, f'button[data-conversation-options-trigger="{chat_id}"]'):
                try:
                    if btn.is_displayed() and btn.is_enabled():
                        return btn
                except Exception:
                    continue

        return False

    return wait.until(_find_button)


def open_current_chat_options_menu(driver, timeout=30):
    chat_item = get_current_sidebar_chat_item(driver, timeout=timeout)
    options_btn = get_chat_options_button(driver, chat_item, timeout=10)

    safe_click(options_btn, driver=driver, scroll=False)

    WebDriverWait(driver, 10).until(
        lambda d: bool(find_all(
            d,
            '[role="menu"], [data-radix-menu-content], div[data-state="open"]',
        ))
    )

    return True


def click_rename_menu_item(driver, timeout=10):
    logger.info("Clicking rename menu item...")

    xpath_list = [
        f"//div[@role='menu']//div[@role='menuitem' and contains(normalize-space(.), '{RENAME_TEXT}')]",
        "//div[@role='menu']//div[@role='menuitem' and contains(normalize-space(.), 'Rename')]",
        f"//*[@data-radix-menu-content]//*[@role='menuitem' and contains(normalize-space(.), '{RENAME_TEXT}')]",
        "//*[@data-radix-menu-content]//*[@role='menuitem' and contains(normalize-space(.), 'Rename')]",
    ]

    wait = WebDriverWait(driver, timeout)

    def _click(d):
        for xpath in xpath_list:
            for item in find_all(d, xpath, by=By.XPATH):
                try:
                    if item.is_displayed() and item.is_enabled():
                        safe_click(item, driver=d)
                        logger.info("Rename menu item clicked")
                        return True
                except Exception:
                    continue

        return False

    return wait.until(_click)


def get_sidebar_rename_editor(driver, timeout=10):
    selectors = [
        f'#history input[name="title-editor"][aria-label="{CHAT_TITLE_LABEL}"]',
        '#history input[name="title-editor"]',
        f'#history input[aria-label="{CHAT_TITLE_LABEL}"]',
    ]

    return wait_clickable(driver, selectors, timeout=timeout)[0]


def set_sidebar_rename_editor_text(driver, new_title, timeout=10):
    editor = get_sidebar_rename_editor(driver, timeout=timeout)

    safe_click(editor, driver=driver, scroll=False)
    editor.send_keys(Keys.CONTROL, "a")
    editor.send_keys(new_title)
    editor.send_keys(Keys.ENTER)

    return True


def wait_chat_title_updated(driver, new_title, timeout=10):
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
    logger.info(f"Renaming chat to: {new_title}")

    new_title = safe_filename(new_title, max_len=100)

    try:
        open_current_chat_options_menu(driver, timeout=30)
        click_rename_menu_item(driver, timeout=10)
        set_sidebar_rename_editor_text(driver, new_title, timeout=10)

        if wait_chat_title_updated(driver, new_title, timeout=10):
            logger.info("Rename confirmed")
        else:
            logger.warning(f"Rename attempted, but title update was not confirmed: title={new_title}")
        return True

    except Exception as e:
        logger.warning(f"Failed to rename chat: {type(e).__name__}: {e}")
        return False

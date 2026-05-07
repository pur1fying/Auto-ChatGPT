from selenium.webdriver.common.by import By
from utils.selenium_utils import wait_first_visible


def get_sidebar_chat_items(driver):
    """
    Get all visible conversation items in the left sidebar.
    """
    selectors = [
        '#history a[data-sidebar-item="true"]',
        'nav a[data-sidebar-item="true"]',
        'aside a[data-sidebar-item="true"]',
        'a[data-sidebar-item="true"][href^="/c/"]',
        'a[data-sidebar-item="true"][href*="/c/"]',
    ]

    items = []

    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            items = [
                element for element in elements
                if element.is_displayed()
            ]

            if items:
                return items
        except Exception:
            continue

    return []


def get_sidebar_chat_count(driver):
    """
    Count visible conversation items in the left sidebar.
    """
    return len(get_sidebar_chat_items(driver))


def wait_for_sidebar_loaded(driver, timeout=30):
    """
    Wait until sidebar history items are loaded.
    """
    return wait_first_visible(
        driver,
        [
            '#history a[data-sidebar-item="true"]',
            'nav a[data-sidebar-item="true"]',
            'aside a[data-sidebar-item="true"]',
            'a[data-sidebar-item="true"][href^="/c/"]',
        ],
        timeout=timeout
    )


def get_first_sidebar_chat(driver, timeout=30):
    """
    Get the first visible conversation item in sidebar.
    """
    wait_for_sidebar_loaded(driver, timeout=timeout)

    items = get_sidebar_chat_items(driver)

    if not items:
        return None

    return items[0]


def get_sidebar_chat_title(chat_item):
    """
    Get sidebar conversation title.
    """
    try:
        title = chat_item.get_attribute("aria-label")
        if title:
            return title.replace("（未读）", "").strip()
    except Exception:
        pass

    try:
        return chat_item.text.strip()
    except Exception:
        return ""


def get_sidebar_chat_href(chat_item):
    """
    Get sidebar conversation href.
    """
    try:
        return chat_item.get_attribute("href") or ""
    except Exception:
        return ""


def get_sidebar_chat_options_button(driver, chat_item):
    """
    Get the options button inside one sidebar conversation item.
    """
    try:
        conversation_id = chat_item.get_attribute("href").rstrip("/").split("/")[-1]
    except Exception:
        conversation_id = ""

    if conversation_id:
        try:
            return driver.find_element(
                By.CSS_SELECTOR,
                f'button[data-conversation-options-trigger="{conversation_id}"]'
            )
        except Exception:
            pass

    try:
        return chat_item.find_element(
            By.CSS_SELECTOR,
            'button[data-trailing-button], button[data-testid^="history-item-"][data-testid$="-options"]'
        )
    except Exception:
        return None


def print_sidebar_chats(driver, limit=20):
    """
    Debug helper: print sidebar conversation titles.
    """
    items = get_sidebar_chat_items(driver)

    print(f"Sidebar chat count: {len(items)}")

    for idx, item in enumerate(items[:limit]):
        title = get_sidebar_chat_title(item)
        href = get_sidebar_chat_href(item)
        print(f"{idx + 1}. {title} | {href}")
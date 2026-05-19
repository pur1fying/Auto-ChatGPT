from utils.selenium_utils import safe_click, wait_clickable, wait_visible
from utils.logger import logger


def create_new_chat(driver):
    """Click the new chat button instead of navigating with driver.get."""
    logger.info("Create new chat...")

    _selector = 'a[data-testid="create-new-chat-button"]'

    btn, _ = wait_clickable(driver, _selector, timeout=30)
    is_active = btn.get_attribute("data-active") is not None
    if not is_active:
        logger.info("Change to page create new chat.")
        safe_click(btn, driver=driver, scroll=False)
        _selector_active = 'a[data-testid="create-new-chat-button"][data-active]'
        wait_visible(driver, _selector_active, timeout=20)
    else:
        logger.info("Already in page new chat.")

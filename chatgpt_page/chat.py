from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utils.selenium_utils import wait_clickable


def create_new_chat(driver):
    """Click the new chat button instead of navigating with driver.get."""
    print("Create new chat...")

    _selector = 'a[data-testid="create-new-chat-button"]'

    btn, _ = wait_clickable(driver, _selector, timeout=30)
    is_active = btn.get_attribute("data-active") is not None
    if not is_active:
        print("Change to page create new chat.")
        btn.click()
        _selector_active = 'a[data-testid="create-new-chat-button"][data-active]'
        WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, _selector_active))
        )
    else:
        print("Already in page new chat.")

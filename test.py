import time

from chatgpt_page.chat import create_new_chat
from utils.selenium_utils import create_driver, get_element_text
from utils.config import config
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys


driver = create_driver(
    profile_dir=config.get("chrome.profile_dir", "config/test_profile"),
    version_main=int(config.get("chrome.version_main", 147)),
)

driver.get("https://chatgpt.com")
create_new_chat(driver)

time.sleep(1000)

driver.quit()

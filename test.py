import time

from chatgpt_page.chat import create_new_chat
from utils.selenium_utils import create_driver, get_element_text
from config.config import SCRIPT_CHROME_PROFILE, CHROME_VERSION_MAIN, FIXED_PROMPT
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys


driver = create_driver(
    profile_dir=SCRIPT_CHROME_PROFILE,
    version_main=CHROME_VERSION_MAIN,
)

driver.get("https://chatgpt.com")
create_new_chat(driver)

time.sleep(1000)

driver.quit()
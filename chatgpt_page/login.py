from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from utils.Exception import AutoChatGPTInternalError
from utils.selenium_utils import is_visible, wait_clickable
from utils.logger import logger


LOGIN_BUTTON_SELECTORS = [
    '[data-testid="login-button"]',
    'button[data-testid="login-button"]',
]

SIGNUP_BUTTON_SELECTORS = [
    '[data-testid="signup-button"]',
    'button[data-testid="signup-button"]',
]

LOGGED_OUT_SELECTORS = [
    *LOGIN_BUTTON_SELECTORS,
    *SIGNUP_BUTTON_SELECTORS,
]

ACCOUNT_PROFILE_BUTTON_SELECTOR = '[data-testid="accounts-profile-button"]'

ACCOUNT_USERNAME_SELECTOR = '.min-w-0 .grow .truncate'
ACCOUNT_PLAN_SELECTOR = 'span.inline-flex span'


def get_first_text(parent, selector):
    elements = parent.find_elements(By.CSS_SELECTOR, selector)

    if not elements:
        return ""

    text = elements[0].text.strip()
    return text if text else ""


def find_first_visible_now(driver, selectors):
    """
    Check selectors once and return the first visible element.
    No waiting here.
    """
    if isinstance(selectors, str):
        selectors = [selectors]

    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
        except Exception:
            continue

        for element in elements:
            try:
                if element.is_displayed():
                    return element
            except Exception:
                continue

    return None


def detect_login_state(driver):
    """
    Check login state once.

    Return:
        False
            Not logged in.

        {
            "username": "...",
            "plan": "Plus"
        }
            Logged in.

    Raise:
        AutoChatGPTInternalError
            Failed to detect login state.
    """

    for selector in LOGGED_OUT_SELECTORS:
        if is_visible(driver, selector):
            return False

    account_button = find_first_visible_now(
        driver,
        [ACCOUNT_PROFILE_BUTTON_SELECTOR],
    )

    if not account_button:
        raise AutoChatGPTInternalError("Failed to detect ChatGPT login state.")

    username = get_first_text(account_button, ACCOUNT_USERNAME_SELECTOR)
    plan = get_first_text(account_button, ACCOUNT_PLAN_SELECTOR)

    if not username:
        raise AutoChatGPTInternalError("Failed to get username from account profile button.")

    if not plan:
        raise AutoChatGPTInternalError("Failed to get plan from account profile button.")

    return {
        "username": username,
        "plan": plan,
    }


def detect_known_login_state_or_none(driver):
    """
    Used by WebDriverWait.until().

    Important:
        detect_login_state() returns False when logged out.
        But WebDriverWait.until() treats False as "keep waiting".

    So logged-out state is wrapped as:
        {"logged_out": True}
    """
    try:
        state = detect_login_state(driver)
    except AutoChatGPTInternalError:
        return None

    if state is False:
        return {
            "logged_out": True,
        }

    return state


def detect_logged_in_state_or_none(driver):
    """
    Used by WebDriverWait.until() after clicking login.

    Return logged-in dict only.
    Return None if still logged out or unknown.
    """
    try:
        state = detect_login_state(driver)
    except AutoChatGPTInternalError:
        return None

    if state:
        return state

    return None


def wait_for_login(driver, manual_login_timeout=600):
    """
    Return:
        {
            "username": "...",
            "plan": "Plus"
        }
    """

    logger.info("<<< Check Login State >>>")

    known_state = WebDriverWait(driver, 20).until(
        detect_known_login_state_or_none
    )

    if known_state.get("logged_out"):
        state = False
    else:
        state = known_state

    # Already login
    if state:
        logger.info("Already Login")
        logger.info(f"Username : {state['username']}")
        logger.info(f"Plan     : {state['plan']}")
        return state

    # Click login button and wait
    logger.info("Not logged in, click login button")

    login_btn, _ = wait_clickable(
        driver,
        LOGIN_BUTTON_SELECTORS,
        timeout=10,
    )
    login_btn.click()

    logger.info("Please log in manually...")

    state = WebDriverWait(driver, manual_login_timeout).until(
        detect_logged_in_state_or_none
    )

    logger.info("Login Manually Succeed")
    logger.info(f"Username : {state['username']}")
    logger.info(f"Plan     : {state['plan']}")
    return state
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

from utils.selenium_utils import is_visible, wait_clickable


def detect_login_state(driver):
    """
    Return:
        "logged_out"  not logged in
        "logged_in"   logged in
        None          unknown / page still loading
    """
    logged_out_selectors = [
        '[data-testid="login-button"]',
        'button[data-testid="login-button"]',
        '[data-testid="signup-button"]',
        'button[data-testid="signup-button"]',
    ]

    logged_in_selectors = [
        '[data-testid="profile-button"]',
        'button[data-testid="profile-button"]',
        'button[aria-label*="profile" i]',
        'button[aria-label*="account" i]',
        'button[aria-label*="用户" i]',
        'button[aria-label*="账户" i]',
        'a[href^="/c/"]',
        'nav a[href^="/c/"]',
        'aside a[href^="/c/"]',
    ]

    for selector in logged_out_selectors:
        if is_visible(driver, selector):
            return "logged_out"

    for selector in logged_in_selectors:
        if is_visible(driver, selector):
            return "logged_in"

    return None


def wait_for_login(driver, timeout=120):
    print("Check for login")
    """Wait until the user is logged in (manual login fallback)."""
    try:
        state = WebDriverWait(driver, 20).until(
            lambda d: detect_login_state(d)
        )
    except TimeoutException:
        print("Warning: cannot determine login state")
        return False

    if state == "logged_in":
        print("Already logged in")
        return True

    try:
        login_btn = wait_clickable(
            driver,
            [
                '[data-testid="login-button"]',
                'button[data-testid="login-button"]',
            ],
            timeout=10,
        )
        login_btn.click()
    except Exception:
        print("Failed to click login button")
        pass

    print("Please log in manually...")

    WebDriverWait(driver, timeout).until(
        lambda d: detect_login_state(d) == "logged_in"
    )

    print("Login confirmed")
    return True
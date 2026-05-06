import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException


TURN_SELECTOR = 'section[data-testid^="conversation-turn-"]'
USER_TURN_SELECTOR = 'section[data-testid^="conversation-turn-"][data-turn="user"]'
ASSISTANT_TURN_SELECTOR = 'section[data-testid^="conversation-turn-"][data-turn="assistant"]'


def get_chat_all_turn_cnt(driver):
    """
    Count all turns in the current chat main area.
    Includes both user turns and assistant turns.
    This is NOT the sidebar history count.
    """
    return len(driver.find_elements(By.CSS_SELECTOR, TURN_SELECTOR))


def get_chat_user_turn_cnt(driver):
    """
    Count user turns in the current chat main area.
    """
    return len(driver.find_elements(By.CSS_SELECTOR, USER_TURN_SELECTOR))


def get_chat_assistant_turn_cnt(driver):
    """
    Count assistant turns in the current chat main area.
    """
    return len(driver.find_elements(By.CSS_SELECTOR, ASSISTANT_TURN_SELECTOR))


def get_latest_chat_user_turn(driver):
    """
    Get the latest user turn in the current chat main area.
    """
    turns = driver.find_elements(By.CSS_SELECTOR, USER_TURN_SELECTOR)

    if not turns:
        return None

    return turns[-1]


def get_latest_chat_assistant_turn(driver):
    """
    Get the latest assistant turn in the current chat main area.
    """
    turns = driver.find_elements(By.CSS_SELECTOR, ASSISTANT_TURN_SELECTOR)

    if not turns:
        return None

    return turns[-1]


def get_chat_turn_cnts(driver):
    """
    Return useful turn counts at once.

    Return:
        {
            "all": int,
            "user": int,
            "assistant": int
        }
    """
    return {
        "all": get_chat_all_turn_cnt(driver),
        "user": get_chat_user_turn_cnt(driver),
        "assistant": get_chat_assistant_turn_cnt(driver),
    }


def get_chat_turn_cnt_snapshot(driver):
    """
    Take a count snapshot before sending a message.

    This is useful for checking:
        - user count increased      => message sent
        - assistant count increased => assistant started replying
    """
    return get_chat_turn_cnts(driver)


def wait_user_msg_sent(driver, before_user_cnt, timeout=60):
    """
    Wait until user turn count increases.

    This means the user's message has appeared in the conversation,
    so the message was submitted successfully.
    """
    print("Waiting for user message to be sent...")

    try:
        WebDriverWait(driver, timeout).until(
            lambda d: get_chat_user_turn_cnt(d) > before_user_cnt
        )
        print("User message sent")
        return True
    except TimeoutException:
        print("Warning: timeout while waiting for user message to be sent")
        return False


def wait_assistant_response_started(driver, before_assistant_cnt, timeout=180):
    """
    Wait until assistant turn count increases.

    This means ChatGPT has started creating a new reply.
    """
    print("Waiting for assistant response to start...")

    try:
        WebDriverWait(driver, timeout).until(
            lambda d: get_chat_assistant_turn_cnt(d) > before_assistant_cnt
        )
        print("Assistant response started")
        return True
    except TimeoutException:
        print("Warning: timeout while waiting for assistant response to start")
        return False


def wait_msg_flow_started(
    driver,
    before_user_cnt,
    before_assistant_cnt,
    user_timeout=60,
    assistant_timeout=180,
):
    """
    Wait for the normal message flow:

        1. user turn count increases
        2. assistant turn count increases

    Return:
        True  if both steps succeed
        False if one of the steps times out
    """
    user_sent = wait_user_msg_sent(
        driver,
        before_user_cnt=before_user_cnt,
        timeout=user_timeout,
    )

    if not user_sent:
        return False

    return wait_assistant_response_started(
        driver,
        before_assistant_cnt=before_assistant_cnt,
        timeout=assistant_timeout,
    )


def wait_msg_flow_started_from_snapshot(
    driver,
    snapshot,
    user_timeout=60,
    assistant_timeout=180,
):
    """
    Same as wait_msg_flow_started(), but uses a snapshot dict.

    Example:
        snapshot = get_chat_turn_cnt_snapshot(driver)
        send_prompt_and_image(...)
        wait_msg_flow_started_from_snapshot(driver, snapshot)
    """
    return wait_msg_flow_started(
        driver,
        before_user_cnt=snapshot["user"],
        before_assistant_cnt=snapshot["assistant"],
        user_timeout=user_timeout,
        assistant_timeout=assistant_timeout,
    )


def wait_new_assistant_msg(driver, before_assistant_cnt, timeout=180):
    """
    Wait until assistant turn count increases.
    """
    return wait_assistant_response_started(
        driver,
        before_assistant_cnt=before_assistant_cnt,
        timeout=timeout,
    )


def wait_response_complete(driver, timeout=240, stable_seconds=10):
    """Wait until ChatGPT finishes generating (stop button disappears)."""
    print("Waiting for response...")

    stop_selectors = [
        '[data-testid="stop-button"]',
        'button[data-testid="stop-button"]',
        'button[aria-label*="Stop" i]',
        'button[aria-label*="停止" i]',
    ]

    last_html = ""
    last_change_time = time.time()

    try:
        wait = WebDriverWait(driver, timeout)

        def _response_done(d):
            nonlocal last_html, last_change_time

            stop_visible = False

            for selector in stop_selectors:
                try:
                    elements = d.find_elements(By.CSS_SELECTOR, selector)
                except Exception:
                    continue

                for element in elements:
                    try:
                        if element.is_displayed():
                            stop_visible = True
                            break
                    except Exception:
                        continue

                if stop_visible:
                    break

            latest_turn = get_latest_chat_assistant_turn(d)

            if latest_turn is None:
                return False

            try:
                current_html = latest_turn.get_attribute("innerHTML") or ""
            except Exception:
                return False

            if current_html != last_html:
                last_html = current_html
                last_change_time = time.time()
                return False

            if stop_visible:
                return False

            return time.time() - last_change_time >= stable_seconds

        wait.until(_response_done)

        print("Response complete")
        time.sleep(1)
        return True

    except TimeoutException:
        print("Warning: timeout while waiting for response")
        return False


def wait_full_response_flow_from_snapshot(
    driver,
    snapshot,
    user_timeout=60,
    assistant_timeout=180,
    complete_timeout=240,
    stable_seconds=10,
):
    """
    Full message flow:

        1. Wait for user message sent
        2. Wait for assistant response started
        3. Wait for assistant response complete

    Return:
        True  if all steps succeed
        False if any step times out
    """
    started = wait_msg_flow_started_from_snapshot(
        driver,
        snapshot=snapshot,
        user_timeout=user_timeout,
        assistant_timeout=assistant_timeout,
    )

    if not started:
        return False

    return wait_response_complete(
        driver,
        timeout=complete_timeout,
        stable_seconds=stable_seconds,
    )


def print_chat_turn_debug(driver):
    """
    Debug helper.
    """
    counts = get_chat_turn_cnts(driver)

    print(
        "Current chat turns: "
        f"all={counts['all']}, "
        f"user={counts['user']}, "
        f"assistant={counts['assistant']}"
    )
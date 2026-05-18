from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

from utils.logger import logger
from utils.selenium_utils import any_visible, find_all, visible_elements
from chatgpt_page.dialogs import raise_if_request_too_frequent


TURN_SELECTOR = 'section[data-testid^="conversation-turn-"]'
USER_TURN_SELECTOR = 'section[data-testid^="conversation-turn-"][data-turn="user"]'
ASSISTANT_TURN_SELECTOR = 'section[data-testid^="conversation-turn-"][data-turn="assistant"]'

STOP_BUTTON_SELECTORS = [
    '#composer-submit-button[data-testid="stop-button"]',
    '#composer-submit-button[aria-label*="\u505c\u6b62"]',
    '#composer-submit-button[aria-label*="Stop" i]',
]

SPEECH_BUTTON_SELECTORS = [
    'button[aria-label="\u542f\u52a8\u8bed\u97f3\u529f\u80fd"]',
    'button[aria-label*="\u542f\u52a8\u8bed\u97f3\u529f\u80fd"]',
    'button[aria-label*="voice" i]',
    'button[aria-label*="speech" i]',
]


def get_chat_turn_cnts(driver):
    try:
        user_count = len(find_all(driver, USER_TURN_SELECTOR))
    except Exception:
        user_count = 0

    try:
        assistant_count = len(find_all(driver, ASSISTANT_TURN_SELECTOR))
    except Exception:
        assistant_count = 0

    return {
        "user": user_count,
        "assistant": assistant_count,
    }


def get_latest_chat_turn(driver):
    visible_turns = visible_elements(driver, TURN_SELECTOR)

    if visible_turns:
        return visible_turns[-1]

    turns = find_all(driver, TURN_SELECTOR)
    if turns:
        return turns[-1]

    return None


def get_latest_chat_user_turn(driver):
    visible_turns = visible_elements(driver, USER_TURN_SELECTOR)

    if visible_turns:
        return visible_turns[-1]

    turns = find_all(driver, USER_TURN_SELECTOR)
    if turns:
        return turns[-1]

    return None


def get_latest_chat_assistant_turn(driver):
    visible_turns = visible_elements(driver, ASSISTANT_TURN_SELECTOR)

    if visible_turns:
        return visible_turns[-1]

    turns = find_all(driver, ASSISTANT_TURN_SELECTOR)
    if turns:
        return turns[-1]

    return None


def wait_user_turn_from_snapshot(driver, snapshot, timeout=60):
    logger.info("Wait user message turn appear...")

    wait = WebDriverWait(driver, timeout)

    def _user_turn_added(d):
        raise_if_request_too_frequent(d)
        current = get_chat_turn_cnts(d)
        return current["user"] > snapshot["user"]

    try:
        wait.until(_user_turn_added)
        current = get_chat_turn_cnts(driver)
        logger.info(
            f"User message appeared. user={snapshot['user']} -> {current['user']}"
        )
        return True

    except TimeoutException:
        logger.warning(
            f"Timeout while waiting user message. user snapshot={snapshot['user']}"
        )
        return False


def wait_assistant_turn_from_snapshot(driver, snapshot, timeout=180):
    logger.info("Wait assistant message turn appear...")

    wait = WebDriverWait(driver, timeout)

    def _assistant_turn_added(d):
        raise_if_request_too_frequent(d)
        current = get_chat_turn_cnts(d)
        return current["assistant"] > snapshot["assistant"]

    try:
        wait.until(_assistant_turn_added)
        current = get_chat_turn_cnts(driver)
        logger.info(
            f"Assistant message appeared. assistant={snapshot['assistant']} -> {current['assistant']}"
        )
        return True

    except TimeoutException:
        logger.warning(
            f"Timeout while waiting assistant message. assistant snapshot={snapshot['assistant']}"
        )
        return False


def wait_response_complete(
    driver,
    timeout=240,
    poll_frequency=1,
    required_confirm_count=5,
):
    logger.info("Wait Button [Stop] appear.")

    wait = WebDriverWait(
        driver,
        timeout,
        poll_frequency=poll_frequency,
    )

    def _begin_response(d):
        raise_if_request_too_frequent(d)
        return any_visible(d, STOP_BUTTON_SELECTORS)

    try:
        wait.until(_begin_response)
        logger.info("Button [Stop] appeared.")

    except TimeoutException:
        logger.warning("Timeout while waiting Button [Stop] appear.")
        return False

    logger.info("Begin Wait Response.")

    confirm_count = 0

    def _response_done(d):
        nonlocal confirm_count

        raise_if_request_too_frequent(d)

        stop_visible = any_visible(d, STOP_BUTTON_SELECTORS)
        speech_visible = any_visible(d, SPEECH_BUTTON_SELECTORS)

        if not stop_visible and speech_visible:
            confirm_count += 1
        else:
            confirm_count = 0

        logger.info(
            f"Response complete confirm: {confirm_count} / {required_confirm_count}, "
            f"stop_visible={stop_visible}, speech_visible={speech_visible}"
        )

        return confirm_count >= required_confirm_count

    try:
        wait.until(_response_done)
        logger.info("Response complete")
        return True

    except TimeoutException:
        logger.warning("Timeout while waiting response complete.")
        return False


def wait_response_turn_still_present(driver, timeout=30):
    logger.info("Wait latest assistant turn present...")

    wait = WebDriverWait(driver, timeout)

    def _has_assistant_turn(d):
        raise_if_request_too_frequent(d)
        turn = get_latest_chat_assistant_turn(d)
        return turn if turn is not None else False

    try:
        wait.until(_has_assistant_turn)
        logger.info("Latest assistant turn found")
        return True

    except TimeoutException:
        logger.warning("Timeout while waiting latest assistant turn")
        return False


def wait_full_response_flow_from_snapshot(
    driver,
    snapshot,
    user_timeout=60,
    assistant_timeout=180,
    complete_timeout=240,
    poll_frequency=1,
    assistant_turn_timeout=30,
    required_confirm_count=5,
):
    user_ok = wait_user_turn_from_snapshot(
        driver,
        snapshot=snapshot,
        timeout=user_timeout,
    )

    if not user_ok:
        return False

    assistant_ok = wait_assistant_turn_from_snapshot(
        driver,
        snapshot=snapshot,
        timeout=assistant_timeout,
    )

    if not assistant_ok:
        return False

    complete_ok = wait_response_complete(
        driver,
        timeout=complete_timeout,
        poll_frequency=poll_frequency,
        required_confirm_count=required_confirm_count,
    )

    if not complete_ok:
        return False

    assistant_turn_ok = wait_response_turn_still_present(
        driver,
        timeout=assistant_turn_timeout,
    )

    if not assistant_turn_ok:
        return False

    return True

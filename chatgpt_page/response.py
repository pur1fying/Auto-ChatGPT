import time

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

IMAGE_GENERATION_LOADING_SELECTORS = [
    '[data-testid="image-gen-loading-state"]',
    '[data-testid="image-gen-loading-state-dots"]',
    '[data-testid="loading-halftone-dots-animation"]',
    '[aria-label*="\u6b63\u5728\u751f\u6210\u56fe\u7247"]',
    '[aria-label*="generating image" i]',
    '[aria-label*="creating image" i]',
    '[role="progressbar"]',
    '[aria-busy="true"]',
    '[data-testid*="loading" i]',
    '[data-testid*="spinner" i]',
    '[data-testid*="skeleton" i]',
    '[class*="animate-spin" i]',
    '[class*="skeleton" i]',
]

IMAGE_GENERATION_TEXT_MARKERS = [
    "\u6b63\u5728\u751f\u6210\u56fe\u7247",
    "\u6b63\u5728\u751f\u6210",
    "\u56fe\u7247\u751f\u6210",
    "generating image",
    "creating image",
    "working on image",
]

IMAGE_WAIT_COLUMNS = ("Speech", "NoStop", "NoLoad", "Image")


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


def get_latest_assistant_text(driver) -> str:
    turn = get_latest_chat_assistant_turn(driver)
    if turn is None:
        return ""

    try:
        return (turn.text or "").strip()
    except Exception:
        return ""


def is_displayed_element(element):
    try:
        if not element.is_displayed():
            return False
        rect = element.rect or {}
        return float(rect.get("width") or 0) > 0 and float(rect.get("height") or 0) > 0
    except Exception:
        return False


def get_latest_assistant_image_generation_state(driver):
    turn = get_latest_chat_assistant_turn(driver)
    if turn is None:
        return {
            "turn_present": False,
            "loading_visible": False,
            "loading_count": 0,
            "blob_image_count": 0,
            "final_image_count": 0,
            "final_image_keys": [],
            "text_markers": [],
        }

    loading_count = 0
    for selector in IMAGE_GENERATION_LOADING_SELECTORS:
        try:
            loading_count += sum(
                1 for element in turn.find_elements(By.CSS_SELECTOR, selector)
                if is_displayed_element(element)
            )
        except Exception:
            continue

    text_markers = []
    try:
        text = (turn.text or "").lower()
        text_markers = [
            marker for marker in IMAGE_GENERATION_TEXT_MARKERS
            if marker.lower() in text
        ]
    except Exception:
        text = ""

    blob_image_count = 0
    final_image_keys = []

    for img in turn.find_elements(By.CSS_SELECTOR, "img"):
        try:
            if not is_displayed_element(img):
                continue

            src = img.get_attribute("src") or ""
            width = int(float(img.get_attribute("naturalWidth") or img.get_attribute("width") or 0))
            height = int(float(img.get_attribute("naturalHeight") or img.get_attribute("height") or 0))

            if src.startswith("blob:"):
                blob_image_count += 1

            if width < 128 or height < 128:
                continue

            if "backend-api/estuary/content" in src and "id=file_" in src:
                final_image_keys.append(src)
            elif src.startswith("data:image"):
                final_image_keys.append(src[:120])
            elif src.startswith("blob:"):
                final_image_keys.append(src)
        except Exception:
            continue

    final_image_keys = sorted(set(final_image_keys))

    return {
        "turn_present": True,
        "loading_visible": loading_count > 0 or bool(text_markers),
        "loading_count": loading_count,
        "blob_image_count": blob_image_count,
        "final_image_count": len(final_image_keys),
        "final_image_keys": final_image_keys,
        "text_markers": text_markers,
    }


def is_speech_icon_visible(driver):
    return any_visible(driver, SPEECH_BUTTON_SELECTORS)


def is_stop_button_gone(driver):
    return not any_visible(driver, STOP_BUTTON_SELECTORS)


def is_image_loading_gone(state):
    return not bool(state["loading_visible"])


def is_final_image_stable(state, previous_keys):
    final_image_keys = tuple(state["final_image_keys"])
    return (
        state["final_image_count"] > 0
        and previous_keys is not None
        and final_image_keys == previous_keys
    )


def format_image_wait_cell(is_met, count, required_count):
    return f"{'T' if is_met else 'F'} {min(count, required_count)}/{required_count}"


def format_image_wait_table(round_no, checks, counts, required_count):
    return (
        "Image wait:\n"
        "Round | Speech | NoStop | NoLoad | Image\n"
        f"{round_no:>5} | "
        f"{format_image_wait_cell(checks['speech'], counts['speech'], required_count):<6} | "
        f"{format_image_wait_cell(checks['no_stop'], counts['no_stop'], required_count):<6} | "
        f"{format_image_wait_cell(checks['no_load'], counts['no_load'], required_count):<6} | "
        f"{format_image_wait_cell(checks['image'], counts['image'], required_count):<6}"
    )


def format_image_wait_timeout_details(checks, counts, required_count, state):
    return (
        f"Speech={format_image_wait_cell(checks['speech'], counts['speech'], required_count)}, "
        f"NoStop={format_image_wait_cell(checks['no_stop'], counts['no_stop'], required_count)}, "
        f"NoLoad={format_image_wait_cell(checks['no_load'], counts['no_load'], required_count)}, "
        f"Image={format_image_wait_cell(checks['image'], counts['image'], required_count)}, "
        f"loading_nodes={state.get('loading_count', 0)}, "
        f"final_images={state.get('final_image_count', 0)}, "
        f"blob_images={state.get('blob_image_count', 0)}"
    )


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


def wait_latest_assistant_image_generation_complete(
    driver,
    timeout=600,
    poll_frequency=1,
    required_confirm_count=5,
    min_observation_seconds=5,
):
    logger.info(f"Wait latest assistant image generation complete. need={required_confirm_count} stable checks")

    wait = WebDriverWait(
        driver,
        timeout,
        poll_frequency=poll_frequency,
    )

    last_final_image_keys = None
    start_time = None
    saw_image_generation = False
    round_no = 0
    counts = {
        "speech": 0,
        "no_stop": 0,
        "no_load": 0,
        "image": 0,
    }
    last_checks = {
        "speech": False,
        "no_stop": False,
        "no_load": False,
        "image": False,
    }
    last_state = {
        "loading_count": 0,
        "final_image_count": 0,
        "blob_image_count": 0,
    }

    def _image_generation_done(d):
        nonlocal last_final_image_keys, start_time, saw_image_generation, round_no, last_checks, last_state

        raise_if_request_too_frequent(d)

        if start_time is None:
            start_time = time.monotonic()

        round_no += 1
        state = get_latest_assistant_image_generation_state(d)
        final_image_keys = tuple(state["final_image_keys"])
        loading_visible = not is_image_loading_gone(state)

        if loading_visible or state["final_image_count"] > 0 or state["blob_image_count"] > 0:
            saw_image_generation = True

        observed_long_enough = (time.monotonic() - start_time) >= min_observation_seconds

        if not saw_image_generation and observed_long_enough:
            logger.info(
                f"Image generation: no image generation indicators observed for {min_observation_seconds}s, "
                "continue to result checks."
            )
            return True

        checks = {
            "speech": is_speech_icon_visible(d),
            "no_stop": is_stop_button_gone(d),
            "no_load": is_image_loading_gone(state),
            "image": is_final_image_stable(state, last_final_image_keys),
        }

        for name, is_met in checks.items():
            if is_met:
                counts[name] += 1
            else:
                counts[name] = 0

        last_final_image_keys = final_image_keys
        last_checks = checks
        last_state = state

        logger.info(format_image_wait_table(round_no, checks, counts, required_confirm_count))
        logger.debug(
            "Image wait details: "
            f"loading_nodes={state['loading_count']}, "
            f"final_images={state['final_image_count']}, "
            f"blob_images={state['blob_image_count']}, "
            f"text_markers={len(state['text_markers'])}"
        )

        return all(count >= required_confirm_count for count in counts.values())

    try:
        wait.until(_image_generation_done)
        logger.info(
            "Image generation complete: "
            f"Speech={min(counts['speech'], required_confirm_count)}/{required_confirm_count}, "
            f"NoStop={min(counts['no_stop'], required_confirm_count)}/{required_confirm_count}, "
            f"NoLoad={min(counts['no_load'], required_confirm_count)}/{required_confirm_count}, "
            f"Image={min(counts['image'], required_confirm_count)}/{required_confirm_count}"
        )
        return True

    except TimeoutException:
        logger.warning(
            "Timeout while waiting image generation complete: "
            f"{format_image_wait_timeout_details(last_checks, counts, required_confirm_count, last_state)}"
        )
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
    image_complete_timeout=600,
    image_required_confirm_count=5,
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

    image_generation_ok = wait_latest_assistant_image_generation_complete(
        driver,
        timeout=image_complete_timeout,
        poll_frequency=poll_frequency,
        required_confirm_count=image_required_confirm_count,
    )

    if not image_generation_ok:
        return False

    return True

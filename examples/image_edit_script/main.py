from pathlib import Path
from typing import Any, Dict, Literal

from chatgpt_page.login import wait_for_login
from chatgpt_page.chat import create_new_chat
from chatgpt_page.message import set_prompt_and_image, send_message
from chatgpt_page.response import (
    wait_full_response_flow_from_snapshot,
    get_chat_turn_cnts,
)
from chatgpt_page.sidebar.rename import rename_current_chat
from config.config import (
    FIXED_PROMPT,
    IMAGE_ROOT_DIR,
    SAVE_DIR,
    SCRIPT_CHROME_PROFILE,
    CHROME_VERSION_MAIN,
    driver_exe_path,
    RESULT_JSON_PATH
)
from chatgpt_page.downloader import save_generated_images
from utils.logger import logger
from utils.utils import init_tasks
from utils.selenium_utils import create_driver
from utils.path_utils import get_relative_path

from memory.manager import ImageEditResult
from memory.result_detector import (
    get_page_text,
    detect_policy_failed,
    detect_limit_reached,
)


ProcessResult = Literal["done", "skipped", "stop"]

def process_single_image(
    driver,
    task: Dict[str, Any],
    idx: int,
    total: int,
    result: ImageEditResult,
) -> ProcessResult:
    logger.info(f"Task : {idx + 1}/{total}")

    image_path = Path(task["image_path"]).resolve()
    relative_path = get_relative_path(image_path, IMAGE_ROOT_DIR)

    logger.info(f"Img  : {relative_path}")

    output_base_name = relative_path.stem
    task_output_dir = SAVE_DIR / relative_path.parent
    task_output_dir.mkdir(parents=True, exist_ok=True)

    if result.is_already_processed(image_path):
        record = result.get_task_record(image_path)
        logger.info(f"Skip task : already processed, status={record.get('status')}")
        return "skipped"

    if result.has_existing_output_image(task_output_dir, output_base_name):
        logger.info("Skip task : output image already exists")

        result.mark_existing_output_as_success(
            image_path=image_path,
            relative_path=relative_path,
            output_dir=task_output_dir,
            output_base_name=output_base_name,
        )
        return "skipped"

    if image_path.name.lower().startswith("final"):
        logger.info("Skip task : image name starts with 'final'")

        result.mark_final_name_as_success(
            image_path=image_path,
            relative_path=relative_path,
            output_dir=task_output_dir,
            output_base_name=output_base_name,
        )
        return "skipped"

    create_new_chat(driver)

    snapshot = get_chat_turn_cnts(driver)
    logger.info("Before sending message, snapshot:")
    logger.info(f"User Message : {snapshot['user']}")
    logger.info(f"GPT  Message : {snapshot['assistant']}")

    set_prompt_and_image(
        driver,
        task["prompt"],
        task.get("image_path"),
    )
    send_message(driver, snapshot)

    flow_ok = wait_full_response_flow_from_snapshot(driver, snapshot=snapshot)

    page_text = get_page_text(driver)

    limit_info = detect_limit_reached(page_text)
    if limit_info:
        logger.warning("Image generation limit reached.")
        logger.warning(f"Reset after: {limit_info.get('reset_after_text')}")

        result.mark_limit_reached(
            image_path=image_path,
            relative_path=relative_path,
            output_dir=task_output_dir,
            output_base_name=output_base_name,
            limit_info=limit_info,
        )

        logger.info("<<< Image generation limit reached >>>")
        logger.info(f"Reset after: {limit_info.get('reset_after_text')}")
        logger.info(f"Reset after minutes: {limit_info.get('reset_after_minutes')}")
        logger.info(f"Result saved into: {result.result_json_path}")

        return "stop"

    policy_reason = detect_policy_failed(page_text)
    if policy_reason:
        logger.warning("Policy failed: unable to generate target image.")

        result.mark_policy_failed(
            image_path=image_path,
            relative_path=relative_path,
            output_dir=task_output_dir,
            output_base_name=output_base_name,
            policy_reason=policy_reason,
        )

        rename_current_chat(driver, str(relative_path))
        return "done"

    if not flow_ok:
        logger.warning(f"Response flow failed for task {idx + 1}")

        result.mark_unknown_failed(
            image_path=image_path,
            relative_path=relative_path,
            output_dir=task_output_dir,
            output_base_name=output_base_name,
            message="Response flow failed.",
        )
        return "done"

    before_count = result.count_output_images(
        task_output_dir,
        output_base_name,
    )

    save_generated_images(
        driver,
        task_output_dir,
        idx + 1,
        base_name=output_base_name,
    )

    after_count = result.count_output_images(
        task_output_dir,
        output_base_name,
    )

    if after_count > before_count:
        logger.info("Task success: generated image saved.")

        result.mark_success(
            image_path=image_path,
            relative_path=relative_path,
            output_dir=task_output_dir,
            output_base_name=output_base_name,
            before_count=before_count,
            after_count=after_count,
        )

        rename_current_chat(driver, str(relative_path))
        return "done"

    logger.warning("Task failed: no generated image was saved.")

    result.mark_unknown_failed(
        image_path=image_path,
        relative_path=relative_path,
        output_dir=task_output_dir,
        output_base_name=output_base_name,
        message="No generated image was saved, and no known failure reason was detected.",
    )

    rename_current_chat(driver, str(relative_path))
    return "done"


if __name__ == "__main__":
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    if RESULT_JSON_PATH is None:
        RESULT_JSON_PATH = SAVE_DIR / "result.json"

    result_manager = ImageEditResult(RESULT_JSON_PATH)
    tasks = init_tasks(IMAGE_ROOT_DIR, FIXED_PROMPT)

    driver = create_driver(
        profile_dir=SCRIPT_CHROME_PROFILE,
        version_main=CHROME_VERSION_MAIN,
        driver_exe_path=driver_exe_path,
    )

    try:
        logger.info("Open chatgpt.com")
        driver.get("https://chatgpt.com")

        wait_for_login(driver)

        for idx, task in enumerate(tasks):
            result = process_single_image(
                driver=driver,
                task=task,
                idx=idx,
                total=len(tasks),
                result=result_manager,
            )

            if result == "stop":
                break

    finally:
        driver.quit()
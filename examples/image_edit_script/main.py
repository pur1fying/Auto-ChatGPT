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
from utils.config import config, optional_path
from utils.human_delay import HumanDelay
from chatgpt_page.downloader import save_generated_images
from utils.logger import logger
from utils.utils import init_tasks
from utils.selenium_utils import create_driver
from utils.path_utils import get_relative_path

from examples.image_edit_script.memory.manager import ImageEditResult
from examples.image_edit_script.memory.result_detector import (
    get_page_text,
    detect_policy_failed,
    detect_limit_reached,
    detect_request_too_frequent,
)


ProcessResult = Literal["done", "skipped", "stop"]
OutputLocation = Literal["source", "output"]


def get_output_location(output_image_location: str) -> OutputLocation:
    if output_image_location in {"source", "output"}:
        return output_image_location  # type: ignore[return-value]
    raise ValueError("output.image_location must be 'source' or 'output'")


def get_task_output_target(
    image_path: Path,
    relative_path: Path,
    result: ImageEditResult,
    output_location: OutputLocation,
    save_dir: Path,
) -> tuple[Path, str]:
    if output_location == "source":
        output_path = result.get_source_synced_png_path(image_path)
        return output_path.parent, output_path.stem

    return save_dir / relative_path.parent, relative_path.stem


def rename_task_chat(driver, relative_path: Path, delay: HumanDelay | None = None) -> None:
    rename_current_chat(driver, str(relative_path))
    if delay is not None:
        delay.sleep("after_rename", "after chat rename")


def process_single_image(
    driver,
    task: Dict[str, Any],
    idx: int,
    total: int,
    result: ImageEditResult,
    output_location: OutputLocation,
    image_root_dir: str,
    save_dir: Path,
    delay: HumanDelay | None = None,
) -> ProcessResult:
    logger.info(f"Task : {idx + 1}/{total}")

    image_path = Path(task["image_path"]).resolve()
    relative_path = get_relative_path(image_path, image_root_dir)

    logger.info(f"Img  : {relative_path}")

    task_output_dir, output_base_name = get_task_output_target(
        image_path,
        relative_path,
        result,
        output_location,
        save_dir,
    )
    task_output_dir.mkdir(parents=True, exist_ok=True)

    if result.is_already_processed(image_path):
        record = result.get_task_record(image_path)
        logger.info(f"Skip task : already processed, status={record.get('status')}")
        if output_location == "source":
            result.sync_output_png_to_source_dir(
                image_path,
                record=record,
                source_root_dir=image_root_dir,
                overwrite=False,
            )
        return "skipped"

    if result.has_existing_output_image(task_output_dir, output_base_name):
        logger.info("Skip task : output image already exists")

        result.mark_existing_output_as_success(
            image_path=image_path,
            relative_path=relative_path,
            output_dir=task_output_dir,
            output_base_name=output_base_name,
        )
        if output_location == "source":
            result.sync_output_png_to_source_dir(
                image_path,
                source_root_dir=image_root_dir,
                overwrite=False,
            )
        return "skipped"

    if image_path.name.lower().startswith("final"):
        logger.info("Skip task : image name starts with 'final'")

        result.mark_final_name_as_success(
            image_path=image_path,
            relative_path=relative_path,
        )
        return "skipped"

    try:
        if delay is not None:
            delay.sleep("before_new_chat", "create new chat")
        create_new_chat(driver)

        snapshot = get_chat_turn_cnts(driver)
        logger.info("Before sending message, snapshot:")
        logger.info(f"User Message : {snapshot['user']}")
        logger.info(f"GPT  Message : {snapshot['assistant']}")

        set_prompt_and_image(
            driver,
            task["prompt"],
            task.get("image_path"),
            delay=delay,
        )
        send_message(driver, snapshot, delay=delay)

    except Exception as e:
        message = f"{type(e).__name__}: {e}"
        logger.warning(f"Task setup/send failed: {message}")

        rate_limit_info = detect_request_too_frequent(get_page_text(driver))
        if rate_limit_info:
            logger.warning("Request too frequent dialog detected. Stop batch.")
            logger.warning(f"Message: {rate_limit_info.get('raw_message')}")

            result.mark_rate_limited(
                image_path=image_path,
                relative_path=relative_path,
                rate_limit_info=rate_limit_info,
            )
            return "stop"

        result.mark_unknown_failed(
            image_path=image_path,
            relative_path=relative_path,
            message=message,
        )

        try:
            rename_task_chat(driver, relative_path, delay=delay)
        except Exception as rename_error:
            logger.warning(f"Failed to rename chat after task exception: {rename_error}")

        return "done"

    if delay is not None:
        delay.sleep("before_wait_response", "wait response")
    flow_ok = wait_full_response_flow_from_snapshot(driver, snapshot=snapshot)

    page_text = get_page_text(driver)

    rate_limit_info = detect_request_too_frequent(page_text)
    if rate_limit_info:
        logger.warning("Request too frequent dialog detected. Stop batch.")
        logger.warning(f"Message: {rate_limit_info.get('raw_message')}")

        result.mark_rate_limited(
            image_path=image_path,
            relative_path=relative_path,
            rate_limit_info=rate_limit_info,
        )
        return "stop"

    limit_info = detect_limit_reached(page_text)
    if limit_info:
        logger.warning("Image generation limit reached.")
        logger.warning(f"Reset after: {limit_info.get('reset_after_text')}")

        result.mark_limit_reached(
            image_path=image_path,
            relative_path=relative_path,
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
            policy_reason=policy_reason,
        )

        rename_task_chat(driver, relative_path, delay=delay)
        return "done"

    if not flow_ok:
        logger.warning(f"Response flow failed for task {idx + 1}")

        result.mark_unknown_failed(
            image_path=image_path,
            relative_path=relative_path,
            message="Response flow failed.",
        )
        return "done"

    if delay is not None:
        delay.sleep("before_download", "save generated images")

    saved_paths = save_generated_images(
        driver,
        task_output_dir,
        idx + 1,
        base_name=output_base_name,
    )

    if saved_paths:
        logger.info("Task success: generated image saved.")

        result.mark_success(
            image_path=image_path,
            relative_path=relative_path,
            output_images=[str(path) for path in saved_paths],
        )

        rename_task_chat(driver, relative_path, delay=delay)
        return "done"

    logger.warning("Task failed: no generated image was saved.")

    result.mark_unknown_failed(
        image_path=image_path,
        relative_path=relative_path,
        message="No generated image was saved, and no known failure reason was detected.",
    )

    rename_task_chat(driver, relative_path, delay=delay)
    return "done"


if __name__ == "__main__":
    save_dir = Path(config.get("output.root_dir", "output/images"))
    save_dir.mkdir(parents=True, exist_ok=True)

    result_json_path = optional_path(config.get("output.result_json_path"))
    if result_json_path is None:
        result_json_path = save_dir / "result.json"

    image_root_dir = str(config.get("image_root_dir"))
    fixed_prompt = str(config.get("fixed_prompt"))
    output_image_location = str(config.get("output.image_location", "source")).strip().lower()
    output_location = get_output_location(output_image_location)
    delay = HumanDelay.from_config(config)

    result_manager = ImageEditResult(result_json_path)
    tasks = init_tasks(image_root_dir, fixed_prompt)

    script_chrome_profile = Path(config.get("chrome.profile_dir", "config/test_profile"))
    chrome_version_main = int(config.get("chrome.version_main", 147))
    driver_exe_path = config.get("chrome.driver_exe_path")

    driver = create_driver(
        profile_dir=script_chrome_profile,
        version_main=chrome_version_main,
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
                output_location=output_location,
                image_root_dir=image_root_dir,
                save_dir=save_dir,
                delay=delay,
            )

            if result == "stop":
                break

            if result == "done":
                delay.sleep("between_tasks", f"completed task {idx + 1}")

    finally:
        driver.quit()

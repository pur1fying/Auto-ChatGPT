import time
from pathlib import Path

from chatgpt_page.login import wait_for_login
from chatgpt_page.chat import create_new_chat
from chatgpt_page.message import send_prompt_and_image
from chatgpt_page.response import (
    get_chat_turn_cnt_snapshot,
    wait_full_response_flow_from_snapshot,
    print_chat_turn_debug,
)
from chatgpt_page.rename import rename_current_chat
from config.config import (
    FIXED_PROMPT,
    IMAGE_ROOT_DIR,
    SAVE_DIR,
    SCRIPT_CHROME_PROFILE,
    CHROME_VERSION_MAIN,
)
from downloader import save_generated_images
from utils.utils import init_tasks
from utils.selenium_utils import create_driver
from utils.path_utils import get_relative_path


def run():
    SAVE_DIR.mkdir(parents=True, exist_ok=True)

    tasks = init_tasks(IMAGE_ROOT_DIR, FIXED_PROMPT)

    driver = create_driver(
        profile_dir=SCRIPT_CHROME_PROFILE,
        version_main=CHROME_VERSION_MAIN,
    )

    try:
        # 1. Open ChatGPT
        print("Switching to chatgpt page.")
        driver.get("https://chatgpt.com")

        # 2. Ensure logged in
        wait_for_login(driver)

        # 3. Loop over tasks
        for idx, task in enumerate(tasks):
            print(f"<<< Task {idx + 1}/{len(tasks)} >>>")

            image_path = Path(task["image_path"]).resolve()
            relative_path = get_relative_path(image_path, IMAGE_ROOT_DIR)

            print(f"Image : {relative_path}")

            relative_title = str(relative_path)
            output_relative_dir = relative_path.parent
            output_base_name = relative_path.stem

            # task_output_dir = SAVE_DIR / output_relative_dir
            # task_output_dir.mkdir(parents=True, exist_ok=True)
            #
            # # Create new chat
            # create_new_chat(driver)
            #
            # print_chat_turn_debug(driver)
            #
            # snapshot = get_chat_turn_cnt_snapshot(driver)
            #
            # # Send message
            # send_prompt_and_image(
            #     driver,
            #     task["prompt"],
            #     task.get("image_path"),
            # )
            #
            # # wait for response and download generated image
            # flow_ok = wait_full_response_flow_from_snapshot(
            #     driver,
            #     snapshot=snapshot,
            #     user_timeout=60,
            #     assistant_timeout=180,
            #     complete_timeout=240,
            #     stable_seconds=10,
            # )
            #
            # if not flow_ok:
            #     print(f"Warning: response flow failed for task {idx + 1}")
            #     time.sleep(3)
            #     continue
            #
            # save_generated_images(
            #     driver,
            #     task_output_dir,
            #     idx + 1,
            #     base_name=output_base_name,
            # )

            # rename current chat
            rename_current_chat(driver, relative_title)

            time.sleep(3)  # small delay between tasks

        print("All tasks finished.")

    finally:
        driver.quit()


if __name__ == "__main__":
    run()
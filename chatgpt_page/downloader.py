import base64
from pathlib import Path

from selenium.webdriver.common.by import By

from chatgpt_page.response import get_latest_chat_assistant_turn
from utils.path_utils import safe_filename


def read_image_by_browser(driver, img):
    """
    Read image bytes inside browser context.

    This works for:
        - blob:
        - data:image
        - https://chatgpt.com/backend-api/estuary/content?id=file_...
    """
    src = img.get_attribute("src") or ""

    if not src:
        return None, None

    result = driver.execute_async_script(
        """
        const img = arguments[0];
        const callback = arguments[1];

        async function readImage() {
            try {
                const src = img.src;

                if (!src) {
                    callback(null);
                    return;
                }

                if (src.startsWith("data:")) {
                    callback(src);
                    return;
                }

                const response = await fetch(src, {
                    method: "GET",
                    credentials: "include",
                    cache: "no-store"
                });

                if (!response.ok) {
                    callback({
                        error: true,
                        status: response.status,
                        contentType: response.headers.get("content-type") || "",
                        text: await response.text().catch(() => "")
                    });
                    return;
                }

                const blob = await response.blob();
                const reader = new FileReader();

                reader.onloadend = () => {
                    callback(reader.result);
                };

                reader.onerror = () => {
                    callback(null);
                };

                reader.readAsDataURL(blob);
            } catch (err) {
                callback({
                    error: true,
                    message: String(err)
                });
            }
        }

        readImage();
        """,
        img,
    )

    if not result:
        return None, None

    if isinstance(result, dict) and result.get("error"):
        print(
            "Browser fetch failed: "
            f"status={result.get('status')}, "
            f"contentType={result.get('contentType')}, "
            f"message={result.get('message', '')}"
        )
        return None, None

    if not isinstance(result, str) or not result.startswith("data:"):
        return None, None

    header, data = result.split(",", 1)

    mime = header.split(";")[0].split(":")[-1]
    ext = "png"

    if "/" in mime:
        ext = mime.split("/")[-1]

    if ext == "jpeg":
        ext = "jpg"

    img_data = base64.b64decode(data)

    return img_data, ext


def save_generated_images(driver, save_dir, task_index, base_name=None):
    """Download images from the latest assistant message."""
    try:
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

        last_turn = get_latest_chat_assistant_turn(driver)

        if last_turn is None:
            print("No assistant turns found")
            return

        images = []

        for img in last_turn.find_elements(By.CSS_SELECTOR, "img"):
            try:
                src = img.get_attribute("src") or ""

                width = int(float(img.get_attribute("naturalWidth") or img.get_attribute("width") or 0))
                height = int(float(img.get_attribute("naturalHeight") or img.get_attribute("height") or 0))

                if width < 128 or height < 128:
                    continue

                if (
                    src.startswith("data:image")
                    or src.startswith("blob:")
                    or "backend-api/estuary/content" in src
                    or src.startswith("http")
                ):
                    images.append(img)

            except Exception:
                continue

        if not images:
            print("No generated images found in latest assistant turn")
            return

        if base_name is None:
            base_name = f"chat_img_task{task_index}"
        else:
            base_name = safe_filename(base_name)

        saved_count = 0

        for img in images:
            img_data, ext = read_image_by_browser(driver, img)

            if img_data is None:
                print("Failed to read image from browser context")
                continue

            filename = f"{base_name}_{saved_count}.{ext}"
            path = save_dir / filename

            with open(path, "wb") as f:
                f.write(img_data)

            saved_count += 1
            print(f"Saved: {path}")

        if saved_count == 0:
            print("No image was saved from latest assistant turn")

    except Exception as e:
        print(f"Error saving images: {e}")
import base64
import hashlib
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from selenium.webdriver.common.by import By

from chatgpt_page.response import get_latest_chat_assistant_turn
from utils.logger import logger
from utils.path_utils import safe_filename


def get_img_src_key(src: str) -> str:
    """
    Build a stable key for image deduplication.
    """
    if not src:
        return ""

    if "backend-api/estuary/content" in src:
        try:
            parsed = urlparse(src)
            query = parse_qs(parsed.query)
            file_id = query.get("id", [""])[0]
            if file_id:
                return f"estuary:{file_id}"
        except Exception:
            pass

    if src.startswith("blob:"):
        return src

    if src.startswith("data:image"):
        return hashlib.sha256(src.encode("utf-8", errors="ignore")).hexdigest()

    return src.split("?")[0]


def read_image_by_browser(driver, img):
    """
    Read image bytes inside browser context.

    Works for:
        - blob:
        - data:image
        - https://chatgpt.com/backend-api/estuary/content?id=file_...
    """
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

                reader.onloadend = () => callback(reader.result);
                reader.onerror = () => callback(null);

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
        logger.warning(
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


def collect_candidate_images(last_turn):
    """
    Collect generated images from latest assistant turn and dedupe by src/file_id first.
    """
    images = []
    seen_src_keys = set()

    for img in last_turn.find_elements(By.CSS_SELECTOR, "img"):
        try:
            src = img.get_attribute("src") or ""

            if not src:
                continue

            width = int(float(img.get_attribute("naturalWidth") or img.get_attribute("width") or 0))
            height = int(float(img.get_attribute("naturalHeight") or img.get_attribute("height") or 0))

            # Skip avatars/icons/small UI images
            if width < 128 or height < 128:
                continue

            if not (
                src.startswith("data:image")
                or src.startswith("blob:")
                or src.startswith("http")
                or "backend-api/estuary/content" in src
            ):
                continue

            src_key = get_img_src_key(src)

            if src_key in seen_src_keys:
                logger.debug(f"Skip duplicated image src: {src_key}")
                continue

            seen_src_keys.add(src_key)
            images.append(img)

        except Exception:
            continue

    return images


def build_output_filename(base_name: str, saved_count: int, ext: str) -> str:
    if saved_count == 0:
        return f"{base_name}.{ext}"

    return f"{base_name}_{saved_count}.{ext}"


def save_generated_images(driver, save_dir, task_index, base_name=None):
    """Download images from the latest assistant message."""
    saved_paths = []

    try:
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

        last_turn = get_latest_chat_assistant_turn(driver)

        if last_turn is None:
            logger.warning("No assistant turns found while saving generated images")
            return saved_paths

        images = collect_candidate_images(last_turn)

        if not images:
            logger.warning("No generated images found in latest assistant turn")
            return saved_paths

        if base_name is None:
            base_name = f"chat_img_task{task_index}"
        else:
            base_name = safe_filename(base_name)

        saved_count = 0
        seen_hashes = set()

        for img in images:
            img_data, ext = read_image_by_browser(driver, img)

            if img_data is None:
                logger.warning("Failed to read image from browser context")
                continue

            img_hash = hashlib.sha256(img_data).hexdigest()

            if img_hash in seen_hashes:
                logger.debug("Skip duplicated image content")
                continue

            seen_hashes.add(img_hash)

            filename = build_output_filename(base_name, saved_count, ext)
            path = save_dir / filename

            while path.exists():
                saved_count += 1
                filename = build_output_filename(base_name, saved_count, ext)
                path = save_dir / filename

            with open(path, "wb") as f:
                f.write(img_data)

            saved_paths.append(path.resolve())
            saved_count += 1
            logger.info(f"Saved generated image: {path}")

        if saved_count == 0:
            logger.warning("No image was saved from latest assistant turn")

        return saved_paths

    except Exception as e:
        logger.error(f"Error saving images: {type(e).__name__}: {e}")
        return saved_paths

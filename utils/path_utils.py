import re
from pathlib import Path


def safe_filename(name: str, max_len: int = 120) -> str:
    name = str(name).replace("\\", "__").replace("/", "__")
    name = re.sub(r'[<>:"|?*\r\n\t]', "_", name)
    name = name.strip(" .")

    if not name:
        name = "untitled"

    return name[:max_len]


def get_relative_path(image_path: str | Path, image_root_dir: str | Path) -> Path:
    image_path = Path(image_path).resolve()
    image_root_path = Path(image_root_dir).resolve()

    try:
        return image_path.relative_to(image_root_path)
    except ValueError:
        return Path(image_path.name)
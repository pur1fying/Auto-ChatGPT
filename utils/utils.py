from pathlib import Path


def init_tasks(root_dir: str, prompt: str) -> list[dict[str, str]]:
    """
        Recursive grap image with jpg extension and png without final in it.
    """
    root = Path(root_dir)

    tasks = []

    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue

        suffix = file_path.suffix.lower()
        filename_lower = file_path.name.lower()

        if suffix in {".jpg", ".jpeg"}:
            tasks.append({
                "prompt": prompt,
                "image_path": str(file_path)
            })

        elif suffix == ".png" and "final" not in filename_lower:
            tasks.append({
                "prompt": prompt,
                "image_path": str(file_path)
            })

    return tasks

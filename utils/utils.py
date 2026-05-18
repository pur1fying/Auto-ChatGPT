from pathlib import Path


def init_tasks(root_dir: str, prompt: str) -> list[dict[str, str]]:
    """
        Recursively collect source images.

        PNG files are accepted only when there is no same-stem JPG/JPEG next to
        them. This keeps generated IMG_xxxx.png files from being processed again
        when output.image_location is "source".
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
            same_stem_jpg = file_path.with_suffix(".jpg")
            same_stem_jpeg = file_path.with_suffix(".jpeg")

            if same_stem_jpg.exists() or same_stem_jpeg.exists():
                continue

            tasks.append({
                "prompt": prompt,
                "image_path": str(file_path)
            })

    tasks.sort(
        key=lambda task: (
            str(Path(task["image_path"]).parent.relative_to(root)).lower(),
            Path(task["image_path"]).name.lower(),
        )
    )

    return tasks

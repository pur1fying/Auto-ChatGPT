# examples/image_edit_script/result_memory/manager.py

import json
from enum import Enum
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from utils.logger import logger


class ProcessStatus(str, Enum):
    SUCCESS = "success"
    POLICY_FAILED = "policy_failed"
    LIMIT_REACHED = "limit_reached"
    UNKNOWN_FAILED = "unknown_failed"


class ImageEditResult:
    IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

    PROCESSED_STATUSES = {
        ProcessStatus.SUCCESS,
        ProcessStatus.POLICY_FAILED,
    }

    def __init__(self, result_json_path: Path):
        self.result_json_path = Path(result_json_path)
        self.data = self._load()

    @staticmethod
    def now_iso() -> str:
        return datetime.now().isoformat(timespec="seconds")

    @staticmethod
    def make_image_key(image_path: Path) -> str:
        return str(Path(image_path).resolve())

    @classmethod
    def create_empty_data(cls) -> Dict[str, Any]:
        return {
            "version": 1,
            "created_at": cls.now_iso(),
            "updated_at": cls.now_iso(),
            "limit_info": None,
            "tasks": {},
        }

    def _load(self) -> Dict[str, Any]:
        if not self.result_json_path.exists():
            logger.info(f"Result json not found, create new memory: {self.result_json_path}")
            return self.create_empty_data()

        try:
            with self.result_json_path.open("r", encoding="utf-8") as f:
                data = json.load(f)

            data.setdefault("version", 1)
            data.setdefault("created_at", self.now_iso())
            data.setdefault("updated_at", self.now_iso())
            data.setdefault("limit_info", None)
            data.setdefault("tasks", {})

            logger.info(f"Loaded result json: {self.result_json_path}")
            return data

        except Exception as e:
            backup_path = self.result_json_path.with_suffix(".broken.json")
            self.result_json_path.rename(backup_path)

            logger.warning(f"Result json is broken, backup to: {backup_path}")
            logger.warning(f"Load result json error: {e}")

            return self.create_empty_data()

    def save(self) -> None:
        self.result_json_path.parent.mkdir(parents=True, exist_ok=True)

        self.data["updated_at"] = self.now_iso()

        tmp_path = self.result_json_path.with_suffix(".tmp")

        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

        tmp_path.replace(self.result_json_path)
        logger.info(f"Saved result json: {self.result_json_path}")

    def get_task_record(self, image_path: Path) -> Optional[Dict[str, Any]]:
        image_key = self.make_image_key(image_path)
        return self.data.get("tasks", {}).get(image_key)

    @staticmethod
    def status_from_value(value: str | None) -> Optional[ProcessStatus]:
        if value is None:
            return None

        try:
            return ProcessStatus(value)
        except ValueError:
            return None

    def is_already_processed(self, image_path: Path) -> bool:
        record = self.get_task_record(image_path)
        if not record:
            return False

        status = self.status_from_value(record.get("status"))
        return status in self.PROCESSED_STATUSES

    def count_output_images(self, output_dir: Path, base_name: str) -> int:
        if not output_dir.exists():
            return 0

        return sum(
            1
            for path in output_dir.glob(f"{base_name}*")
            if path.is_file() and path.suffix.lower() in self.IMAGE_EXTS
        )

    def list_output_images(self, output_dir: Path, base_name: str) -> list[str]:
        if not output_dir.exists():
            return []

        paths = [
            str(path.resolve())
            for path in output_dir.glob(f"{base_name}*")
            if path.is_file() and path.suffix.lower() in self.IMAGE_EXTS
        ]

        return sorted(paths)

    def has_existing_output_image(self, output_dir: Path, base_name: str) -> bool:
        return self.count_output_images(output_dir, base_name) > 0

    def update_task_result(
        self,
        image_path: Path,
        *,
        status: ProcessStatus,
        message: str,
        relative_path: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        output_base_name: Optional[str] = None,
        output_images: Optional[list[str]] = None,
        extra: Optional[Dict[str, Any]] = None,
        auto_save: bool = True,
    ) -> None:
        image_path = Path(image_path).resolve()
        image_key = self.make_image_key(image_path)

        old_record = self.data["tasks"].get(image_key)

        record = {
            "status": status.value,
            "image_path": str(image_path),
            "message": message,
            "updated_at": self.now_iso(),
        }

        if old_record and "created_at" in old_record:
            record["created_at"] = old_record["created_at"]
        else:
            record["created_at"] = self.now_iso()

        if relative_path is not None:
            record["relative_path"] = str(relative_path)

        if output_dir is not None:
            record["output_dir"] = str(output_dir)

        if output_base_name is not None:
            record["output_base_name"] = output_base_name

        if output_images is not None:
            record["output_images"] = output_images

        if extra:
            record.update(extra)

        self.data["tasks"][image_key] = record

        logger.info(f"Update task result: {image_path}")
        logger.info(f"Status: {status.value}")
        logger.info(f"Message: {message}")

        if auto_save:
            self.save()

    def mark_existing_output_as_success(
        self,
        image_path: Path,
        relative_path: Path,
        output_dir: Path,
        output_base_name: str,
    ) -> None:
        self.update_task_result(
            image_path,
            status=ProcessStatus.SUCCESS,
            message="Output image already exists, marked as success.",
            relative_path=relative_path,
            output_dir=output_dir,
            output_base_name=output_base_name,
            output_images=self.list_output_images(output_dir, output_base_name),
        )

    def mark_final_name_as_success(
        self,
        image_path: Path,
        relative_path: Path,
        output_dir: Path,
        output_base_name: str,
    ) -> None:
        self.update_task_result(
            image_path,
            status=ProcessStatus.SUCCESS,
            message="Image name starts with final, treated as already edited.",
            relative_path=relative_path,
            output_dir=output_dir,
            output_base_name=output_base_name,
            output_images=[],
        )

    def mark_success(
        self,
        image_path: Path,
        relative_path: Path,
        output_dir: Path,
        output_base_name: str,
        *,
        before_count: int,
        after_count: int,
    ) -> None:
        self.update_task_result(
            image_path,
            status=ProcessStatus.SUCCESS,
            message="Generated image saved successfully.",
            relative_path=relative_path,
            output_dir=output_dir,
            output_base_name=output_base_name,
            output_images=self.list_output_images(output_dir, output_base_name),
            extra={
                "before_output_count": before_count,
                "after_output_count": after_count,
            },
        )

    def mark_policy_failed(
        self,
        image_path: Path,
        relative_path: Path,
        output_dir: Path,
        output_base_name: str,
        *,
        policy_reason: str,
    ) -> None:
        self.update_task_result(
            image_path,
            status=ProcessStatus.POLICY_FAILED,
            message="Unable to generate target image because the generated image may violate content policies.",
            relative_path=relative_path,
            output_dir=output_dir,
            output_base_name=output_base_name,
            output_images=[],
            extra={
                "policy_reason": policy_reason,
            },
        )

    def mark_limit_reached(
        self,
        image_path: Path,
        relative_path: Path,
        output_dir: Path,
        output_base_name: str,
        *,
        limit_info: Dict[str, Any],
    ) -> None:
        self.data["limit_info"] = limit_info

        self.update_task_result(
            image_path,
            status=ProcessStatus.LIMIT_REACHED,
            message="Plus plan image generation limit reached. Program stopped here.",
            relative_path=relative_path,
            output_dir=output_dir,
            output_base_name=output_base_name,
            output_images=[],
            extra={
                "limit_info": limit_info,
            },
        )

    def mark_unknown_failed(
        self,
        image_path: Path,
        relative_path: Path,
        output_dir: Path,
        output_base_name: str,
        *,
        message: str,
    ) -> None:
        self.update_task_result(
            image_path,
            status=ProcessStatus.UNKNOWN_FAILED,
            message=message,
            relative_path=relative_path,
            output_dir=output_dir,
            output_base_name=output_base_name,
            output_images=self.list_output_images(output_dir, output_base_name),
        )
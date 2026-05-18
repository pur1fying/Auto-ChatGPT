# examples/image_edit_script/result_memory/manager.py

import json
import shutil
from enum import Enum
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from utils.logger import logger


class ProcessStatus(str, Enum):
    SUCCESS = "success"
    POLICY_FAILED = "policy_failed"
    LIMIT_REACHED = "limit_reached"
    RATE_LIMITED = "rate_limited"
    UNKNOWN_FAILED = "unknown_failed"


class ImageEditResult:
    IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    SYNC_OUTPUT_EXTS = {".png"}

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
            json.dump(self.data, f, ensure_ascii=False, separators=(",", ":"))

        tmp_path.replace(self.result_json_path)
        logger.info(f"Saved result json: {self.result_json_path}")

    def get_task_record(self, image_path: Path) -> Optional[Dict[str, Any]]:
        image_key = self.make_image_key(image_path)
        record = self.data.get("tasks", {}).get(image_key)

        if record:
            return record

        image_name = Path(image_path).name.lower()
        matched_records = [
            task_record
            for task_key, task_record in self.data.get("tasks", {}).items()
            if Path(task_record.get("image_path") or task_key).name.lower() == image_name
        ]

        if len(matched_records) == 1:
            return matched_records[0]

        return None

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

    def count_output_images(
        self,
        output_dir: Path,
        base_name: str,
        exts: Optional[set[str]] = None,
    ) -> int:
        if not output_dir.exists():
            return 0

        if exts is None:
            exts = self.IMAGE_EXTS

        return sum(
            1
            for path in output_dir.glob(f"{base_name}*")
            if path.is_file() and path.suffix.lower() in exts
        )

    def list_output_images(
        self,
        output_dir: Path,
        base_name: str,
        exts: Optional[set[str]] = None,
    ) -> list[str]:
        if not output_dir.exists():
            return []

        if exts is None:
            exts = self.IMAGE_EXTS

        paths = [
            str(path.resolve())
            for path in output_dir.glob(f"{base_name}*")
            if path.is_file() and path.suffix.lower() in exts
        ]

        return sorted(paths)

    def list_record_output_pngs(self, record: Dict[str, Any]) -> list[Path]:
        paths: list[Path] = []

        for value in record.get("output_images") or []:
            path = Path(value)
            if path.is_file() and path.suffix.lower() in self.SYNC_OUTPUT_EXTS:
                paths.append(path.resolve())

        if not paths:
            output_dir = record.get("output_dir")
            output_base_name = record.get("output_base_name")

            if output_dir and output_base_name:
                paths = [
                    Path(path).resolve()
                    for path in self.list_output_images(Path(output_dir), output_base_name)
                    if Path(path).suffix.lower() in self.SYNC_OUTPUT_EXTS
                ]

        return sorted(set(paths))

    @staticmethod
    def get_source_synced_png_path(image_path: Path) -> Path:
        image_path = Path(image_path).resolve()

        if image_path.suffix.lower() == ".png":
            return image_path.with_name(f"{image_path.stem}_edited.png")

        return image_path.with_suffix(".png")

    @staticmethod
    def find_current_source_image_path(image_path: Path, source_root_dir: Optional[Path] = None) -> Path:
        image_path = Path(image_path).resolve()

        if image_path.exists():
            return image_path

        if source_root_dir is None:
            return image_path

        source_root = Path(source_root_dir)
        if not source_root.exists():
            return image_path

        matches = [
            path.resolve()
            for path in source_root.rglob(image_path.name)
            if path.is_file()
        ]

        if len(matches) == 1:
            return matches[0]

        return image_path

    def sync_output_png_to_source_dir(
        self,
        image_path: Path,
        *,
        record: Optional[Dict[str, Any]] = None,
        source_root_dir: Optional[Path] = None,
        overwrite: bool = False,
    ) -> Optional[Path]:
        if record is None:
            record = self.get_task_record(image_path)

        if not record:
            logger.warning(f"Skip sync output png: result record not found, image={image_path}")
            return None

        status = self.status_from_value(record.get("status"))
        if status != ProcessStatus.SUCCESS:
            logger.info(f"Skip sync output png: status={record.get('status')}")
            return None

        output_pngs = self.list_record_output_pngs(record)
        if not output_pngs:
            logger.warning(f"Skip sync output png: no output png found, image={image_path}")
            return None

        source_path = self.find_current_source_image_path(
            Path(record.get("image_path") or image_path),
            source_root_dir=source_root_dir,
        )
        synced_path = self.get_source_synced_png_path(source_path)
        synced_path.parent.mkdir(parents=True, exist_ok=True)

        if synced_path.exists() and not overwrite:
            logger.info(f"Skip sync output png: target already exists, target={synced_path}")
        else:
            shutil.copy2(output_pngs[0], synced_path)
            logger.info(f"Synced output png: {output_pngs[0]} -> {synced_path}")

        return synced_path

    def sync_success_outputs_to_source_dirs(
        self,
        *,
        source_root_dir: Optional[Path] = None,
        overwrite: bool = False,
    ) -> Dict[str, int]:
        stats = {
            "success": 0,
            "skipped": 0,
            "failed": 0,
        }

        for image_key, record in self.data.get("tasks", {}).items():
            status = self.status_from_value(record.get("status"))
            if status != ProcessStatus.SUCCESS:
                stats["skipped"] += 1
                continue

            try:
                synced_path = self.sync_output_png_to_source_dir(
                    Path(record.get("image_path") or image_key),
                    record=record,
                    source_root_dir=source_root_dir,
                    overwrite=overwrite,
                )
            except Exception as e:
                logger.warning(f"Failed to sync output png for {image_key}: {e}")
                stats["failed"] += 1
                continue

            if synced_path is None:
                stats["skipped"] += 1
            else:
                stats["success"] += 1

        logger.info(
            "Sync output png summary: "
            f"success={stats['success']}, skipped={stats['skipped']}, failed={stats['failed']}"
        )
        return stats

    def has_existing_output_image(self, output_dir: Path, base_name: str) -> bool:
        return self.count_output_images(output_dir, base_name, self.SYNC_OUTPUT_EXTS) > 0

    def update_task_result(
        self,
        image_path: Path,
        *,
        status: ProcessStatus,
        message: str,
        relative_path: Optional[Path] = None,
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

        if output_images:
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
            output_images=self.list_output_images(
                output_dir,
                output_base_name,
                self.SYNC_OUTPUT_EXTS,
            ),
        )

    def mark_final_name_as_success(
        self,
        image_path: Path,
        relative_path: Path,
    ) -> None:
        self.update_task_result(
            image_path,
            status=ProcessStatus.SUCCESS,
            message="Image name starts with final, treated as already edited.",
            relative_path=relative_path,
            output_images=[],
        )

    def mark_success(
        self,
        image_path: Path,
        relative_path: Path,
        *,
        output_images: list[str],
    ) -> None:
        self.update_task_result(
            image_path,
            status=ProcessStatus.SUCCESS,
            message="Generated image saved successfully.",
            relative_path=relative_path,
            output_images=output_images,
        )

    def mark_policy_failed(
        self,
        image_path: Path,
        relative_path: Path,
        *,
        policy_reason: str,
    ) -> None:
        self.update_task_result(
            image_path,
            status=ProcessStatus.POLICY_FAILED,
            message="Unable to generate target image because the generated image may violate content policies.",
            relative_path=relative_path,
            output_images=[],
            extra={
                "policy_reason": policy_reason,
            },
        )

    def mark_limit_reached(
        self,
        image_path: Path,
        relative_path: Path,
        *,
        limit_info: Dict[str, Any],
    ) -> None:
        self.data["limit_info"] = limit_info

        self.update_task_result(
            image_path,
            status=ProcessStatus.LIMIT_REACHED,
            message="Plus plan image generation limit reached. Program stopped here.",
            relative_path=relative_path,
            output_images=[],
            extra={
                "limit_info": limit_info,
            },
        )

    def mark_rate_limited(
        self,
        image_path: Path,
        relative_path: Path,
        *,
        rate_limit_info: Dict[str, Any],
    ) -> None:
        self.data["rate_limit_info"] = rate_limit_info

        self.update_task_result(
            image_path,
            status=ProcessStatus.RATE_LIMITED,
            message="Request too frequent. Program stopped here to avoid triggering more rate limits.",
            relative_path=relative_path,
            output_images=[],
            extra={
                "rate_limit_info": rate_limit_info,
            },
        )

    def mark_unknown_failed(
        self,
        image_path: Path,
        relative_path: Path,
        *,
        message: str,
    ) -> None:
        self.update_task_result(
            image_path,
            status=ProcessStatus.UNKNOWN_FAILED,
            message=message,
            relative_path=relative_path,
        )

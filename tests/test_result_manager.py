import tempfile
import unittest
from pathlib import Path

from examples.image_edit_script.memory.manager import ImageEditResult


class ImageEditResultTests(unittest.TestCase):
    def test_policy_failed_is_skipped_when_enabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / "IMG_0001.JPG"
            manager = ImageEditResult(Path(tmpdir) / "result.json")
            manager.mark_policy_failed(
                image_path=image_path,
                relative_path=Path("IMG_0001.JPG"),
                policy_reason="policy",
            )

            self.assertTrue(manager.is_already_processed(image_path, include_policy_failed=True))

    def test_policy_failed_is_retryable_when_disabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / "IMG_0001.JPG"
            manager = ImageEditResult(Path(tmpdir) / "result.json")
            manager.mark_policy_failed(
                image_path=image_path,
                relative_path=Path("IMG_0001.JPG"),
                policy_reason="policy",
            )

            self.assertFalse(manager.is_already_processed(image_path, include_policy_failed=False))

    def test_unknown_failed_records_gpt_response_text(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / "IMG_0001.JPG"
            manager = ImageEditResult(Path(tmpdir) / "result.json")
            manager.mark_unknown_failed(
                image_path=image_path,
                relative_path=Path("IMG_0001.JPG"),
                message="No generated image was saved.",
                gpt_response_text="I could not edit this image.",
                page_text_excerpt="full page text",
            )

            record = manager.get_task_record(image_path)

            self.assertIsNotNone(record)
            self.assertEqual(record["gpt_response_text"], "I could not edit this image.")
            self.assertEqual(record["gpt_response_text_length"], len("I could not edit this image."))
            self.assertEqual(record["page_text_excerpt"], "full page text")
            self.assertIn("gpt_response_captured_at", record)

    def test_failure_text_snapshot_is_truncated(self):
        text = "x" * 5000

        snapshot = ImageEditResult.make_text_snapshot(text)

        self.assertEqual(len(snapshot), 4000)


if __name__ == "__main__":
    unittest.main()

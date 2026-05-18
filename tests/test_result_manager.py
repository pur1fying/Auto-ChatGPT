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


if __name__ == "__main__":
    unittest.main()

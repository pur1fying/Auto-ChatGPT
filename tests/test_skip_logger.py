import unittest
from pathlib import Path
from unittest.mock import patch

from examples.image_edit_script.main import ConsecutiveSkipLogger


class ConsecutiveSkipLoggerTest(unittest.TestCase):
    def test_merges_consecutive_same_reason(self):
        skip_logger = ConsecutiveSkipLogger()

        with patch("examples.image_edit_script.main.logger.info") as info:
            skip_logger.record(5, 287, Path("企业/IMG_0564.JPG"), "processed:success", "already processed, status=success")
            skip_logger.record(6, 287, Path("企业/IMG_0565.JPG"), "processed:success", "already processed, status=success")
            skip_logger.record(7, 287, Path("企业/IMG_0566.JPG"), "processed:success", "already processed, status=success")
            skip_logger.flush()

        info.assert_called_once()
        message = info.call_args.args[0]
        self.assertIn("Skip tasks 6-8/287", message)
        self.assertIn("3 images", message)
        self.assertIn("already processed, status=success", message)

    def test_flushes_when_reason_changes(self):
        skip_logger = ConsecutiveSkipLogger()

        with patch("examples.image_edit_script.main.logger.info") as info:
            skip_logger.record(0, 10, Path("a.JPG"), "processed:success", "already processed, status=success")
            skip_logger.record(1, 10, Path("b.JPG"), "processed:policy_failed", "previous result was policy_failed")
            skip_logger.flush()

        self.assertEqual(info.call_count, 2)
        first_message = info.call_args_list[0].args[0]
        second_message = info.call_args_list[1].args[0]
        self.assertIn("Skip task 1/10", first_message)
        self.assertIn("already processed, status=success", first_message)
        self.assertIn("Skip task 2/10", second_message)
        self.assertIn("previous result was policy_failed", second_message)


if __name__ == "__main__":
    unittest.main()

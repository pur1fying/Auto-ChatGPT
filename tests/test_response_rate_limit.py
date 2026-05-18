import unittest
from unittest.mock import Mock, patch

from chatgpt_page import response
from chatgpt_page.dialogs import RequestTooFrequentError


class ResponseRateLimitTests(unittest.TestCase):
    def test_wait_user_turn_raises_when_rate_limit_dialog_appears(self):
        with patch.object(
            response,
            "raise_if_request_too_frequent",
            side_effect=RequestTooFrequentError("limited"),
        ):
            with self.assertRaises(RequestTooFrequentError):
                response.wait_user_turn_from_snapshot(Mock(), {"user": 0, "assistant": 0}, timeout=1)

    def test_wait_response_complete_still_succeeds_without_dialog(self):
        with (
            patch.object(response, "raise_if_request_too_frequent", return_value=None),
            patch.object(response, "any_visible", side_effect=[True, False, True]),
        ):
            self.assertTrue(
                response.wait_response_complete(
                    Mock(),
                    timeout=1,
                    poll_frequency=0.01,
                    required_confirm_count=1,
                )
            )


if __name__ == "__main__":
    unittest.main()

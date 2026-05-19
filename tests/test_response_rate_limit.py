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

    def test_image_generation_loading_state_detects_halftone_dots(self):
        class FakeElement:
            text = ""
            rect = {"width": 480, "height": 480}

            def __init__(self, attrs=None):
                self.attrs = attrs or {}

            def is_displayed(self):
                return True

            def get_attribute(self, name):
                return self.attrs.get(name, "")

        class FakeTurn:
            text = ""

            def find_elements(self, _by, selector):
                if selector == '[data-testid="image-gen-loading-state"]':
                    return [FakeElement()]
                if selector == "img":
                    return []
                return []

        with patch.object(response, "get_latest_chat_assistant_turn", return_value=FakeTurn()):
            state = response.get_latest_assistant_image_generation_state(Mock())

        self.assertTrue(state["loading_visible"])
        self.assertEqual(state["loading_count"], 1)
        self.assertEqual(state["final_image_count"], 0)

    def test_image_generation_state_detects_final_estuary_image(self):
        class FakeImage:
            rect = {"width": 1024, "height": 1024}

            def is_displayed(self):
                return True

            def get_attribute(self, name):
                return {
                    "src": "https://chatgpt.com/backend-api/estuary/content?id=file_abc",
                    "naturalWidth": "1024",
                    "naturalHeight": "1024",
                }.get(name, "")

        class FakeTurn:
            text = ""

            def find_elements(self, _by, selector):
                if selector == "img":
                    return [FakeImage()]
                return []

        with patch.object(response, "get_latest_chat_assistant_turn", return_value=FakeTurn()):
            state = response.get_latest_assistant_image_generation_state(Mock())

        self.assertFalse(state["loading_visible"])
        self.assertEqual(state["final_image_count"], 1)
        self.assertIn("file_abc", state["final_image_keys"][0])

    def test_image_generation_completion_waits_for_all_indicators(self):
        states = iter([
            {
                "loading_visible": False,
                "loading_count": 0,
                "blob_image_count": 0,
                "final_image_count": 1,
                "final_image_keys": ["file_a"],
                "text_markers": [],
            },
            {
                "loading_visible": False,
                "loading_count": 0,
                "blob_image_count": 0,
                "final_image_count": 1,
                "final_image_keys": ["file_a"],
                "text_markers": [],
            },
        ])

        with (
            patch.object(response, "raise_if_request_too_frequent", return_value=None),
            patch.object(response, "is_speech_icon_visible", return_value=True),
            patch.object(response, "is_stop_button_gone", return_value=True),
            patch.object(response, "get_latest_assistant_image_generation_state", side_effect=lambda _driver: next(states)),
        ):
            self.assertTrue(
                response.wait_latest_assistant_image_generation_complete(
                    Mock(),
                    timeout=1,
                    poll_frequency=0.01,
                    required_confirm_count=1,
                    min_observation_seconds=5,
                )
            )

    def test_image_generation_completion_resets_changed_image_key(self):
        state_values = [
            {
                "loading_visible": False,
                "loading_count": 0,
                "blob_image_count": 0,
                "final_image_count": 1,
                "final_image_keys": ["file_a"],
                "text_markers": [],
            },
            {
                "loading_visible": False,
                "loading_count": 0,
                "blob_image_count": 0,
                "final_image_count": 1,
                "final_image_keys": ["file_a"],
                "text_markers": [],
            },
            {
                "loading_visible": False,
                "loading_count": 0,
                "blob_image_count": 0,
                "final_image_count": 1,
                "final_image_keys": ["file_b"],
                "text_markers": [],
            },
            {
                "loading_visible": False,
                "loading_count": 0,
                "blob_image_count": 0,
                "final_image_count": 1,
                "final_image_keys": ["file_b"],
                "text_markers": [],
            },
            {
                "loading_visible": False,
                "loading_count": 0,
                "blob_image_count": 0,
                "final_image_count": 1,
                "final_image_keys": ["file_b"],
                "text_markers": [],
            },
        ]
        states = iter(state_values)

        with (
            patch.object(response, "raise_if_request_too_frequent", return_value=None),
            patch.object(response, "is_speech_icon_visible", return_value=True),
            patch.object(response, "is_stop_button_gone", return_value=True),
            patch.object(response, "get_latest_assistant_image_generation_state", side_effect=lambda _driver: next(states)) as get_state,
        ):
            self.assertTrue(
                response.wait_latest_assistant_image_generation_complete(
                    Mock(),
                    timeout=1,
                    poll_frequency=0.01,
                    required_confirm_count=2,
                    min_observation_seconds=5,
                )
            )

        self.assertEqual(get_state.call_count, 5)

    def test_image_wait_table_is_readable(self):
        table = response.format_image_wait_table(
            3,
            {"speech": True, "no_stop": True, "no_load": False, "image": True},
            {"speech": 3, "no_stop": 3, "no_load": 0, "image": 2},
            5,
        )

        self.assertIn("Speech | NoStop | NoLoad | Image", table)
        self.assertIn("T 3/5", table)
        self.assertIn("F 0/5", table)
        self.assertIn("T 2/5", table)


if __name__ == "__main__":
    unittest.main()

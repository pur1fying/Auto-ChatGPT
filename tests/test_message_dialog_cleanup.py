import unittest
from unittest.mock import Mock, patch

from selenium.common.exceptions import ElementClickInterceptedException

from chatgpt_page import message


class MessageDialogCleanupTests(unittest.TestCase):
    def test_get_visible_blocking_dialogs_returns_only_displayed_elements(self):
        visible = Mock()
        visible.is_displayed.return_value = True
        hidden = Mock()
        hidden.is_displayed.return_value = False

        driver = Mock()
        driver.find_elements.side_effect = [[hidden, visible], [], []]

        dialogs = message.get_visible_blocking_dialogs(driver)

        self.assertEqual(dialogs, [visible])

    def test_dismiss_blocking_dialog_returns_false_when_nothing_blocks(self):
        with patch.object(message, "get_visible_blocking_dialogs", return_value=[]):
            self.assertFalse(message.dismiss_blocking_dialog_if_present(Mock()))

    def test_dismiss_blocking_dialog_prefers_escape(self):
        driver = Mock()
        dialog = Mock()
        dialog.text = "Regular dialog"

        with (
            patch.object(message, "get_visible_blocking_dialogs", return_value=[dialog]),
            patch.object(message, "_send_escape", return_value=True) as send_escape,
            patch.object(message, "wait_blocking_dialog_closed", return_value=True),
            patch.object(message, "_click_dialog_close_button", return_value=True) as click_close,
        ):
            self.assertTrue(message.dismiss_blocking_dialog_if_present(driver))

        send_escape.assert_called_once_with(driver)
        click_close.assert_not_called()

    def test_dismiss_blocking_dialog_does_not_close_request_too_frequent(self):
        dialog = Mock()
        dialog.text = "请求过于频繁 请稍等几分钟后再重试"

        with patch.object(message, "get_visible_blocking_dialogs", return_value=[dialog]):
            with self.assertRaisesRegex(Exception, "Request too frequent"):
                message.dismiss_blocking_dialog_if_present(Mock())

    def test_set_prompt_text_retries_after_intercepted_click(self):
        prompt_input = Mock()
        prompt_input.click.side_effect = [
            ElementClickInterceptedException("blocked"),
            None,
        ]

        driver = Mock()

        with patch.object(message, "dismiss_blocking_dialog_if_present", return_value=False):
            message.set_prompt_text(
                prompt_input,
                "hello",
                check=False,
                driver=driver,
                input_getter=lambda: prompt_input,
            )

        self.assertEqual(prompt_input.click.call_count, 2)
        prompt_input.clear.assert_called_once()
        prompt_input.send_keys.assert_called_once_with("hello")


if __name__ == "__main__":
    unittest.main()

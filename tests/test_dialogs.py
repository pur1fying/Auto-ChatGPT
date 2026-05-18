import unittest
from unittest.mock import Mock, patch

from chatgpt_page import dialogs


class DialogTests(unittest.TestCase):
    def test_get_visible_dialogs_returns_only_displayed_elements(self):
        visible = Mock()
        visible.is_displayed.return_value = True
        hidden = Mock()
        hidden.is_displayed.return_value = False

        driver = Mock()
        driver.find_elements.side_effect = [[hidden, visible], [], []]

        self.assertEqual(dialogs.get_visible_dialogs(driver), [visible])

    def test_dismiss_blocking_dialog_returns_false_when_nothing_blocks(self):
        with patch.object(dialogs, "get_visible_dialogs", return_value=[]):
            self.assertFalse(dialogs.dismiss_blocking_dialog_if_present(Mock()))

    def test_dismiss_blocking_dialog_prefers_escape(self):
        driver = Mock()
        dialog = Mock()
        dialog.text = "Regular dialog"

        with (
            patch.object(dialogs, "get_visible_dialogs", return_value=[dialog]),
            patch.object(dialogs, "_send_escape", return_value=True) as send_escape,
            patch.object(dialogs, "wait_blocking_dialog_closed", return_value=True),
            patch.object(dialogs, "_click_dialog_close_button", return_value=True) as click_close,
        ):
            self.assertTrue(dialogs.dismiss_blocking_dialog_if_present(driver))

        send_escape.assert_called_once_with(driver)
        click_close.assert_not_called()

    def test_dismiss_blocking_dialog_does_not_close_request_too_frequent(self):
        dialog = Mock()
        dialog.text = (
            "\u8bf7\u6c42\u8fc7\u4e8e\u9891\u7e41 "
            "\u8bf7\u7a0d\u7b49\u51e0\u5206\u949f\u540e\u518d\u91cd\u8bd5"
        )

        with patch.object(dialogs, "get_visible_dialogs", return_value=[dialog]):
            with self.assertRaises(dialogs.RequestTooFrequentError):
                dialogs.dismiss_blocking_dialog_if_present(Mock())


if __name__ == "__main__":
    unittest.main()

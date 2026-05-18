import unittest
from unittest.mock import Mock

from utils import selenium_utils


class SeleniumUtilsTests(unittest.TestCase):
    def test_normalize_selectors_accepts_string_or_iterable(self):
        self.assertEqual(selenium_utils.normalize_selectors("button"), ["button"])
        self.assertEqual(selenium_utils.normalize_selectors(["a", "b"]), ["a", "b"])

    def test_visible_elements_filters_displayed_elements(self):
        visible = Mock()
        visible.is_displayed.return_value = True
        hidden = Mock()
        hidden.is_displayed.return_value = False

        driver = Mock()
        driver.find_elements.return_value = [hidden, visible]

        self.assertEqual(selenium_utils.visible_elements(driver, "button"), [visible])

    def test_safe_click_falls_back_to_javascript_click(self):
        element = Mock()
        element.click.side_effect = Exception("blocked")
        driver = Mock()

        self.assertTrue(selenium_utils.safe_click(element, driver=driver))

        driver.execute_script.assert_any_call(
            "arguments[0].click();",
            element,
        )


if __name__ == "__main__":
    unittest.main()

import unittest

from examples.image_edit_script.memory.result_detector import detect_request_too_frequent


class ResultDetectorTests(unittest.TestCase):
    def test_detect_request_too_frequent_chinese_dialog(self):
        info = detect_request_too_frequent(
            "\u8bf7\u6c42\u8fc7\u4e8e\u9891\u7e41 "
            "\u4f60\u7684\u8bf7\u6c42\u8fc7\u4e8e\u9891\u7e41\u3002"
            "\u4e3a\u4fdd\u969c\u6570\u636e\u5b89\u5168\uff0c"
            "\u6211\u4eec\u5df2\u6682\u65f6\u9650\u5236\u4f60\u8bbf\u95ee\u5bf9\u8bdd\u8bb0\u5f55\u3002"
        )

        self.assertIsNotNone(info)
        self.assertIn("\u8bf7\u6c42\u8fc7\u4e8e\u9891\u7e41", info["raw_message"])

    def test_detect_request_too_frequent_returns_none_for_regular_text(self):
        self.assertIsNone(detect_request_too_frequent("Response complete"))


if __name__ == "__main__":
    unittest.main()

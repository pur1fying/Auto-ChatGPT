import unittest
from unittest.mock import Mock, patch

from utils.human_delay import HumanDelay, parse_ms_range


class HumanDelayTests(unittest.TestCase):
    def test_parse_ms_range_uses_default_for_invalid_values(self):
        self.assertEqual(parse_ms_range("bad", (1, 2)), (1, 2))
        self.assertEqual(parse_ms_range([None, "x"], (3, 4)), (3, 4))

    def test_parse_ms_range_clamps_and_orders_values(self):
        self.assertEqual(parse_ms_range([500, 100], (1, 2)), (100, 500))
        self.assertEqual(parse_ms_range([-20, 30], (1, 2)), (0, 30))

    def test_from_config_reads_ranges(self):
        config = Mock()

        def get_value(key, default=None):
            values = {
                "human_like_interaction.enabled": True,
                "human_like_interaction.before_send_ms": [10, 20],
            }
            return values.get(key, default)

        config.get.side_effect = get_value

        delay = HumanDelay.from_config(config)

        self.assertTrue(delay.enabled)
        self.assertEqual(delay.ranges["before_send"], (10, 20))

    def test_sleep_noops_when_disabled(self):
        delay = HumanDelay(enabled=False)

        with patch("utils.human_delay.time.sleep") as sleep:
            self.assertEqual(delay.sleep("before_send", "test"), 0)

        sleep.assert_not_called()

    def test_sleep_uses_randomized_ms_range(self):
        delay = HumanDelay(enabled=True, ranges={"before_send": (10, 20)})

        with (
            patch("utils.human_delay.random.randint", return_value=15) as randint,
            patch("utils.human_delay.time.sleep") as sleep,
        ):
            self.assertEqual(delay.sleep("before_send", "test"), 15)

        randint.assert_called_once_with(10, 20)
        sleep.assert_called_once_with(0.015)


if __name__ == "__main__":
    unittest.main()

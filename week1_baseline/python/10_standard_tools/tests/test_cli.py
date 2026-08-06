import io
import unittest
from unittest.mock import patch

import boukensha_cli


class CliTest(unittest.TestCase):
    def test_default_starts_repl(self):
        with patch("boukensha_cli.load_and_start_repl") as start:
            self.assertEqual(0, boukensha_cli.main([], stdout=io.StringIO()))
        start.assert_called_once()

    def test_arguments_do_not_select_a_second_command_surface(self):
        with patch("boukensha_cli.load_and_start_repl") as start:
            self.assertEqual(0, boukensha_cli.main(["--version"], stdout=io.StringIO()))
        start.assert_called_once()


if __name__ == "__main__":
    unittest.main()

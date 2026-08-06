import io
import unittest
from unittest.mock import ANY, patch

import boukensha_cli


class CliTest(unittest.TestCase):
    def test_default_starts_repl(self):
        with patch("boukensha_cli.load_and_start_repl") as start:
            self.assertEqual(0, boukensha_cli.main([], stdout=io.StringIO()))
        start.assert_called_once_with(output=ANY, argv=[])

    def test_no_tui_is_forwarded_to_loader(self):
        with patch("boukensha_cli.load_and_start_repl") as start:
            self.assertEqual(0, boukensha_cli.main(["--no-tui"], stdout=io.StringIO()))
        self.assertEqual(["--no-tui"], start.call_args.kwargs["argv"])

    def test_arguments_do_not_select_a_second_command_surface(self):
        with patch("boukensha_cli.load_and_start_repl") as start:
            self.assertEqual(0, boukensha_cli.main(["--version"], stdout=io.StringIO()))
        self.assertEqual(["--version"], start.call_args.kwargs["argv"])


if __name__ == "__main__":
    unittest.main()

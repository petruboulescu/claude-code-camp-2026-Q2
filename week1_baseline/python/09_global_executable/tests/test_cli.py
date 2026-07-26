import io
import unittest
from unittest.mock import patch

import boukensha_cli


class CliTest(unittest.TestCase):
    def test_version_and_help(self):
        output = io.StringIO()
        self.assertEqual(0, boukensha_cli.main(["--version"], stdout=output))
        self.assertEqual("boukensha 0.9.0\n", output.getvalue())

        output = io.StringIO()
        self.assertEqual(0, boukensha_cli.main(["help"], stdout=output))
        self.assertIn("Usage:", output.getvalue())

    def test_default_starts_repl(self):
        with patch("boukensha_cli.load_and_start_repl") as start:
            self.assertEqual(0, boukensha_cli.main([], stdout=io.StringIO()))
        start.assert_called_once()

    def test_doctor_dispatches(self):
        with patch("boukensha_cli.doctor") as doctor:
            self.assertEqual(0, boukensha_cli.main(["doctor"], stdout=io.StringIO()))
        doctor.assert_called_once()

    def test_unknown_command_fails(self):
        error = io.StringIO()
        self.assertEqual(1, boukensha_cli.main(["wat"], stderr=error))
        self.assertIn("unknown command", error.getvalue())


if __name__ == "__main__":
    unittest.main()

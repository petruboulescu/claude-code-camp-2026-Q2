import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from boukensha import Config


class ConfigDirectoryTest(unittest.TestCase):
    def test_explicit_directory_has_precedence(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            explicit = root / "explicit"
            explicit.mkdir()
            (root / ".boukensha").mkdir()

            with (
                patch.dict(
                    os.environ,
                    {"BOUKENSHA_DIR": str(explicit)},
                    clear=False,
                ),
                patch("pathlib.Path.cwd", return_value=root),
            ):
                config = Config()

        self.assertEqual(config.dir, str(explicit))

    def test_existing_current_directory_config_does_not_precede_home(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            local = root / ".boukensha"
            local.mkdir()
            fallback = root / "home"

            with (
                patch.dict(os.environ, {}, clear=False),
                patch("pathlib.Path.cwd", return_value=root),
                patch.object(Config, "DEFAULT_DIR", str(fallback)),
            ):
                os.environ.pop("BOUKENSHA_DIR", None)
                config = Config()

            self.assertEqual(config.dir, str(fallback))

    def test_home_default_is_used_without_other_directory(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            fallback = root / "home"

            with (
                patch.dict(os.environ, {}, clear=False),
                patch("pathlib.Path.cwd", return_value=root),
                patch.object(Config, "DEFAULT_DIR", str(fallback)),
            ):
                os.environ.pop("BOUKENSHA_DIR", None)
                config = Config()

        self.assertEqual(config.dir, str(fallback))


if __name__ == "__main__":
    unittest.main()

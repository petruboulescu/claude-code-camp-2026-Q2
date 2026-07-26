import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import boukensha_loader


class LoaderTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.rc = self.home / ".boukensharc"

    def tearDown(self):
        self.temp.cleanup()

    def make_step(self, name):
        step = self.home / name
        package = step / "boukensha"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("def repl(): pass\n", encoding="utf-8")
        return step

    def test_mapping_resolves_relative_paths_and_environment_overrides(self):
        rc_step = self.make_step("rc-step")
        env_step = self.make_step("env-step")
        self.rc.write_text(
            "boukensha_path: rc-step\nboukensha_dir: rc-config\n",
            encoding="utf-8",
        )

        implementation, config, _ = boukensha_loader.resolve(
            path=self.rc,
            environ={"BOUKENSHA_PATH": str(env_step), "BOUKENSHA_DIR": str(self.home / "env-config")},
        )

        self.assertEqual(env_step, implementation)
        self.assertEqual(self.home / "env-config", config)
        self.assertNotEqual(rc_step, implementation)

    def test_legacy_string_and_empty_documents(self):
        step = self.make_step("legacy")
        self.rc.write_text("legacy\n", encoding="utf-8")
        implementation, _, _ = boukensha_loader.resolve(path=self.rc, environ={})
        self.assertEqual(step, implementation)

        self.rc.write_text("", encoding="utf-8")
        implementation, _, rc = boukensha_loader.resolve(path=self.rc, environ={})
        self.assertIsNone(implementation)
        self.assertEqual({}, rc)

    def test_invalid_shape_and_missing_package_are_errors(self):
        self.rc.write_text("- bad\n- shape\n", encoding="utf-8")
        with self.assertRaises(boukensha_loader.LoaderError):
            boukensha_loader.load_rc(self.rc)

        self.rc.write_text("boukensha_path: missing\n", encoding="utf-8")
        with self.assertRaisesRegex(boukensha_loader.LoaderError, "boukensha/__init__.py"):
            boukensha_loader.resolve(path=self.rc, environ={})

    def test_doctor_reports_configuration_without_secret(self):
        config = self.home / "config"
        config.mkdir()
        (config / "settings.yaml").write_text(
            "tasks:\n  player:\n    provider: openai\n    model: gpt-test\n",
            encoding="utf-8",
        )
        (config / ".env").write_text("OPENAI_API_KEY=super-secret\n", encoding="utf-8")
        output = io.StringIO()

        with patch.dict(os.environ, {"HOME": str(self.home)}, clear=False):
            boukensha_loader.doctor(
                path=self.rc,
                environ={"BOUKENSHA_DIR": str(config), "PATH": ""},
                output=output,
                executable=str(self.home / "bin" / "boukensha"),
            )

        self.assertIn("provider:           openai", output.getvalue())
        self.assertIn("model:              gpt-test", output.getvalue())
        self.assertIn("credential ready:   yes", output.getvalue())
        self.assertNotIn("super-secret", output.getvalue())

    def test_local_ollama_needs_no_credential(self):
        config = self.home / "config"
        config.mkdir()
        (config / "settings.yaml").write_text(
            "tasks:\n  player:\n    provider: ollama\n",
            encoding="utf-8",
        )
        output = io.StringIO()
        boukensha_loader.doctor(
            path=self.rc,
            environ={"BOUKENSHA_DIR": str(config), "PATH": ""},
            output=output,
            executable=str(self.home / "bin" / "boukensha"),
        )
        self.assertIn("credential ready:   yes", output.getvalue())


if __name__ == "__main__":
    unittest.main()

import os
import pathlib
import sys
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import run_blender  # noqa: E402


class RunBlenderEnvTests(unittest.TestCase):
    def test_sanitized_blender_env_removes_virtualenv_python_overrides(self):
        env = {
            "VIRTUAL_ENV": "/tmp/project/.venv",
            "PYTHONHOME": "/tmp/python-home",
            "PYTHONPATH": "/tmp/python-path",
            "PYTHONSTARTUP": "/tmp/python-startup.py",
            "PYTHONUSERBASE": "/tmp/python-userbase",
            "__PYVENV_LAUNCHER__": "/tmp/launcher",
            "PATH": os.pathsep.join(
                ["/tmp/project/.venv/bin", "/usr/local/bin", "/usr/bin"]
            ),
            "HOME": "/tmp/home",
        }

        sanitized = run_blender._sanitized_blender_env(env)

        for key in (
            "VIRTUAL_ENV",
            "PYTHONHOME",
            "PYTHONPATH",
            "PYTHONSTARTUP",
            "PYTHONUSERBASE",
            "__PYVENV_LAUNCHER__",
        ):
            self.assertNotIn(key, sanitized)

        self.assertEqual(sanitized["HOME"], "/tmp/home")
        self.assertNotIn("/tmp/project/.venv/bin", sanitized["PATH"])
        self.assertIn("/usr/bin", sanitized["PATH"])


if __name__ == "__main__":
    unittest.main()

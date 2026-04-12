import os
import pathlib
import sys
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "rvlib" / "rvlib"))

import runtime_bootstrap  # noqa: E402


class RuntimeBootstrapTests(unittest.TestCase):
    def test_bootstrap_runtime_prioritizes_libpath_and_cwd(self):
        old_sys_path = list(sys.path)
        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            libpath = os.path.join(tmp, "lib")
            cwd = os.path.join(tmp, "cwd")
            os.makedirs(libpath, exist_ok=True)
            os.makedirs(cwd, exist_ok=True)
            try:
                runtime_bootstrap.bootstrap_runtime(libpath, cwd)

                self.assertEqual(sys.path[0], cwd)
                self.assertEqual(sys.path[1], libpath)
                self.assertEqual(os.getcwd(), os.path.realpath(cwd))
            finally:
                sys.path[:] = old_sys_path
                os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()

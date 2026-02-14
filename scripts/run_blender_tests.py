#!/usr/bin/env python3
"""
Run Blender-dependent tests under tests/blender using unittest discovery.

Usage:
  python3 scripts/run_blender.py --background --factory-startup --python scripts/run_blender_tests.py
  python3 scripts/run_blender.py --background --factory-startup --python scripts/run_blender_tests.py -- -k test_scatter
"""

import argparse
import pathlib
import sys
import unittest


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Blender integration tests.")
    parser.add_argument(
        "-k",
        "--pattern",
        default="test*.py",
        help="unittest discovery pattern (default: test*.py)",
    )
    parser.add_argument(
        "-v",
        "--verbosity",
        type=int,
        default=2,
        choices=[0, 1, 2],
        help="unittest verbosity (0, 1, 2)",
    )
    return parser.parse_args(argv)


def main() -> int:
    try:
        import bpy  # noqa: F401
    except Exception as exc:
        print(
            "This runner must be executed inside Blender "
            "(missing bpy module): "
            f"{exc}",
            file=sys.stderr,
        )
        return 2

    repo_root = pathlib.Path(__file__).resolve().parents[1]
    rv_pkg = repo_root / "rvlib" / "rvlib"
    tests_root = repo_root / "tests" / "blender"

    # Blender embeds Python with its own sys.path; add repo paths explicitly.
    sys.path.insert(0, str(repo_root))
    sys.path.insert(0, str(rv_pkg))

    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []
    args = _parse_args(argv)

    suite = unittest.defaultTestLoader.discover(
        start_dir=str(tests_root),
        pattern=args.pattern,
    )
    result = unittest.TextTestRunner(verbosity=args.verbosity).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())

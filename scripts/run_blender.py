#!/usr/bin/env python3
"""
Run Blender using the same binary resolution order as the rv framework:
1) BLENDER_PATH env var
2) blender from PATH
3) platform fallback path
"""

import os
import platform
import shutil
import subprocess
import sys


def _resolve_blender_path() -> str:
    env_path = os.environ.get("BLENDER_PATH", "")
    if env_path and os.path.exists(env_path):
        return env_path

    path_blender = shutil.which("blender")
    if path_blender:
        return path_blender

    system = platform.system().lower()
    if system == "darwin":
        fallback = "/Applications/Blender.app/Contents/MacOS/Blender"
        if os.path.exists(fallback):
            return fallback
    elif system == "windows":
        fallback = r"C:\Program Files\Blender Foundation\Blender\blender.exe"
        if os.path.exists(fallback):
            return fallback

    raise FileNotFoundError("blender executable not found")


def main(argv: list[str]) -> int:
    if len(argv) == 0:
        print(
            "Usage: python3 scripts/run_blender.py <blender-args...>",
            file=sys.stderr,
        )
        return 2

    blender = _resolve_blender_path()
    cmd = [blender, *argv]
    proc = subprocess.run(cmd)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

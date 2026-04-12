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
from typing import Union


_BLOCKED_ENV_KEYS = {
    "PYTHONHOME",
    "PYTHONPATH",
    "PYTHONSTARTUP",
    "PYTHONUSERBASE",
    "VIRTUAL_ENV",
    "__PYVENV_LAUNCHER__",
}


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


def _remove_path_entry(raw_path: str, target: str) -> str:
    if not raw_path or not target:
        return raw_path

    normalized_target = os.path.normpath(target)
    filtered = [
        entry
        for entry in raw_path.split(os.pathsep)
        if os.path.normpath(entry) != normalized_target
    ]
    return os.pathsep.join(filtered)


def _sanitized_blender_env(
    env: Union[dict[str, str], None] = None
) -> dict[str, str]:
    if env is None:
        env = os.environ

    sanitized = {
        key: value for key, value in env.items() if key not in _BLOCKED_ENV_KEYS
    }

    virtual_env = env.get("VIRTUAL_ENV", "").strip()
    if virtual_env and "PATH" in sanitized:
        venv_bin = os.path.join(virtual_env, "bin")
        if platform.system().lower() == "windows":
            venv_bin = os.path.join(virtual_env, "Scripts")
        sanitized["PATH"] = _remove_path_entry(sanitized["PATH"], venv_bin)

    return sanitized


def main(argv: list[str]) -> int:
    if len(argv) == 0:
        print(
            "Usage: python3 scripts/run_blender.py <blender-args...>",
            file=sys.stderr,
        )
        return 2

    blender = _resolve_blender_path()
    cmd = [blender, *argv]
    proc = subprocess.run(cmd, env=_sanitized_blender_env())
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

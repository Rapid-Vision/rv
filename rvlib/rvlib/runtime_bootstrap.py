import os
import sys


def bootstrap_runtime(libpath: str, cwd: str) -> None:
    """
    Configure Python import resolution for embedded Blender runners.

    `cwd` must be importable so scene scripts can import sibling modules
    consistently across render, preview, and export.
    """
    sys.path.insert(0, libpath)
    sys.path.insert(0, cwd)
    os.chdir(cwd)

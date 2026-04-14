import json
from pathlib import Path
from typing import Union
from urllib import error, request

_GENERATOR_URL: Union[str, None] = None
_GENERATOR_CWD = Path.cwd()


def _configure_generator_runtime(port: int, cwd: str) -> None:
    global _GENERATOR_URL, _GENERATOR_CWD

    _GENERATOR_CWD = Path(cwd).expanduser().resolve()
    if port <= 0:
        _GENERATOR_URL = None
        return
    _GENERATOR_URL = f"http://127.0.0.1:{port}/v1/generate"


class GeneratorHandle:
    def __init__(self, scene, command: str) -> None:
        if command is None or str(command).strip() == "":
            raise ValueError("generator command is required.")
        self.scene = scene
        self.command = str(command).strip()

    def generate(self, operation: str, **params) -> str:
        if _GENERATOR_URL is None:
            raise RuntimeError("Generator runtime is not configured.")
        if operation is None or str(operation).strip() == "":
            raise ValueError("generator operation is required.")

        seed = None
        if self.scene.seed is not None:
            seed = int(self.scene.seed)

        payload = {
            "command": self.command,
            "cwd": str(_GENERATOR_CWD),
            "operation": operation,
            "params": params,
            "seed": seed,
            "seed_mode": self.scene.seed_mode,
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            _GENERATOR_URL,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req) as resp:
                raw = resp.read()
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").strip()
            raise RuntimeError(
                f"generator request failed with status {exc.code}: {detail}"
            ) from exc
        except error.URLError as exc:
            raise RuntimeError(f"generator request failed: {exc.reason}") from exc

        response = json.loads(raw.decode("utf-8"))
        path = response.get("path")
        if not isinstance(path, str) or path.strip() == "":
            raise RuntimeError("generator response must include a non-empty path.")
        return path


class GeneratorFactory:
    def __init__(self, scene) -> None:
        self.scene = scene

    def init(self, command: str) -> GeneratorHandle:
        return GeneratorHandle(self.scene, command)

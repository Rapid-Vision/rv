import json
from pathlib import Path
from typing import Any, Union
from urllib import error, request

_GENERATOR_URL: Union[str, None] = None
_GENERATOR_ROOT_DIR = Path.cwd()
_GENERATOR_WORK_DIR = Path.cwd()


def _configure_generator_runtime(port: int, root_dir: str, work_dir: str) -> None:
    global _GENERATOR_URL, _GENERATOR_ROOT_DIR, _GENERATOR_WORK_DIR

    _GENERATOR_ROOT_DIR = Path(root_dir).expanduser().resolve()
    _GENERATOR_WORK_DIR = Path(work_dir).expanduser().resolve()
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

    def _request(self, **params) -> Any:
        if _GENERATOR_URL is None:
            raise RuntimeError("Generator runtime is not configured.")

        seed = None
        if self.scene.seed is not None:
            seed = int(self.scene.seed)

        payload = {
            "command": self.command,
            "root_dir": str(_GENERATOR_ROOT_DIR),
            "work_dir": str(_GENERATOR_WORK_DIR),
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
        if "result" not in response:
            raise RuntimeError("generator response must include result.")
        return response["result"]

    def generate(self, **params) -> Any:
        return self._request(**params)

    def generate_path(self, **params) -> str:
        result = self._request(**params)
        if not isinstance(result, str) or result.strip() == "":
            raise RuntimeError("generator result must be a non-empty path string.")

        path = Path(result)
        if not path.is_absolute():
            path = _GENERATOR_WORK_DIR / path
        path = path.expanduser().resolve()
        if not path.exists():
            raise RuntimeError(f"generated path does not exist: {path}")
        return str(path)

    def generate_str(self, **params) -> str:
        result = self._request(**params)
        if not isinstance(result, str):
            raise RuntimeError("generator result must be a string.")
        return result

    def generate_num(self, **params) -> float:
        result = self._request(**params)
        if isinstance(result, bool) or not isinstance(result, (int, float)):
            raise RuntimeError("generator result must be a number.")
        return float(result)


class GeneratorFactory:
    def __init__(self, scene) -> None:
        self.scene = scene

    def init(self, command: str) -> GeneratorHandle:
        return GeneratorHandle(self.scene, command)

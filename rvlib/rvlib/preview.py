import inspect
import os
import bpy
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import sys
import argparse
import signal
import importlib.util
import traceback
import shutil
import time
import tempfile

CLASS_COUNT_ERROR_MESSAGE = """ERROR: exactly one class derived from rv.Scene must be defined.
Example usage:

import rv
class MyScene(rv.Scene):
    def generate(self):
        pass
"""

VALID_GPU_BACKENDS = ("auto", "optix", "cuda", "hip", "oneapi", "metal", "cpu")


def parse_args():
    args = []
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1 :]

    parser = argparse.ArgumentParser(description="Embedded blender server for rv tool")
    parser.add_argument("--port", type=int, default=5757)
    parser.add_argument("--script", type=str)
    parser.add_argument("--libpath", type=str)
    parser.add_argument("--cwd", type=str)
    parser.add_argument("--preview-files", type=parse_bool, default=False)
    parser.add_argument("--preview-out", type=str, default=None)
    parser.add_argument("--no-window", type=parse_bool, default=False)
    parser.add_argument("--resolution", type=str, default="640,640")
    parser.add_argument("--gpu-backend", type=str, default="auto")
    parser.add_argument("--time-limit", type=float, default=None)

    return parser.parse_args(args)


def parse_bool(raw):
    if isinstance(raw, bool):
        return raw
    value = str(raw).strip().lower()
    if value in ("true", "1", "yes", "y", "on"):
        return True
    if value in ("false", "0", "no", "n", "off"):
        return False
    raise ValueError("boolean flag value must be true or false")


def parse_resolution(raw):
    parts = [part.strip() for part in raw.split(",")]
    if len(parts) != 2:
        raise ValueError("--resolution must be WIDTH,HEIGHT")
    width = int(parts[0])
    height = int(parts[1])
    if width <= 0 or height <= 0:
        raise ValueError("--resolution width and height must be > 0")
    return (width, height)


def iter_cycles_devices(preferences):
    devices = getattr(preferences, "devices", None)
    if devices:
        return list(devices)

    get_devices = getattr(preferences, "get_devices", None)
    if callable(get_devices):
        groups = get_devices() or []
        flattened = []
        for group in groups:
            if group:
                flattened.extend(group)
        return flattened

    return []


def configure_cycles_backend(requested_backend):
    scene = bpy.context.scene
    scene.cycles.device = "GPU"

    try:
        preferences = bpy.context.preferences.addons["cycles"].preferences
    except KeyError as exc:
        raise RuntimeError("Cycles add-on preferences are unavailable") from exc

    refresh_devices = getattr(preferences, "refresh_devices", None)
    if callable(refresh_devices):
        refresh_devices()

    requested = requested_backend.strip().lower()
    if requested not in VALID_GPU_BACKENDS:
        raise ValueError(
            "--gpu-backend must be one of auto, optix, cuda, hip, oneapi, metal, cpu"
        )

    available_types = {device.type for device in iter_cycles_devices(preferences)}
    if requested == "auto":
        for backend in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL"):
            if backend in available_types:
                requested = backend.lower()
                break
        else:
            requested = "cpu"

    if requested == "cpu":
        scene.cycles.device = "CPU"
        return "CPU"

    selected_type = requested.upper()
    if selected_type not in available_types:
        available = sorted(available_types) or ["CPU"]
        raise RuntimeError(
            f"Requested GPU backend {selected_type} is unavailable. "
            f"Available device types: {', '.join(available)}"
        )

    preferences.compute_device_type = selected_type
    if callable(refresh_devices):
        refresh_devices()

    enabled_gpu = False
    for device in iter_cycles_devices(preferences):
        is_matching_gpu = device.type == selected_type
        if hasattr(device, "use"):
            device.use = is_matching_gpu
        if is_matching_gpu:
            enabled_gpu = True

    if not enabled_gpu:
        raise RuntimeError(f"Requested GPU backend {selected_type} found no enabled devices")

    scene.cycles.device = "GPU"
    return selected_type


def print_cycles_device_info():
    scene = bpy.context.scene
    print(f"[rv] engine={scene.render.engine}")
    print(f"[rv] cycles_device={scene.cycles.device}")

    try:
        preferences = bpy.context.preferences.addons["cycles"].preferences
    except KeyError:
        print("[rv] cycles_preferences=unavailable")
        return

    refresh_devices = getattr(preferences, "refresh_devices", None)
    if callable(refresh_devices):
        refresh_devices()

    print(
        f"[rv] compute_device_type={getattr(preferences, 'compute_device_type', None)}"
    )

    devices = iter_cycles_devices(preferences)
    if not devices:
        print("[rv] devices=[]")
        return

    serialized_devices = [
        {
            "name": device.name,
            "type": device.type,
            "use": getattr(device, "use", None),
        }
        for device in devices
    ]
    print(f"[rv] devices={serialized_devices}")


def register_quit():
    def quit_blender():
        bpy.ops.wm.quit_blender()
        return None

    bpy.app.timers.register(quit_blender)


RERUN_PENDING = False
RERUN_RUNNING = False
HTTPD = None
STOP_EVENT = threading.Event()


def iter_files(root_dir):
    for base, _, files in os.walk(root_dir):
        for filename in files:
            full_path = os.path.join(base, filename)
            rel_path = os.path.relpath(full_path, root_dir)
            yield rel_path, full_path


def cleanup_empty_dirs(root_dir):
    for base, dirs, files in os.walk(root_dir, topdown=False):
        if base == root_dir:
            continue
        if not dirs and not files:
            try:
                os.rmdir(base)
            except OSError:
                pass


def replace_preview_output(staging_dir, preview_out):
    os.makedirs(preview_out, exist_ok=True)

    staged_files = set()
    for rel_path, staged_full_path in iter_files(staging_dir):
        staged_files.add(rel_path)
        target_path = os.path.join(preview_out, rel_path)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(staged_full_path, "rb") as src:
            data = src.read()
        with open(target_path, "wb") as dst:
            dst.write(data)

    # Remove files that are no longer produced by the latest render.
    existing_files = []
    for rel_path, existing_full_path in iter_files(preview_out):
        existing_files.append((rel_path, existing_full_path))
    for rel_path, existing_full_path in existing_files:
        if rel_path not in staged_files:
            try:
                os.remove(existing_full_path)
            except FileNotFoundError:
                pass

    cleanup_empty_dirs(preview_out)


def reset_preview_scene_state():
    scene = bpy.context.scene
    scene.frame_set(int(scene.frame_start))
    bpy.context.view_layer.update()

    if scene.rigidbody_world is not None:
        try:
            bpy.ops.object.select_all(action="DESELECT")
            bpy.ops.rigidbody.world_remove()
        except Exception:
            pass

    scene.frame_set(int(scene.frame_start))
    bpy.context.view_layer.update()


def run_script(
    script_path,
    preview_files=False,
    preview_out=None,
    resolution=(640, 640),
    gpu_backend="auto",
    time_limit=None,
):
    spec = importlib.util.spec_from_file_location("dynamic_module", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    import rv

    scene_classes = []
    for _, obj in inspect.getmembers(module, inspect.isclass):
        if issubclass(obj, rv.Scene) and obj is not rv.Scene:
            scene_classes.append(obj)

    if len(scene_classes) != 1:
        print(CLASS_COUNT_ERROR_MESSAGE)
        return

    reset_preview_scene_state()
    rv._internal_begin_run(purge_orphans=True)
    if preview_files:
        os.makedirs(preview_out, exist_ok=True)
        staging_parent = os.path.dirname(preview_out) or "."
        staging_dir = tempfile.mkdtemp(prefix=".rv_preview_stage_", dir=staging_parent)
        instance = scene_classes[0](staging_dir)
        instance.subdir = ""
        instance.resolution = resolution
        if time_limit is not None:
            if time_limit <= 0:
                raise ValueError("--time-limit must be > 0")
            instance.time_limit = time_limit
    else:
        staging_dir = None
        instance = scene_classes[0]()
    try:
        instance.generate()
        instance._internal_post_gen()
        selected_backend = configure_cycles_backend(gpu_backend)
        print(f"[rv] selected_gpu_backend={selected_backend}")
        print_cycles_device_info()
        if preview_files:
            instance._internal_render()
    finally:
        rv._internal_end_run(purge_orphans=False)

    if preview_files:
        try:
            replace_preview_output(staging_dir, preview_out)
        finally:
            shutil.rmtree(staging_dir, ignore_errors=True)


def request_rerun():
    global RERUN_PENDING
    RERUN_PENDING = True


def preview_tick():
    global RERUN_PENDING, RERUN_RUNNING

    if RERUN_RUNNING or not RERUN_PENDING:
        return 0.1

    RERUN_RUNNING = True
    RERUN_PENDING = False
    try:
        run_script(
            ARGS.script,
            preview_files=ARGS.preview_files,
            preview_out=ARGS.preview_out,
            resolution=RESOLUTION,
            gpu_backend=ARGS.gpu_backend,
            time_limit=ARGS.time_limit,
        )
    except Exception:
        print("ERROR: Failed to execute preview run")
        traceback.print_exc()
    finally:
        RERUN_RUNNING = False

    return 0.1


def run_command(path, body):
    if path == "/rerun":
        request_rerun()


class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        path = self.path
        content_length = int(self.headers.get("Content-Length", 0))
        json_body = None
        if content_length > 0:
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                json_body = json.loads(body)
            except json.JSONDecodeError:
                self.send_response(400)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", 0)
                self.end_headers()
                return

        run_command(path, json_body)
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", 0)
        self.end_headers()


def run_server():
    global HTTPD
    try:
        server_address = ("127.0.0.1", ARGS.port)
        HTTPD = HTTPServer(server_address, RequestHandler)
        print(f"HTTP server running at http://127.0.0.1:{ARGS.port}")
        HTTPD.serve_forever()
    finally:
        if not ARGS.no_window:
            register_quit()


def sig_handler(signum, frame):
    STOP_EVENT.set()
    if HTTPD is not None:
        HTTPD.shutdown()
    if not ARGS.no_window:
        register_quit()


def run_headless_loop():
    request_rerun()
    while not STOP_EVENT.is_set():
        if RERUN_PENDING and not RERUN_RUNNING:
            preview_tick()
            continue
        time.sleep(0.1)


ARGS = parse_args()
RESOLUTION = parse_resolution(ARGS.resolution)

if ARGS.no_window and not ARGS.preview_files:
    raise ValueError("--no-window requires --preview-files")

if ARGS.preview_files and not ARGS.preview_out:
    raise ValueError("--preview-out is required when --preview-files=true")

signal.signal(signal.SIGINT, sig_handler)
signal.signal(signal.SIGTERM, sig_handler)

sys.path.append(ARGS.libpath)
os.chdir(ARGS.cwd)
server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

if ARGS.no_window:
    run_headless_loop()
else:
    request_rerun()
    bpy.app.timers.register(preview_tick)

print("Blender is running with an embedded HTTP server.")

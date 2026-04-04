import os
import bpy
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import sys
import argparse
import signal
import traceback
import shutil
import time
import tempfile

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from runtime_bootstrap import bootstrap_runtime


def parse_args():
    args = []
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1 :]

    parser = argparse.ArgumentParser(description="Embedded blender server for rv tool")
    parser.add_argument("--port", type=int, default=5757)
    parser.add_argument("--script", type=str)
    parser.add_argument("--libpath", type=str)
    parser.add_argument("--cwd", type=str)
    parser.add_argument("--preview-files", action="store_true")
    parser.add_argument("--preview-out", type=str, default=None)
    parser.add_argument("--no-window", action="store_true")
    parser.add_argument("--resolution", type=str, default="640,640")
    parser.add_argument("--gpu-backend", type=str, default="auto")
    parser.add_argument("--seed-mode", type=str, default="rand")
    parser.add_argument("--seed-value", type=int, default=None)
    parser.add_argument("--time-limit", type=float, default=None)

    return parser.parse_args(args)


def register_quit():
    def quit_blender():
        bpy.ops.wm.quit_blender()
        return None

    bpy.app.timers.register(quit_blender)


RERUN_PENDING = False
RERUN_RUNNING = False
HTTPD = None
STOP_EVENT = threading.Event()
RERUN_INDEX = 0


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
    seed=None,
):
    import rv
    import rv.internal as rvi

    scene_class = rvi._internal_load_scene_class(script_path)

    reset_preview_scene_state()
    rvi._internal_begin_run(purge_orphans=True)
    if preview_files:
        os.makedirs(preview_out, exist_ok=True)
        staging_parent = os.path.dirname(preview_out) or "."
        staging_dir = tempfile.mkdtemp(prefix=".rv_preview_stage_", dir=staging_parent)
        instance = scene_class(staging_dir)
        instance.subdir = ""
        instance.resolution = resolution
    else:
        staging_dir = None
        instance = scene_class()
        instance.resolution = resolution
    rvi._internal_set_time_limit(instance, time_limit)
    try:
        rvi._internal_run_scene_generate(instance, seed, ARGS.seed_mode)
        instance._internal_post_gen()
        selected_backend = rvi._internal_configure_cycles_backend(gpu_backend)
        print(f"[rv] selected_gpu_backend={selected_backend}")
        rvi._internal_print_cycles_device_info()
        if preview_files:
            instance._internal_render()
    finally:
        rvi._internal_end_run(purge_orphans=False)

    if preview_files:
        try:
            replace_preview_output(staging_dir, preview_out)
        finally:
            shutil.rmtree(staging_dir, ignore_errors=True)


def request_rerun():
    global RERUN_PENDING
    RERUN_PENDING = True


def preview_tick():
    global RERUN_PENDING, RERUN_RUNNING, RERUN_INDEX

    if RERUN_RUNNING or not RERUN_PENDING:
        return 0.1

    RERUN_RUNNING = True
    RERUN_PENDING = False
    try:
        seed = rvi._internal_resolve_seed(
            ARGS.seed_mode, ARGS.seed_value, 0, RERUN_INDEX
        )
        run_script(
            ARGS.script,
            preview_files=ARGS.preview_files,
            preview_out=ARGS.preview_out,
            resolution=RESOLUTION,
            gpu_backend=ARGS.gpu_backend,
            time_limit=ARGS.time_limit,
            seed=seed,
        )
        RERUN_INDEX += 1
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

bootstrap_runtime(ARGS.libpath, ARGS.cwd)

import rv
import rv.internal as rvi

RESOLUTION = rvi._internal_parse_resolution(ARGS.resolution)

if ARGS.no_window and not ARGS.preview_files:
    raise ValueError("--no-window requires --preview-files")

if ARGS.preview_files and not ARGS.preview_out:
    raise ValueError("--preview-out is required when --preview-files=true")

signal.signal(signal.SIGINT, sig_handler)
signal.signal(signal.SIGTERM, sig_handler)

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

if ARGS.no_window:
    run_headless_loop()
else:
    request_rerun()
    bpy.app.timers.register(preview_tick)

print("Blender is running with an embedded HTTP server.")

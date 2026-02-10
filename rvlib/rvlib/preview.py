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

CLASS_COUNT_ERROR_MESSAGE = """ERROR: exactly one class derived from rv.Scene must be defined.
Example usage:

import rv
class MyScene(rv.Scene):
    def generate(self):
        pass
"""


def parse_args():
    args = []
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1 :]

    parser = argparse.ArgumentParser(description="Embedded blender server for rv tool")
    parser.add_argument("--port", type=int, default=5757)
    parser.add_argument("--script", type=str)
    parser.add_argument("--libpath", type=str)
    parser.add_argument("--cwd", type=str)

    return parser.parse_args(args)


def register_quit():
    def quit_blender():
        bpy.ops.wm.quit_blender()
        return None

    bpy.app.timers.register(quit_blender)


RERUN_PENDING = False
RERUN_RUNNING = False


def run_script(script_path):
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

    rv.begin_run(purge_orphans=True)
    instance = scene_classes[0]()
    instance.generate()
    instance._post_gen()
    rv.end_run(purge_orphans=False)


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
        run_script(ARGS.script)
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
    try:
        server_address = ("127.0.0.1", ARGS.port)
        httpd = HTTPServer(server_address, RequestHandler)
        print(f"HTTP server running at http://127.0.0.1:{ARGS.port}")

        httpd.serve_forever()
    finally:
        register_quit()


def sig_handler(signum, frame):
    register_quit()


ARGS = parse_args()

signal.signal(signal.SIGINT, sig_handler)

sys.path.append(ARGS.libpath)
os.chdir(ARGS.cwd)
request_rerun()
bpy.app.timers.register(preview_tick)

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

print("Blender is running with an embedded HTTP server.")

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
PACKAGED_EDITOR_DIR = SKILL_DIR / "assets" / "editor"
DEFAULT_PORT = 4321


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Enable the bundled Swiss Style Web PPT visual editor inside a deck project."
    )
    parser.add_argument(
        "--project",
        default=".",
        help="Deck project directory. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Local editor port. Defaults to {DEFAULT_PORT}.",
    )
    parser.add_argument(
        "--launch",
        action="store_true",
        help="Start the local editor server when it is not already running.",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the editor page in the default browser.",
    )
    return parser.parse_args()


def copy_editor_assets(project_dir: Path) -> Path:
    target_dir = project_dir / "editor"
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(PACKAGED_EDITOR_DIR, target_dir, dirs_exist_ok=True)
    return target_dir


def probe(url: str, timeout: float = 0.6) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 500
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        return False


def wait_until_ready(url: str, timeout_seconds: float = 8.0) -> bool:
    started = time.time()
    while time.time() - started < timeout_seconds:
        if probe(url):
            return True
        time.sleep(0.25)
    return False


def launch_server(project_dir: Path, editor_dir: Path, port: int) -> tuple[bool, Path]:
    editor_url = f"http://127.0.0.1:{port}/editor/"
    log_path = editor_dir / ".server.log"

    if probe(editor_url):
        return True, log_path

    node_bin = shutil.which("node")
    if not node_bin:
        raise RuntimeError("`node` is required to launch the web PPT editor.")

    env = os.environ.copy()
    env["PORT"] = str(port)

    with log_path.open("ab") as log_file:
        subprocess.Popen(
            [node_bin, str(editor_dir / "server.mjs")],
            cwd=str(project_dir),
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    if not wait_until_ready(editor_url):
        raise RuntimeError(
            f"Editor server did not become ready on port {port}. Check log: {log_path}"
        )

    return False, log_path


def main() -> int:
    args = parse_args()

    if not PACKAGED_EDITOR_DIR.exists():
        print(f"Packaged editor not found: {PACKAGED_EDITOR_DIR}", file=sys.stderr)
        return 1

    project_dir = Path(args.project).expanduser().resolve()
    if not project_dir.exists() or not project_dir.is_dir():
        print(f"Project directory does not exist: {project_dir}", file=sys.stderr)
        return 1

    editor_dir = copy_editor_assets(project_dir)
    editor_url = f"http://127.0.0.1:{args.port}/editor/"
    index_files = sorted(path.name for path in project_dir.glob("index*.html"))

    print(f"[OK] Editor synced to {editor_dir}")
    if index_files:
        print(f"[OK] Deck files: {', '.join(index_files)}")
    else:
        print("[WARN] No `index*.html` files found yet; the editor will open but may not list a deck.")

    if args.launch:
        already_running, log_path = launch_server(project_dir, editor_dir, args.port)
        if already_running:
            print(f"[OK] Reusing running editor server: {editor_url}")
        else:
            print(f"[OK] Editor server started: {editor_url}")
        print(f"[OK] Server log: {log_path}")
    elif args.open and not probe(editor_url):
        print(
            f"[WARN] Editor server is not running on {editor_url}. Add `--launch` to start it automatically."
        )

    if args.open:
        webbrowser.open(editor_url)
        print(f"[OK] Browser open requested: {editor_url}")
    else:
        print(f"[OK] Editor URL: {editor_url}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Starts the stack once per test session: the real backend (rule-based LLM, offline) and the
real React UI (production build served by `vite preview`, which proxies /api exactly like
nginx does in Docker), plus a second UI pointed at a dead backend for the offline case."""

import os
import shutil
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
import requests
from playwright.sync_api import Browser, Page, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for(url: str, proc: subprocess.Popen, timeout: float = 90) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"{proc.args} exited with code {proc.returncode}")
        try:
            if requests.get(url, timeout=1).ok:
                return
        except requests.RequestException:
            pass
        time.sleep(0.5)
    raise TimeoutError(f"{url} did not come up")


def _npx() -> str:
    npx = shutil.which("npx")
    if not npx:
        raise RuntimeError("Node.js is required for the e2e suite (npx not found)")
    return npx


@pytest.fixture(scope="session")
def frontend_build() -> None:
    """Build the React app once (skip with E2E_SKIP_BUILD=1 when dist/ is fresh)."""
    frontend = ROOT / "frontend"
    if not (frontend / "node_modules").exists():
        raise RuntimeError("Run `npm ci` in frontend/ first")
    if os.environ.get("E2E_SKIP_BUILD") != "1":
        subprocess.run([_npx(), "vite", "build"], cwd=frontend, check=True, capture_output=True)


def _start_ui(backend_url: str) -> tuple[subprocess.Popen, str]:
    port = _free_port()
    env = {**os.environ, "BACKEND_URL": backend_url, "ADMIN_TOKEN": ""}
    cmd = [_npx(), "vite", "preview", "--host", "127.0.0.1", "--port", str(port), "--strictPort"]
    proc = subprocess.Popen(cmd, cwd=ROOT / "frontend", env=env, stdout=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}"
    _wait_for(url, proc)
    return proc, url


@pytest.fixture(scope="session")
def data_dir(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("omnicare-e2e")


@pytest.fixture(scope="session")
def backend_url(data_dir: Path) -> Iterator[str]:
    port = _free_port()
    cmd = [
        sys.executable,
        str(HERE / "server.py"),
        "--port",
        str(port),
        "--data-dir",
        str(data_dir),
    ]
    proc = subprocess.Popen(cmd)
    url = f"http://127.0.0.1:{port}"
    try:
        _wait_for(f"{url}/api/v1/health", proc)
        yield url
    finally:
        proc.terminate()


@pytest.fixture(scope="session")
def app_url(backend_url: str, frontend_build: None) -> Iterator[str]:
    proc, url = _start_ui(backend_url)
    yield url
    proc.terminate()


@pytest.fixture(scope="session")
def offline_app_url(frontend_build: None) -> Iterator[str]:
    proc, url = _start_ui(f"http://127.0.0.1:{_free_port()}")  # nothing listens there
    yield url
    proc.terminate()


@pytest.fixture(scope="session")
def browser() -> Iterator[Browser]:
    with sync_playwright() as pw:
        b = pw.chromium.launch(
            headless=os.environ.get("HEADED") != "1",
            args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"],
        )
        yield b
        b.close()


@pytest.fixture
def page(browser: Browser, app_url: str) -> Iterator[Page]:
    """A fresh browser context (empty storage, new conversation) per test."""
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    context.grant_permissions(["microphone"])
    page = context.new_page()
    page.set_default_timeout(20_000)
    page.goto(app_url)
    page.get_by_test_id("intro").wait_for()
    yield page
    context.close()

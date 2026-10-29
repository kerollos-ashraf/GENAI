"""Polling folder watcher: calls `on_change` whenever `signature()` changes.

Polling (rather than OS file events) is deliberate: it works on Docker bind mounts on
Windows/macOS, where inotify events from the host don't reach the container.
"""

import logging
import threading
from collections.abc import Callable, Hashable

logger = logging.getLogger(__name__)


class FolderWatcher:
    def __init__(
        self, signature: Callable[[], Hashable], on_change: Callable[[], object], interval: float
    ) -> None:
        self._signature = signature
        self._on_change = on_change
        self._interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._interval <= 0 or self._thread:
            return
        self._thread = threading.Thread(target=self._run, name="kb-watcher", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def _run(self) -> None:
        # No baseline: the first poll always syncs once (cheap - unchanged files are skipped by
        # content hash). Snapshotting here instead would race with files written right after
        # start() and could miss them forever.
        last: Hashable | None = None
        while not self._stop.wait(self._interval):
            try:
                current = self._signature()
                if current != last:
                    self._on_change()
                    last = current
            except Exception:  # never let the watcher die
                logger.exception("Folder watcher failed")

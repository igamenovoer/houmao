"""Reentrant process/thread serialization for offline membership and private reads."""

from __future__ import annotations

from contextlib import contextmanager
import fcntl
from pathlib import Path
import threading
from typing import Iterator, TextIO

_LOCKS_GUARD = threading.Lock()
_LOCKS: dict[Path, threading.RLock] = {}
_LOCAL = threading.local()


@contextmanager
def offline_authority_lock(mailbox_root: Path) -> Iterator[None]:
    """Prevent release/reassignment from overlapping an admitted member operation.

    Every membership writer participates. The lock is reentrant within a thread
    so service operations may invoke registration helpers without reacquiring an
    OS lock on a different descriptor. OS ownership releases locks after crashes.
    """

    root = mailbox_root.resolve()
    with _LOCKS_GUARD:
        lock = _LOCKS.setdefault(root, threading.RLock())
    with lock:
        held: dict[Path, TextIO] = getattr(_LOCAL, "held", {})
        if root in held:
            yield
            return
        root.mkdir(parents=True, exist_ok=True)
        with (root / ".authority.lock").open("a+") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            held[root] = handle
            _LOCAL.held = held
            try:
                yield
            finally:
                del held[root]
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

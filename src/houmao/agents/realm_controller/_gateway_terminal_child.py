"""Acquire the browser attachment's controlling terminal and exec tmux."""

from __future__ import annotations

import fcntl
import os
import sys
import termios


def main() -> None:
    """Use the PTY slave inherited from the gateway after the child calls setsid."""

    try:
        fcntl.ioctl(0, termios.TIOCSCTTY, 0)
        os.execv(sys.argv[1], sys.argv[1:])
    except OSError:
        # The gateway verifies attachment before sending any child output.
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()

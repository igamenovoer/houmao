# orphan

## Purpose
External repositories/checkouts not tracked as project dependencies.

## Current Contents
- `asciinema/`: shallow source checkout of `https://github.com/asciinema/asciinema.git` for local reference and inspection.
- `bin/`: local executable drop directory for standalone reference tools.
- `bin/asciinema-x86_64-unknown-linux-gnu`: standalone Linux x86_64 executable from asciinema v3.2.1.
- `bin/asciinema-aarch64-unknown-linux-gnu`: standalone Linux aarch64 executable from asciinema v3.2.1. The `pixi run asciinema` task dispatches to the host architecture via `uname -m`.
- `codex/`: local source checkout of `https://github.com/openai/codex.git` for local reference and inspection.
- `cypht/`: shallow source checkout of `https://github.com/cypht-org/cypht.git` for local reference and inspection.
- `filestash/`: local source checkout of `https://github.com/mickael-kerjean/filestash` for local reference and inspection.
- `kimi-code/`: shallow source checkout of `https://github.com/MoonshotAI/kimi-code.git` for local reference and inspection (TUI parsing investigation).
- `libtmux/`: shallow source checkout of `https://github.com/tmux-python/libtmux` for local reference and inspection.
- `promptfoo/`: shallow source checkout of `https://github.com/promptfoo/promptfoo.git` for local reference and inspection.
- `RxPY/`: shallow source checkout of `https://github.com/ReactiveX/RxPY.git` for local reference and inspection (reactive streams reference for tracker sessions).
- `stalwart/`: shallow source checkout of `https://github.com/stalwartlabs/stalwart.git` for local reference and inspection.

## Notes
- Content in this directory is intentionally ignored by Git except for this README and `.gitignore`.
- Treat these files as local reference artifacts rather than managed project dependencies.

# Terminal Record Tool

This directory provides the repo-local wrapper for the terminal recorder described in [docs/reference/terminal_record.md](/data1/huangzhe/code/houmao/docs/reference/terminal_record.md).

Run it from the repository root with Pixi:

```bash
pixi run python -m tools.terminal_record start --mode active --target-session AGENTSYS-gpu --tool codex
```

The wrapper forwards to [`houmao.terminal_record.service`](/data1/huangzhe/code/houmao/src/houmao/terminal_record/service.py) so the same CLI is available through either module path.

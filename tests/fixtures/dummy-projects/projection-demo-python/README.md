# projection-demo-python

Tiny tracked Python project for interactive shadow-state validation demos.

Use this fixture when the goal is to watch `shadow_only` parser and lifecycle state change during manual Claude Code and Codex interaction, not to exercise large-repository discovery.

Suggested live exercises:

- ask the agent to explain `projection_demo/formatting.py`
- ask it to add a small helper to `projection_demo/checks.py`
- open slash-command or selection-menu surfaces and watch the monitor show `waiting`
- trigger an approval or confirmation surface and watch `blocked`
- submit a short code-edit prompt and watch `in_progress -> candidate_complete -> completed`

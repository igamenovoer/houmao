"""Campaign tooling for the kimi-code 2.1.x TUI parsing debug campaign.

Supports ``context/campaigns/debug/2026-10-10-kimi-code-tui-parsing/``
iteration 1: recorded 5 fps state-matrix captures of kimi-code 2.1.1,
blind-labeled ground truth, and replay of the current detector plus a
monkey-patched 2.1.x candidate detector. Nothing here mutates ``src/houmao/``;
candidate behavior is applied through runtime monkey patches only.
"""

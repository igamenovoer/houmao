# Use Cases

This directory contains use cases for comprehensive and long-horizon TUI state-tracking qualification.

## Index

| ID | Use Case | Status |
| --- | --- | --- |
| [UC-01](uc-01-qualify-tui-state-tracking-robustness.md) | Qualify TUI State Tracking Robustness | Kimi 0.23.x qualified; Codex 0.144.x and stress execution blocked by external model timeouts |

## Notes

- The plan targets the maintained Claude Code, Codex, and Kimi Code tracker profiles.
- Provider-visible network and LLM API failures are excluded from live scenario coverage because they cannot be induced reliably. Every live provider session uses the maintained `unattended` launch posture. Avoidable confirmation, approval, permission, trust, update, login, session-picker, browser, and user-question prompts are forbidden test outcomes rather than required stimuli.
- A prompt may receive scripted intervention only when provider/version-specific evidence proves that the CLI hard-codes it and exposes no CLI argument, configuration key, environment variable, prepared state, or other supported bypass. Such exceptions are declared before execution in an intervention allowlist and receive a distinct `pass_with_unavoidable_intervention` verdict.
- Locally controllable transport, process, parser, interruption, terminal-failure, and unknown-to-stalled states remain in scope. Approval and waiting-for-operator states are covered by negative live assertions and synthetic/replay fixtures unless an allowlisted unavoidable prompt makes them reachable under `unattended` mode.
- Canonical recordings use approximately 20 fps capture. Lower and irregular replay cadences use semantic transition contracts when exact sample equality is no longer meaningful.

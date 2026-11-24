# Kimi Native Config Verification

## Live Kimi Web

Kimi Code 2.7.2 ran a managed Web fixture using the self-hosted `Qwen/Qwen3.8-27B-FP8` model at `http://127.0.0.1:14888/v1`. The fixture's private credential TOML was the only source for the `low`, `medium`, `high`, `xhigh` effort catalog. Its project profile selected reasoning level 4.

- The native config API reported all four labels and selected `xhigh`. The materialized config had mode `0600`.
- The native provider process, owning tmux session, and an ordinary pane omitted config-owned environment bindings. A deliberately seeded stale value in the isolated server and a peer session stayed in those locations.
- A prompt submitted through the managed gateway completed. Exact relaunch retained the native session and effort, and the environment checks passed again.
- The managed stop succeeded. Removing the qualification peer left the isolated tmux server with no sessions.

## Automated Verification

- 224 tests passed in the focused Kimi ACP, Web, TUI, headless, model-mapping, launch-plan, and isolated tmux suites.
- 222 tests passed in the brain builder, reasoning, forced-launch preflight, headless turns, Kimi hook, ACP, and tmux command suites.
- 110 tests passed in the fixture, maintained Kimi demo, and fixture-consumer suites. Nine Kimi fixture subprocess integration cases also passed.
- The credential and project command suites passed 158 tests with 13 skips. The packaged Kimi guidance checks passed all three tests.
- `pixi run test` passed with 5,258 tests and 14 skips.
- `pixi run lint`, `pixi run typecheck`, `git diff --check`, and `openspec validate use-native-kimi-config --strict` passed.

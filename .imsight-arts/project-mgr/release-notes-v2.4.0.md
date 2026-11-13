# Houmao 2.4.0

CLI hook observation channel: Claude Code, Codex, and Kimi Code hooks now feed a live activity-posture signal into managed launch, TUI tracking, gateway admission, and recorder replay.

## Changes

### Added

- **CLI hook observation channel**: a new `hook_observation` core package (collector, emitter, settings generator) turns CLI tool hooks into a live activity-posture signal, injected as a managed-home settings merge. Hook observation is wired into managed launch, tracker merge, and recorder replay, and hook posture gates now feed gateway admission and passive observation surfaces.
- **Claude hook observation adapter**: Claude Code hooks feed the channel, qualified by a recorded debug campaign and a documented live smoke run.
- **Codex hook observation adapter**: Codex hooks feed the channel, with tracking and launch reference coverage and a managed-path live smoke harness.
- **Kimi hook observation adapter**: a Kimi hooks generator, normalizer, and reducer rules feed the channel, gated by Kimi install path and enablement checks, wired into managed launch and launch policy, and merged into TUI tracked state, with a managed-path live smoke harness and tracking, launch, and signal reference coverage.

### Fixed

- **TUI interrupt override and hook latch correctness**: the TUI interrupt override is constrained by turn epoch, collector stop is detected, and the hook latch persists through staleness.

### Docs

- Archived the `add-cli-hook-observation-channel`, `add-codex-hook-observation`, and `add-kimi-hook-observation` OpenSpec changes and synced their delta specs into the main specs; published the Claude and Codex hook observation debug campaigns under `context/campaigns/`.

## Notes

- Minor-segment bump for the hook observation channel and its three CLI adapters, each qualified by live managed-path smoke harnesses.
- Publishing this release triggers the `pypi-release.yml` PyPI publication, the `docs.yml` GitHub Pages deployment, and the houmao-skills mirror sync, which publishes the matching `v2.4.0` tag in `igamenovoer/houmao-skills` and advances its stable `main`.
- Pre-publish validation: `ruff check` passed; `python -m build` produced `houmao-2.4.0` wheel and sdist and `twine check` passed on both; the unit suite passed 3039 tests with 1 pre-existing failure (`test_agents_gateway_prompt_rejects_removed_force_option`, a Click error-message format drift that also fails on the unmodified pre-release tree and is unchanged from `v2.3.0`); `mypy src` reports 9 pre-existing errors (redundant casts and unused `type: ignore` comments in `managed_launch_force.py`, `managed_prompt_header.py`, `system_skill_version.py`, and `launch_policy/engine.py`), the identical set reported at the `v2.3.0` tag. This release ships with that known status rather than expanding the release diff.
- Full changelog: [CHANGELOG.md](https://github.com/igamenovoer/houmao/blob/main/CHANGELOG.md); comparison: [`v2.3.0...v2.4.0`](https://github.com/igamenovoer/houmao/compare/v2.3.0...v2.4.0).

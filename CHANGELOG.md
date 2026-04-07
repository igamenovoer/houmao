# Changelog

This changelog tracks published Houmao releases.

The entries below summarize user-visible changes from the tagged release history rather than listing every commit verbatim.

## [0.4.0] - 2026-04-07

### Added

- **Agent launch profiles**: a new reusable, recipe-backed birth-time launch configuration object on `houmao-mgr project agents launch-profiles ...`, plus the matching specialist-backed easy-profile lane on `houmao-mgr project easy profile ...`. Both lanes share one catalog launch-profile family and a shared conceptual model documented in the new launch-profiles guide.
- **Managed launch prompt header**: every managed launch now prepends a short Houmao-owned prompt header by default that identifies the agent as managed, names `houmao-mgr` as the canonical interface, and points the model at supported Houmao workflows. Per-launch `--managed-header` / `--no-managed-header` flags and a stored `managed_header_policy` field on launch profiles control the behavior; documented in the new run-phase reference page.
- **Unified model selection**: `--model` and `--reasoning-level` are now tool-agnostic launch-owned selectors on `agents launch`, `project easy specialist create`, and `project easy instance launch`, with the per-tool resolution handled by the provider mapping.
- **Agent definition / instance / messaging / gateway / email-comms system skills**: six new packaged Houmao-owned system skills bring the catalog to eight: `houmao-manage-agent-definition`, `houmao-manage-agent-instance`, `houmao-agent-messaging`, `houmao-agent-gateway`, `houmao-agent-email-comms` (the unified ordinary mailbox skill), and `houmao-process-emails-via-gateway` (notifier-driven unread-mail rounds). The catalog now ships with a JSON Schema and explicit auto-install set lists.
- **`system-skills install --symlink`**: install packaged skills as directory symlinks to the source roots instead of copied trees, for development homes that should track in-place edits.
- **`agents launch --workdir`**: explicit runtime-cwd override for `agents launch`, `agents join`, and `project easy instance launch`. Source-overlay and runtime-root pinning remain on the launch source project even when `--workdir` points elsewhere.
- **Easy gateway by default**: `project easy instance launch` now requests launch-time gateway attach on loopback by default, with `--no-gateway` and `--gateway-port <port>` as the supported overrides.
- **`houmao-mgr --version`**: root reporting flag that prints the packaged Houmao version and exits successfully without a subcommand.
- **Claude vendor auth lanes**: `project agents tools claude auth` and `project easy specialist create --tool claude` accept directory-based vendor login state via `--config-dir` / `--claude-config-dir`, alongside an optional Claude-official-login fixture smoke check.
- **Managed prompt header reference and system-skills overview guide**: two new documentation pages bridging the README skill catalog and the per-flag CLI reference.
- **GitHub release → docs deploy**: the docs workflow now builds and deploys GitHub Pages from the published release tag, in lockstep with the existing release-driven PyPI publish workflow.

### Changed

- **Agent presets refactored to named resources**: low-level recipes are now administered through `houmao-mgr project agents recipes ...` (with `presets ...` retained as the compatibility alias) and explicit launch profiles through `houmao-mgr project agents launch-profiles ...`. Recipe and launch-profile files live under `agents/presets/<name>.yaml` and `agents/launch-profiles/<name>.yaml`.
- **Specialist skill renamed**: the packaged `houmao-create-specialist` skill is now `houmao-manage-specialist` and covers create, list, get, remove, launch, and stop. The flat layout now mirrors the rest of the system-skills surface.
- **Email-comms skill unified**: the prior split mailbox skill surface is now one `houmao-agent-email-comms` skill for ordinary shared-mailbox operations plus the no-gateway fallback path, paired with `houmao-process-emails-via-gateway` for the round-oriented unread-mail workflow.
- **System-skills install defaults revised**: `agents launch` and `agents join` now auto-install `mailbox-full + user-control + agent-messaging + agent-gateway` (seven skills) into managed homes by default. Explicit `system-skills install` against an external tool home additionally installs `agent-instance` for the full eight-skill CLI default. The CLI-default selection is requested by omitting both `--set` and `--skill`.
- **Gateway and agent management workflows updated**: refreshed gateway sidecar lifecycle, manifest-first discovery, target-tmux-session selectors, and gateway mail-notifier coverage.
- **Documentation refresh**: CLI reference pages, README skill catalog, getting-started overview/quickstart/easy-specialists/launch-profiles, and the run-phase pages were resynced against the post-launch-profiles state. Two new pages added (managed-prompt-header reference, system-skills overview guide).

### Removed

- **BREAKING: `--yolo` removed from `houmao-mgr agents launch` and `project easy instance launch`.** Prompt-mode posture is now controlled exclusively through stored `launch.prompt_mode` (`unattended` or `as_is`) on recipes, specialists, and launch profiles. Existing scripts or tutorials that pass `--yolo` should remove the flag and rely on the recipe-stored prompt mode instead.

### Fixed

- Post-refactor accuracy errors in CLI help text, README, and CLI reference pages were corrected. Stale `--yolo` and pre-rename `houmao-create-specialist` references in documentation were removed or rewritten as historical notes.

### Notes

- This release covers the full set of changes shipped after `v0.2.0`. Internal version bumps `0.3.0`, `0.3.1`, `0.3.2`, and `0.3.3` were never published as public PyPI releases; their changes are folded into this entry.
- The `gh release create v0.4.0` event triggers both `pypi-release.yml` (PyPI publish via OIDC trusted publishing) and `docs.yml` (GitHub Pages deploy from the release tag).

## [0.2.0] - 2026-04-04

### Added

- Project-aware workflows across the main CLI, including richer `houmao-mgr` project commands, project overlay handling, and catalog-backed project state.
- Passive-server discovery, gateway proxying, and headless-management flows for server-backed automation.
- New demo and validation surfaces, including minimal agent launch, single-agent mail wake-up, single-agent gateway wake-up headless, and refreshed shared TUI tracking packs.
- Expanded Gemini support, including unattended launch defaults, easy-demo lanes, and full-permission headless execution.
- GitHub Pages publishing for the docs site and an automated GitHub-release-to-PyPI publication path.

### Changed

- Promoted `houmao-mgr` as the primary lifecycle and project-management CLI surface, with broader runtime, cleanup, mailbox, gateway, and output-rendering support.
- Simplified agent definitions and demo launch flows, while retiring the legacy agent-definition layout and additional `agentsys` compatibility fallbacks.
- Made more operations project-aware, including mailbox and gateway behavior that now resolves against the active project layout instead of older environment-driven conventions.
- Reworked mailbox skill projection so native mailbox/system-skill contracts are part of the current Houmao runtime model.
- Expanded and reorganized the documentation set around getting-started, reference, and developer guides.

### Fixed

- Hardened gateway endpoint discovery, prompt-readiness gating, notifier triggering, and gateway/headless output rendering.
- Clarified and enforced mailbox runtime contracts, including removal of older env-based mailbox assumptions and non-authoritative TUI mail submission paths.
- Tightened credential-fixture hygiene and removed leaked or ambiguous auth-related history and test artifacts.
- Improved headless and resume behavior across Codex, Claude, and Gemini flows, including tmux/session lifecycle handling.

### Notes

- This release includes the full set of changes published after `v0.1.0`, including the release automation needed to publish `v0.2.0`.

## [0.1.0] - 2026-03-27

### Added

- First public Houmao release.
- Initial published package and tagged GitHub release for the Houmao runtime, CLI, docs, and supporting workflows that existed at the public-release baseline.

### Notes

- `v0.1.0` is the initial public reference point for the project changelog.

[0.4.0]: https://github.com/igamenovoer/houmao/compare/v0.2.0...v0.4.0
[0.2.0]: https://github.com/igamenovoer/houmao/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/igamenovoer/houmao/releases/tag/v0.1.0

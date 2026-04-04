# Changelog

This changelog tracks published Houmao releases.

The entries below summarize user-visible changes from the tagged release history rather than listing every commit verbatim.

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

[0.2.0]: https://github.com/igamenovoer/houmao/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/igamenovoer/houmao/releases/tag/v0.1.0

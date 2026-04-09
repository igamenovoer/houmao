# Changelog

This changelog tracks published Houmao releases.

The entries below summarize user-visible changes from the tagged release history rather than listing every commit verbatim.

## [0.4.2] - 2026-04-09

### Added

- **Gateway reminders CLI**: `houmao-mgr agents gateway reminders` now exposes the live gateway ranked reminder surface end-to-end as `list`, `get`, `create`, `update`, `pause`, `resume`, and `delete` subcommands, routed through the local pair-server gateway proxy on both `houmao-server` and `houmao-passive-server`. Documented in the refreshed [agents-gateway CLI reference](docs/reference/cli/agents-gateway.md), in the gateway reminders operations page, and in the `houmao-agent-gateway` system skill.
- **Managed agent memory directories**: managed launches now project a per-agent memory directory under the runtime home and expose it through `HOUMAO_MEMORY_DIR`. The directory is recorded in the session manifest, surfaced via `houmao-mgr agents` listings, cleaned up by `admin cleanup`, and documented in the new [Managed memory directories](docs/getting-started/managed-memory-dirs.md) guide and updated agents-and-runtime reference. Specs: `agent-memory-dir`, plus updates to `brain-launch-runtime`, `houmao-mgr-agents-launch`, `houmao-mgr-agents-join`, and `houmao-mgr-project-easy-cli`.
- **Launch-time system prompt appendix**: every managed launch can now carry a Houmao-owned system-prompt appendix appended after the standard managed-launch header. The appendix copy lives under `managed_prompt_header.py`, is exposed through the run-phase managed-prompt-header reference, and is recorded against the launch plan so reruns and `agents join` see the same effective prompt.
- **`houmao-touring` system skill**: a new packaged manual guided-tour skill that inspects current Houmao state, explains the posture in plain language, and routes work into the appropriate maintained Houmao skill. Brings the packaged catalog to **twelve** skills.
- **Pairwise driver-worker edge-loop pattern**: the `houmao-adv-usage-pattern` skill gains a second supported pattern at `patterns/pairwise-edge-loop-via-gateway-and-mailbox.md` for delegation rounds where each edge closes locally between exactly two agents. The `SKILL.md` chooser now distinguishes it from the existing forward relay-loop pattern.
- **Forward relay-loop pattern**: the `houmao-adv-usage-pattern` skill also ships the supported relay-loop pattern at `patterns/relay-loop-via-gateway-and-mailbox.md` for multi-agent loops where work can transit across additional live-gateway agents before a downstream egress returns the final result to a more distant origin.
- **Passive-server gateway proxy**: `houmao-passive-server` and `houmao-server` both expose a uniform pair-server gateway proxy surface (`pair_client.py`, `service.py`, `app.py`) used by the new gateway reminders CLI; documented in the new `passive-server-gateway-proxy` spec.

### Changed

- **System skills install internals**: `houmao-mgr system-skills install` and the underlying `system_skills.py` projection layer were resynced so renamed packaged identifiers, the new `houmao-touring` skill, the new advanced-usage pattern files, and the gateway-reminders skill updates project consistently into managed and external tool homes. CLI reference docs (`system-skills.md`, `houmao-mgr.md`) were refreshed alongside the changes.
- **Gateway-first mailbox runtime support**: `mailbox_runtime_support.py`, `runtime_artifacts.py`, and the project-aware command surface picked up the memory-dir wiring, the prompt-appendix wiring, and the gateway-reminders manifest fields so existing managed-agent operations and `admin cleanup` continue to behave correctly across the new launch-time inputs.

### Fixed

- **Codex bootstrap migrates the `model` key**: `_ensure_codex_model_migration_state` now rewrites the runtime config `model` key to `gpt-5.4` when the existing value is the migration source `gpt-5.3-codex`, instead of only recording a `notice.model_migrations` entry. Unattended Codex launches no longer keep invoking the deprecated model after bootstrap. Backed by the existing `tests/unit/agents/realm_controller/test_codex_bootstrap.py` cases that have always expected this behavior.
- **System skills install + CLI startup backports**: a backport sweep on `houmao-mgr system-skills install` and the CLI startup path repairs handling of the renamed packaged identifiers and the new pattern/skill assets, paired with refreshed `system-skills` and `houmao-mgr` reference pages.

### Notes

- This is a patch release on top of `v0.4.1`. It bundles the new gateway reminders CLI, managed memory directories, launch-time prompt appendix, the `houmao-touring` skill, the two `houmao-adv-usage-pattern` loop patterns, the codex bootstrap migration fix, and the system-skills install backport. The patch label is kept for continuity even though the contents include user-visible feature surfaces.
- The `gh release create v0.4.2` event triggers both `pypi-release.yml` (PyPI publish via OIDC trusted publishing) and `docs.yml` (GitHub Pages deploy from the release tag).

## [0.4.1] - 2026-04-08

### Added

- **Gateway ranked reminders**: the live gateway sidecar now exposes a ranked reminder surface at `/v1/reminders` (replacing the prior `/v1/wakeups` surface) supporting `POST`, `GET`, `GET {id}`, `PUT {id}`, and `DELETE {id}`. Reminders carry a signed `ranking`, optional `paused` state, and either a `prompt` or a raw `send_keys` payload; the gateway selects one effective reminder by ranking and only that one is eligible to dispatch. Documented end-to-end in the new [Gateway Reminders](docs/reference/gateway/operations/reminders.md) operations page and in the protocol contract.
- **Managed launch force takeover modes**: `houmao-mgr agents launch` and `houmao-mgr project easy instance launch` now accept `--force [keep-stale|clean]` to take over an existing live local owner of the resolved managed identity. Bare `--force` means `keep-stale` (stop the predecessor and reuse the predecessor managed home in place); `--force clean` stops the predecessor and removes only predecessor-owned replaceable launch artifacts before rebuilding. Force mode is launch-owned only and is never persisted into stored launch profiles or easy profiles.
- **`houmao-project-mgr` system skill**: a new packaged Houmao-owned system skill for project overlay lifecycle, `.houmao/` layout explanation, project-aware command effects, explicit launch-profile management, and project-scoped easy-instance inspection or stop routing.
- **`houmao-mailbox-mgr` system skill**: a new packaged mailbox-admin skill covering filesystem mailbox root lifecycle, mailbox account lifecycle, structural mailbox inspection, and late filesystem mailbox binding on existing local managed agents.
- **`houmao-adv-usage-pattern` system skill**: a new packaged skill that documents supported advanced multi-skill mailbox and gateway workflow compositions layered on top of the direct-operation skills, starting with self-wakeup through self-mail plus notifier-driven rounds.
- **Operator-origin filesystem mail**: the mailbox subsystem and managed helpers now support operator-origin send for filesystem mailbox transports through `houmao-mgr agents mail post`.

### Changed

- **Managed gateways default to foreground**: `houmao-mgr project easy instance launch` and the matching managed launch flow now default the gateway sidecar to foreground attachment instead of detached background mode.
- **System skill identifiers renamed**: the packaged user-control skills were renamed for consistency — `houmao-create-specialist` → `houmao-specialist-mgr`, `houmao-manage-credentials` → `houmao-credential-mgr`, `houmao-manage-agent-definition` → `houmao-agent-definition`, and `houmao-manage-agent-instance` → `houmao-agent-instance`. The new `houmao-project-mgr`, `houmao-mailbox-mgr`, and `houmao-adv-usage-pattern` skills bring the catalog to **eleven** packaged Houmao-owned skills.
- **Documentation refresh**: `CLAUDE.md`, README, the getting-started guides, and the reference index were resynced for the post-v0.4 state. The duplicative `docs/reference/agents/` subtree was retired in favor of the current `run-phase`, `system-files`, and CLI reference homes. The deprecated `cao_rest` and `houmao_server_rest` backends now carry an unmaintained-deprecation banner where they are still documented.

### Fixed

- **Agent cleanup skips missing artifacts**: `houmao-mgr admin cleanup` no longer fails when a referenced artifact has already been removed by an earlier sweep or by an unrelated operator action.
- **CLI custom renderer payload normalization**: model-name normalization for the CLI custom renderer was tightened so non-standard payloads no longer break headless output rendering.
- **System skill launcher resolution**: the launcher resolution path was tightened so packaged system skills resolve correctly under the renamed identifiers.
- **Stale doc links and skill counts**: corrected a broken `docs/reference/agents/operations/project-aware-operations.md` link in the system-skills overview, refreshed two stale "ten packaged skills" mentions to "eleven", and updated the README `houmao-agent-gateway` row from "schedule wakeups" to "schedule ranked reminders" for consistency with the post-rename gateway surface.

### Notes

- This is a patch release that consolidates several feature commits (gateway reminders, force takeover, three new system skills, default-foreground gateway) plus a small docs cleanup pass on top of `v0.4.0`. The `0.4.1` label was chosen for continuity with the post-`0.4.0` numbering even though the contents include user-visible feature surfaces; future releases that add more breaking surface may bump the minor segment instead.
- The `gh release create v0.4.1` event triggers both `pypi-release.yml` (PyPI publish via OIDC trusted publishing) and `docs.yml` (GitHub Pages deploy from the release tag).

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

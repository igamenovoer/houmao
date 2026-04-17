# Changelog

This changelog tracks published Houmao releases.

The entries below summarize user-visible changes from the tagged release history rather than listing every commit verbatim.

## [0.7.0rc8] - 2026-04-17

### Changed

- **Clarified system skill projection output**: `houmao-mgr system-skills install` and `uninstall` now emit structured, human-readable projection summaries showing exactly which skills were installed, skipped, or removed per tool home.
- **Revised in-repo workspace mutation model**: the `houmao-utils-workspace-mgr` in-repo workspace subskill gains clearer mutation-scope guidance and expanded safety rules for managed-agent file operations.

### Fixed

- **Stopped agent cleanup targets recovered**: `houmao-mgr cleanup` and `houmao-server` agent API now correctly resolve and clean up agents that reached stopped state, fixing cases where stopped agents were missed during discovery and cleanup sweeps.

## [0.7.0rc7] - 2026-04-17

### Added

- **Workspace manager utility system skill**: new `houmao-utils-workspace-mgr` packaged system skill provides in-repo and out-of-repo workspace management subskills for managed agents.

### Changed

- **Consolidated system skill install sets**: system skill catalog reorganized into simplified install sets, streamlining `houmao-mgr system-skills install` and reducing per-tool skill fragmentation. Overview docs and CLI reference updated accordingly.

## [0.7.0rc6] - 2026-04-16

### Added

- **System skills uninstall command**: `houmao-mgr system-skills uninstall` removes previously installed Houmao system skills from tool homes, with `--tool` filtering and `--dry-run` preview support.
- **LLM Wiki utility system skill**: new `houmao-utils-llm-wiki` packaged system skill provides a complete wiki authoring toolkit — article scaffolding, schema validation, lint, audit review, and an interactive web viewer with graph visualization — installable via `houmao-mgr system-skills install`.

## [0.7.0rc5] - 2026-04-16

### Changed

- **Simplified system skill reinstall**: `houmao-mgr system-skills install` no longer requires separate overwrite flags; reinstalling over existing skills now uses straightforward replace semantics, removing previous overwrite-policy complexity.

### Fixed

- **Proxy env bypassed for gateway attach**: gateway HTTP client now strips proxy-related environment variables (`HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY` and lowercase variants) during attach and status calls, preventing connection failures when the runtime runs behind a corporate proxy that cannot reach the local gateway.

## [0.7.0rc4] - 2026-04-16

### Added

- **Multi-tool system skill installs**: `houmao-mgr system-skills install` now accepts comma-separated `--tool` values (e.g. `--tool claude,codex,gemini`) to install Houmao system skills into multiple tool homes in a single command.

### Changed

- **Simplified launch profile memo seeds**: memo seed policies reduced to unconditional replace semantics; removed `initialize` and `fail-if-nonempty` policies and the represented-targets content check.
- **Removed source migration paths**: in-memory manifest upgrade logic for schema versions 1–3 removed; the runtime now requires `schema_version=4` exclusively. Legacy brain homes must be rebuilt with the current builder.
- **Removed GitHub skill mirrors**: the mirrored GitHub skill files that duplicated packaged system skills are removed; the canonical source is the packaged skill tree.

### Fixed

- **Memo seed content refs migrated**: memo seed `content_ref` paths updated to match the simplified seed structure.
- **Stale schema version references in docs**: `agents-and-runtime.md` and `brain-launch-runtime` spec updated from schema v2/v3 references to v4.

## [0.7.0rc3] - 2026-04-15

### Added

- **Copilot system skill installs**: GitHub Copilot CLI is now a supported system-skill install target alongside Claude, Codex, and Gemini.
- **Per-tool credential kinds reference pages**: `houmao-specialist-mgr` and `houmao-credential-mgr` system skills gain dedicated credential-kinds reference pages for Claude, Codex, and Gemini with cross-linked discovery shortcuts.
- **Launch profile memo seeds**: launch profiles can now carry `memo_seeds` — a list of policy-driven memo-file seed entries that are materialized into the agent's memory root at launch time.
- **Writer team example and touring welcome**: new `examples/writer-team/` multi-agent example and an updated `houmao-touring` skill welcome branch.

### Changed

- **Compatibility profile bootstrap hidden**: the legacy compatibility profile bootstrap path is no longer surfaced in default flows.
- **Docs synced with rc1/rc2 changes**: architecture overview diagram updated to schema_version 4, mailbox answered state documented, writer-team cross-referenced from loop authoring guide and README.

### Fixed

- **Memo seed policies scoped to represented components**: memo seed policies now apply only to the components the launch profile actually represents, preventing unintended seed injection across unrelated agents.

## [0.7.0rc2] - 2026-04-15

### Added

- **`houmao-memory-mgr` system skill**: new packaged skill gives managed agents a first-class interface for reading and writing their own memory root — free-form memo file, page files, and page link resolution — without operator intervention.
- **Memo-cue section in managed prompt header**: the Houmao-owned prompt header gains a sixth independently controllable section, `memo-cue`, enabled by default. It points the agent at the resolved absolute `houmao-memo.md` path at the start of every prompt turn, ensuring the agent sees its persistent memo without being explicitly instructed to read it. Control with `--managed-header-section memo-cue=disabled` or store the setting in a launch profile.

### Changed

- **`agents workspace` renamed to `agents memory`**: the per-agent workspace command family is now `houmao-mgr agents memory` to reflect the broader memory model (free-form memo, pages, and directory tree). All sub-commands (`path`, `memo show/set`, `tree`, `read`, `write`, `append`, `delete`, `clear`) are preserved under the new name. **BREAKING for rc1 users**: update any scripts using `agents workspace` to `agents memory`.
- **Simplified memory model**: the `scratch/` and `persist/` lane distinction is removed in favor of a flat free-form memory root. The `houmao-memo.md` file and an optional `pages/` directory are the canonical memory surfaces. Environment variables updated accordingly.
- **rc1 changelog corrected**: the `agents workspace` and unified workspace layout entries from rc1 describe the API that is now renamed/simplified in rc2.

## [0.7.0rc1] - 2026-04-14

### Added

- **Agent workspace commands**: `houmao-mgr agents workspace` command family gives every managed agent an operator-addressable workspace root with `path`, `memo show/set`, `tree`, `read`, `write`, `append`, `delete`, and `clear` sub-commands. Per-agent workspaces resolve to `<project-root>/.houmao/memory/agents/<agent-id>/` by default and expose `scratch/` and `persist/` lanes. The same workspace controls are available on `agents join`, `agents launch`, `project easy instance launch`, and stored launch profiles.
- **Mail-notifier notification mode**: gateway mail-notifier gains a `notification_mode` setting — `any_inbox` (default, existing behavior: wake while any unarchived inbox mail remains) and `unread_only` (wake only for unread unarchived inbox mail). Configurable at attach time and stored in gateway state.
- **Mailbox answered-archive lifecycle**: answered messages are now moved to an `answered/` archive lane in the filesystem mailbox, keeping the active inbox clean without deleting processed messages.

### Changed

- **Unified workspace directory layout**: `HOUMAO_AGENT_STATE_DIR`, `HOUMAO_AGENT_MEMO_FILE`, `HOUMAO_AGENT_SCRATCH_DIR`, and `HOUMAO_AGENT_PERSIST_DIR` replace the retired `HOUMAO_JOB_DIR` and `HOUMAO_MEMORY_DIR` env vars. The `memory/` subdirectory now appears in the `.houmao/` project overlay layout.
- **Docs and README updated**: `docs/index.md` gains a brief intro and audience-oriented "where to start" table; `docs/getting-started/quickstart.md` notes that it targets from-source checkouts; `README.md` reflects the workspace layout and `agents workspace` capabilities; `DEVELOPMENT-SETUP.md` filename typo fixed.

## [0.6.6] - 2026-04-14

### Changed

- **Operator-origin reply policy defaults to `operator_mailbox`**: `houmao-mgr agents mail post`, the gateway `POST /v1/mail/post` route, and the low-level `operator_origin_headers()` helper now default to `reply_policy=operator_mailbox` so replies route back to the reserved operator mailbox. Use `reply_policy=none` explicitly when a one-way operator note is intended.
- **Reply hardening in email processing skill**: `houmao-process-emails-via-gateway` now includes reply-hardening guidance with one-off gateway reminders that guard required replies against stalls or interrupts, including a prompt template and guardrails for duplicate-reply prevention.
- **Touring skill advanced-usage branch**: `houmao-touring` gains an `advanced-usage` branch for pairwise agent-loop creation guidance, routing users to `houmao-agent-loop-pairwise` or `houmao-agent-loop-pairwise-v2` with explicit skill-selection boundaries.

## [0.6.5] - 2026-04-13

### Added

- **Mailbox `clear-messages` command**: `houmao-mgr mailbox clear-messages` (and `project mailbox clear-messages`) clears delivered filesystem mail, message projections, mailbox-local message/thread state, and managed-copy attachments while preserving mailbox registrations and account directories. Supports `--dry-run` preview and `--yes` for non-interactive confirmation.
- **Mailbox `export` command**: `houmao-mgr mailbox export` (and `project mailbox export`) exports selected mailbox accounts and indexed messages into a portable archive directory with `manifest.json`, canonical messages, account metadata, and managed-copy attachments. Requires `--output-dir` plus explicit account scope (`--all-accounts` or `--address`). Default `--symlink-mode materialize` writes regular files with no symlinks.
- **`houmao-mailbox-mgr` system skill updated**: skill actions now cover `clear-messages` and `export` verbs alongside existing mailbox lifecycle operations.

## [0.6.4] - 2026-04-13

### Added

- **Final stable-active recovery**: new 20-second recovery path that clears stuck active TUI posture when raw evidence and published state stop changing while independent parser evidence confirms idle/freeform prompt-ready state, complementing the existing 5-second stale-active recovery for broader false-positive correction.
- **`--gateway-tui-final-stable-active-recovery-seconds`** CLI flag for tuning the final recovery window at attach and launch time.

### Changed

- **Simplified Claude Code activity detection**: replaced fragile text-matching patterns (`THINKING_PATTERNS`, `ACTIVE_TOOL_PATTERNS`) with spinner-line regex for more reliable activity detection.

## [0.6.3] - 2026-04-13

Release superseded by 0.6.4 (missing changelog update).

## [0.6.2] - 2026-04-12

### Fixed

- **Claude model selection via CLI args**: pass Claude model name and reasoning effort through CLI arguments (`--model`, `--reasoning-effort`) on launch instead of relying solely on environment variables, matching the Codex CLI override pattern.

## [0.6.1] - 2026-04-12

### Fixed

- **Claude Code stale scrollback active-state detection**: fixed false-positive active state when scrollback contained stale tool-use patterns but the visible surface showed idle.

### Added

- **Gateway TUI tracking timings**: expose gateway-owned TUI tracking timing metadata through `houmao-mgr agents gateway tui state`, the managed-agent API, and the `houmao-server` pair surface.
- **Easy instance launch `--gateway-tui-tracking` flag**: opt into gateway TUI state tracking at launch time through `project easy instance launch`.

### Changed

- **Foreground gateway skill guidance clarified**: system skill action docs for `houmao-agent-gateway`, `houmao-agent-instance`, `houmao-specialist-mgr`, `houmao-touring`, and `houmao-adv-usage-pattern` now clarify foreground gateway lifecycle expectations.
- **Specs synced**: updated OpenSpec specs for TUI state tracking, signal profiles, gateway, system skills, and easy CLI surfaces.

## [0.6.0] - 2026-04-12

### Added

- **Per-section managed-header policy**: the managed prompt header now has five independently controllable sections (`identity`, `houmao-runtime-guidance`, `automation-notice`, `task-reminder`, `mail-ack`) with per-section defaults, stored profile policy, and one-shot CLI overrides via `--managed-header-section SECTION=enabled|disabled`.
- **Easy specialist patch command** (`project easy specialist set`): patch an existing specialist's prompt, skills, setup, credential, model, reasoning level, prompt mode, and env without recreating it.
- **Codex CLI config override preference layer**: Houmao-managed Codex launches now pass final `-c` override arguments for model, reasoning effort, provider selection, and unattended posture so project-local `.codex/config.toml` cannot override Houmao-resolved preferences.
- **Internals graph tools** (`houmao-mgr internals graph`): NetworkX-backed graph helpers for loop plan authoring, structural analysis, packet validation, slicing, and Mermaid rendering.
- **Pairwise-v2 routing packets**: prestart routing-packet model for `houmao-agent-loop-pairwise-v2` with `initialize` strategy support.
- **Generic loop planner skill** (`houmao-agent-loop-generic`): decompose generic multi-agent loop graphs into typed pairwise and relay components.
- **Mailbox preferred in pairwise loop skill**: `houmao-agent-loop-pairwise` now states mailbox as the preferred communication channel and requires gateway mail-notifier preflight (interval 5s default) before start.

### Changed

- **Launch profile workflows improved**: expanded easy profile and explicit launch profile editing surfaces with full patch-preserving `set` commands and clear flags.
- **Codex reasoning ladder revised**: current Codex coding models (`gpt-5.4`, `gpt-5.3-codex`, `gpt-5.2-codex`) use `1=low`, `2=medium`, `3=high`, `4=xhigh`; `minimal` projected only when the model ladder explicitly includes it.
- **README and docs updated**: managed-header section architecture, specialist set verb, Codex CLI override hook, and loop authoring guide all reflected across README, getting-started guides, CLI reference, and system-skills overview.
- **Agent-driven workflow positioned as recommended**: README Step 1 leads with system-skills install and agent-driven conversation.

### Notes

- This release bumps the minor segment for the per-section managed-header policy, the new specialist set command, the Codex override preference layer, the graph tools, and the generic loop planner skill.

## [0.5.1] - 2026-04-10

### Added

- **`houmao-agent-loop-pairwise-v2` system skill**: enriched versioned pairwise loop workflow skill with `initialize`, `peek`, `ping`, `pause`, `resume`, `stop`, and `hard-kill` lifecycle verbs, split out from the stable `houmao-agent-loop-pairwise` skill which now retains only the `plan` + `start` / `status` / `stop` surface. Both skills are included in the `user-control` set and auto-installed into managed homes.
- **`readme-structure` spec**: new OpenSpec main spec tracking the README section layout and specialist-first onboarding ordering requirements.

### Changed

- **README rewritten for specialist-first workflow**: the README now leads with system-skills install (step 0), project init (step 1), and specialist creation/launch (step 2) as the primary onboarding path. A new Agent Loop section (step 3) showcases pairwise multi-agent coordination with a real story-writing example (3 specialists, per-chapter pipeline, mermaid control graph, produced artifacts). `agents join` is repositioned as a secondary lightweight/ad-hoc path (step 4). The intro is condensed from four subsections to two. Section ordering follows: Quick Start, Typical Use Cases, System Skills, Subsystems, Runnable Demos, CLI Entry Points, Full Docs, Development.
- **Stable pairwise loop skill simplified**: `houmao-agent-loop-pairwise` is trimmed to three operating pages (`start`, `status`, `stop`) and compact references/templates, with enriched lifecycle verbs moved to the new v2 skill.
- **System skills catalog updated**: `catalog.toml` now declares both `houmao-agent-loop-pairwise` and `houmao-agent-loop-pairwise-v2` in the `user-control` set. Docs and README system-skills tables updated to reflect the split.

### Notes

- The `gh release create v0.5.1` event triggers both `pypi-release.yml` (PyPI publish via OIDC trusted publishing) and `docs.yml` (GitHub Pages deploy from the release tag).

## [0.5.0] - 2026-04-09

### Added

- **Dedicated `credentials` CLI command group**: `houmao-mgr` now exposes a top-level `credentials` family alongside `admin`, `agents`, `brains`, `mailbox`, `project`, `server`, and `system-skills`. The family ships `claude`, `codex`, and `gemini` subcommands with the full `list`, `get`, `add`, `set`, `remove`, and `rename` CRUD verbs and uses `--agent-def-dir <path>` to target plain agent-definition directories outside any project overlay. The project-scoped `houmao-mgr project credentials <tool> ...` wrapper remains the preferred entry point when an active project overlay is present and shares the same semantics. Documented in the refreshed [houmao-mgr CLI reference](docs/reference/cli/houmao-mgr.md) and surfaced from the docs landing page; the `houmao-credential-mgr` system skill was rewired to route through this new surface.
- **Headless execution overrides on prompt surfaces**: `houmao-mgr agents prompt`, `houmao-mgr agents turn submit`, and `houmao-mgr agents gateway prompt` now accept `--model TEXT` and `--reasoning-level INTEGER` (normalized `1..10`) as request-scoped overrides. The overrides apply only to the submitted prompt/turn/gateway request and never mutate launch profiles, recipes, specialists, manifests, or stored easy profiles. Partial overrides (e.g., `--reasoning-level` alone) merge with launch-resolved model defaults through the shared headless resolution helper. Supplying either flag against a TUI-backed target is rejected explicitly rather than silently dropped. The same request-scoped `execution.model` payload is documented for the managed-agent HTTP routes (`POST /houmao/agents/{agent_ref}/turns`, `/gateway/control/prompt`, `/gateway/requests`) and for the direct gateway routes (`POST /v1/control/prompt`, `POST /v1/requests` for `submit_prompt`).
- **`houmao-agent-loop-pairwise` system skill**: a new packaged Houmao-owned skill for authoring and operating pairwise driver-worker edge loops. Pairs with the existing `pairwise-edge-loop-via-gateway-and-mailbox.md` advanced-usage pattern doc and brings the packaged catalog to thirteen skills.
- **`houmao-agent-loop-relay` system skill**: a second new packaged Houmao-owned skill for authoring and operating forward relay loops across multiple live-gateway agents. Pairs with the existing `relay-loop-via-gateway-and-mailbox.md` pattern doc and brings the packaged catalog to fourteen skills.

### Changed

- **Auth bundle decoupled from launch identity**: the auth profile, credential bundle, and launch identity surfaces were separated so credential management is no longer coupled to launch-time identity selection. `BrainBuilder`, the project catalog, and the `houmao-mgr project ...` command surface were resynced so credential CRUD, auth-profile rename, and `project easy specialist create` lanes route through the dedicated credential interface. The `houmao-credential-mgr`, `houmao-specialist-mgr`, and `houmao-agent-definition` packaged skill action docs were updated to match.
- **Documentation refresh for the catalog growth and new CLI surfaces**: README, `docs/getting-started/system-skills-overview.md`, `docs/reference/cli/houmao-mgr.md`, `docs/index.md`, and the operator-facing reference pages were resynced so the system-skills table enumerates every entry under `catalog.toml` (now fourteen), so the auto-install diagram and per-set expansion reflect the resolved `managed_launch_sets`/`managed_join_sets`/`cli_default_sets` contents instead of frozen counts, and so the `agents prompt`, `agents turn submit`, and `agents gateway prompt` rows explicitly document the new headless overrides and TUI-target rejection.

### Fixed

- **Codex stale active TUI tracking**: the Codex TUI tracker now recovers from a stale `active` state instead of staying stuck after the worker has gone idle. Adds a recovery path through `src/houmao/server/tui/tracking.py`, profile/signal updates under `src/houmao/shared_tui_tracking/apps/codex_tui/`, regression fixtures, and unit tests in `tests/unit/server/test_tui_parser_and_tracking.py` and `tests/unit/shared_tui_tracking/test_codex_tui_session.py`.
- **TUI interrupt always sends escape**: the interrupt path now always emits an escape key when interrupting a TUI-backed agent, replacing the prior conditional path that occasionally left the TUI in an unrecoverable focused-input state.
- **Mail-notifier source link in mkdocs strict build**: corrected the `gateway-mail-notifier` reference page link depth so the docs site builds cleanly under `mkdocs build --strict`.

### Notes

- This release bumps the minor segment because of the new top-level `credentials` CLI command group, the new headless execution override flags on three prompt surfaces, the auth/identity decoupling refactor, and the two new packaged loop system skills (`houmao-agent-loop-pairwise`, `houmao-agent-loop-relay`).
- The `gh release create v0.5.0` event triggers both `pypi-release.yml` (PyPI publish via OIDC trusted publishing) and `docs.yml` (GitHub Pages deploy from the release tag).

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

[0.6.6]: https://github.com/igamenovoer/houmao/compare/v0.6.5...v0.6.6
[0.6.5]: https://github.com/igamenovoer/houmao/compare/v0.6.4...v0.6.5
[0.6.4]: https://github.com/igamenovoer/houmao/compare/v0.6.3...v0.6.4
[0.6.3]: https://github.com/igamenovoer/houmao/compare/v0.6.2...v0.6.3
[0.6.2]: https://github.com/igamenovoer/houmao/compare/v0.6.1...v0.6.2
[0.6.1]: https://github.com/igamenovoer/houmao/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/igamenovoer/houmao/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/igamenovoer/houmao/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/igamenovoer/houmao/compare/v0.4.2...v0.5.0
[0.4.2]: https://github.com/igamenovoer/houmao/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/igamenovoer/houmao/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/igamenovoer/houmao/compare/v0.2.0...v0.4.0
[0.2.0]: https://github.com/igamenovoer/houmao/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/igamenovoer/houmao/releases/tag/v0.1.0

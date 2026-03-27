## ADDED Requirements

### Requirement: Joined tmux-backed sessions materialize the standard runtime session envelope
The runtime SHALL support materializing a standard Houmao session envelope around an existing tmux session that was not originally started by Houmao, so later control can use the same manifest-first contract as native launches.

For joined TUI adoption, the effective backend SHALL be `local_interactive`. For joined native headless adoption, the effective backend SHALL be the provider-specific native headless backend (`claude_headless`, `codex_headless`, or `gemini_headless`).

The join materialization path SHALL create all of the following under the effective runtime root for the adopted session:

- a session root,
- placeholder `agent_def/` content,
- placeholder `brain_manifest.json`,
- a persisted session manifest,
- session-local gateway artifacts under `gateway/`,
- a shared-registry record for the adopted managed agent.

The join materialization path SHALL construct the persisted joined-session `launch_plan` directly from join inputs rather than deriving runtime launch behavior from the placeholder `brain_manifest.json`.

If a placeholder `brain_manifest.json` is written for a joined session, it SHALL remain a path or invariant artifact only and SHALL NOT be the authoritative source of runtime launch or relaunch behavior for that joined session.

The join materialization path SHALL create the resolved job directory on disk before publishing `AGENTSYS_JOB_DIR`.

The join materialization path SHALL publish `AGENTSYS_MANIFEST_PATH`, `AGENTSYS_AGENT_ID`, `AGENTSYS_AGENT_DEF_DIR`, and `AGENTSYS_JOB_DIR` into the adopted tmux session environment.

The adopted session SHALL reuse the current tmux session name as the live tmux handle and SHALL keep tmux window `0` as the canonical managed agent surface even when the join command itself runs from another window of that same tmux session.

After successful join, the runtime SHALL treat shared-registry publication and later refresh or teardown for that adopted session as runtime-owned publication state even though the current provider process was originally started by the user.

For joined sessions, the initial shared-registry publication SHALL use a long sentinel lease that keeps the adopted session discoverable after the one-shot join command exits until the session is explicitly stopped or cleaned up.

The resulting manifest and tmux session environment SHALL remain the authoritative inputs for later `state`, `show`, `prompt`, `interrupt`, `gateway attach`, and related runtime-managed control paths rather than introducing a join-only discovery store.

#### Scenario: TUI join materializes a normal `local_interactive` runtime envelope
- **WHEN** the local join path adopts a live Codex TUI from tmux window `0`, pane `0`
- **THEN** it writes a normal session root containing placeholder `agent_def/`, placeholder `brain_manifest.json`, a persisted session manifest, and session-local `gateway/` artifacts
- **AND THEN** it publishes `AGENTSYS_MANIFEST_PATH`, `AGENTSYS_AGENT_ID`, `AGENTSYS_AGENT_DEF_DIR`, and `AGENTSYS_JOB_DIR` into that tmux session environment
- **AND THEN** it publishes a shared-registry record for the adopted managed agent without requiring a separate join-only discovery store

#### Scenario: Headless join materializes a native headless runtime envelope between turns
- **WHEN** the local join path adopts a tmux-backed Codex headless logical session between turns
- **THEN** it persists that adopted session as `backend = "codex_headless"` with the normal manifest, gateway, tmux-env, and shared-registry artifacts
- **AND THEN** later runtime-controlled headless turn submission can resume the same logical session from that manifest-backed authority

#### Scenario: Joined session launch behavior does not depend on the placeholder brain manifest
- **WHEN** the local join path materializes a joined session with a placeholder `brain_manifest.json`
- **THEN** the joined session's persisted `launch_plan` remains the authoritative launch and relaunch input for runtime control
- **AND THEN** runtime behavior does not require reconstructing provider launch semantics from the placeholder brain manifest

#### Scenario: Joined registry publication survives the one-shot join command
- **WHEN** a joined session is published to the shared registry
- **AND WHEN** the one-shot `houmao-mgr agents join` command exits successfully
- **THEN** the adopted session remains discoverable through its initial long sentinel lease
- **AND THEN** the design does not require a background lease-renewal daemon just to keep that joined session visible

### Requirement: Joined tmux-backed sessions persist explicit adopted relaunch posture
For tmux-backed joined sessions, the persisted relaunch authority SHALL record that the session origin is tmux join adoption rather than Houmao-started provider launch.

For joined sessions, the persisted session manifest's `agent_launch_authority` SHALL be the source of truth for secret-free relaunch posture.

For this change, joined-session relaunch metadata SHALL remain a backward-compatible extension of the existing session manifest v4 contract rather than requiring a new manifest version solely for joined-session posture fields.

That persisted relaunch authority SHALL distinguish at minimum all of the following postures:

- `runtime_launch_plan`,
- `tui_launch_options`,
- `headless_launch_options`,
- `unavailable`.

The persisted relaunch authority SHALL include an explicit `posture_kind` discriminator. Runtime relaunch logic SHALL NOT infer the joined-session relaunch posture solely from field presence.

For `tui_launch_options` and `headless_launch_options`, the persisted relaunch authority SHALL store structured launch args together with structured Docker-style launch env specs:

- `NAME=value` is persisted as a literal binding record,
- `NAME` is persisted as an inherited binding record that resolves `NAME` from the adopted tmux session environment at relaunch time.

When a joined TUI session is adopted without any structured launch options, later `houmao-mgr agents relaunch` and gateway-managed relaunch SHALL fail explicitly with an unavailable-relaunch error while other manifest-backed control paths remain valid.

When a joined TUI or native headless session includes operator-supplied relaunch posture, later relaunch SHALL reuse tmux window `0` and SHALL NOT rebuild a brain home or invent a replacement launch contract.

For joined native headless sessions that persist `headless_launch_options`, the provider continuity state needed to continue later work SHALL remain in the backend-specific manifest section for that provider rather than being duplicated into the shared registry.

That backend-specific continuity state SHALL support all of the following meanings:

- no known-chat resume,
- resume the provider's most current known chat,
- resume one exact provider chat or session id.

The tmux session environment SHALL NOT become a second persistence store for relaunch posture. It SHALL be used only for existing manifest-discovery pointers and for resolving inherited launch-env bindings at relaunch time.

The shared registry SHALL NOT persist a second copy of joined-session relaunch posture. Shared-registry publication for joined sessions remains limited to discovery and stable runtime pointers.

The persisted operator-supplied relaunch posture SHALL remain secret-free manifest metadata. The runtime SHALL NOT copy credentials into the shared registry or into synthesized launcher directories just to relaunch a joined session.

#### Scenario: Joined TUI without structured launch options remains controllable but not relaunchable
- **WHEN** a live Claude Code TUI is adopted through `houmao-mgr agents join` without any `--launch-args` or `--launch-env`
- **THEN** later manifest-backed `state`, `show`, `prompt`, `interrupt`, and `gateway attach` operations remain valid for that joined session
- **AND THEN** a later `houmao-mgr agents relaunch` fails with an explicit unavailable-relaunch error instead of inventing a restart command

#### Scenario: Joined headless relaunch uses the persisted launch options and exact resume id
- **WHEN** a Codex native headless logical session was adopted with `--launch-args exec --launch-args --json --launch-env CODEX_HOME` and `--resume-id thread_123`
- **THEN** later relaunch uses those persisted launch args and launch env specs together with the persisted `resume_id`
- **AND THEN** the relaunched work reuses tmux window `0`
- **AND THEN** the runtime does not rebuild a brain home for that joined headless session

#### Scenario: Joined headless relaunch can use the latest known chat
- **WHEN** a Codex native headless logical session was adopted with `--launch-args exec --launch-args --json --resume-id last`
- **THEN** later runtime-controlled headless work uses the provider's most current known chat rather than requiring one exact persisted thread id
- **AND THEN** the relaunched work reuses tmux window `0`

#### Scenario: Joined headless relaunch can intentionally avoid known-chat resume
- **WHEN** a Codex native headless logical session was adopted with `--launch-args exec --launch-args --json` and without `--resume-id`
- **THEN** later runtime-controlled headless work does not resume a known provider chat
- **AND THEN** the relaunched work starts from a fresh provider session

#### Scenario: Joined relaunch resolves inherited env from tmux env while registry stays pointer-only
- **WHEN** a joined session persists launch env specs that include inherited entry `CODEX_HOME`
- **AND WHEN** the adopted tmux session environment currently publishes `CODEX_HOME=/tmp/codex-home`
- **THEN** later relaunch resolves `CODEX_HOME` from that tmux session environment
- **AND THEN** the shared-registry record for that joined session does not need to persist a second copy of the relaunch posture or inherited env value

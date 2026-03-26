## MODIFIED Requirements

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

For joined TUI adoption, the persisted manifest and later manifest rewrites SHALL preserve the adopted tmux window identity needed to find the live provider surface. Resume-time capability publication and other post-join local control paths SHALL NOT overwrite that adopted window metadata with `null` or a default launch-time window name.

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

#### Scenario: Joined local TUI resume preserves the adopted tmux window metadata
- **WHEN** a live Claude TUI is joined from tmux window `0` whose current window name is `claude`
- **AND WHEN** a later local control path resumes that joined session and republishes manifest-backed gateway capability
- **THEN** the persisted manifest still records the adopted window identity needed to find window `0`
- **AND THEN** later local TUI tracking does not fall back to probing window name `agent` only because the resume path rewrote the manifest

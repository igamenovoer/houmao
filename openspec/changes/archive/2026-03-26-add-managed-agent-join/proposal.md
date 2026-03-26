## Why

Today Houmao can only manage tmux-backed agent sessions that it launched itself or that another Houmao-owned launcher registered on its behalf. Operators who already started a provider TUI or maintain a tmux-backed native headless session outside that launch path cannot adopt it into Houmao, so registry discovery, gateway attach, prompt or interrupt, and relaunch workflows stop at the launcher boundary.

## What Changes

- Add a local `houmao-mgr agents join` command that adopts an existing tmux-backed agent session into Houmao without restarting the current provider process.
- Support two join modes: live TUI adoption from tmux window `0`, pane `0` of the current session with provider auto-detection, and headless adoption of a tmux-backed logical session using structured launch args, Docker-style launch env specs, and optional resume selection (`none`, `last`, or explicit provider resume id).
- Materialize the same runtime-owned control artifacts used by native launches while constructing joined-session launch-plan state directly from join inputs instead of treating the placeholder brain manifest as runtime behavioral truth.
- Persist explicit adopted-session metadata and tagged relaunch posture in backward-compatible session-manifest v4 extensions so later `state`, `show`, `prompt`, `interrupt`, `gateway attach`, and `relaunch` flow through the normal manifest-first control path.
- Publish joined shared-registry records with a long sentinel lease so one-shot join commands remain discoverable until explicit stop or cleanup.
- Fail closed when required tmux context or operator-supplied adoption inputs are missing, inconsistent, or unsupported.

## Capabilities

### New Capabilities
- `houmao-mgr-agents-join`: Adopt an already-running tmux-backed TUI or native headless session into local managed-agent control.

### Modified Capabilities
- `brain-launch-runtime`: Extend runtime session materialization and relaunch metadata so externally started tmux sessions can be adopted into the standard manifest, gateway, and registry contract.
- `houmao-srv-ctrl-native-cli`: Add `houmao-mgr agents join` as a supported native managed-agent command.

## Impact

- **CLI behavior**: `houmao-mgr agents join` becomes the native local adoption command for existing tmux-backed sessions.
- **Runtime artifacts**: joined sessions need manifest, placeholder agent-definition and brain-manifest artifacts, gateway capability publication, tmux env publication, and shared-registry publication.
- **Manifest and relaunch metadata**: tmux-backed joined sessions need explicit session-origin, tagged relaunch-posture metadata, and join-derived launch-plan state while remaining compatible with the current manifest schema generation path.
- **Registry lifecycle**: joined shared-registry publication needs an explicit long-lease posture because `join` is a one-shot adoption command rather than a resident runtime controller.
- **Testing and docs**: add coverage and operator guidance for TUI join, headless join, resume-selector semantics, schema-regeneration requirements, and failure cases around missing tmux context or invalid join inputs.

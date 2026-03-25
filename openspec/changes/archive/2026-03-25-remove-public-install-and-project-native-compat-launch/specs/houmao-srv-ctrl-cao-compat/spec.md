## ADDED Requirements

### Requirement: Session-backed pair launch resolves native agent definitions instead of installed compatibility profiles
For session-backed TUI launch in the supported pair, top-level `houmao-mgr launch` and explicit `houmao-mgr cao launch` SHALL interpret `--agents` as a native launch selector resolved from the effective agent-definition root rather than as a preinstalled compatibility profile name.

The effective agent-definition root used by session-backed launch SHALL follow the same native root contract used by top-level native headless translation.

In the first cut, session-backed selector resolution SHALL support tool-lane brain recipes from that root for the selected provider or tool lane.

This first cut SHALL NOT require blueprint-by-name resolution on the session-backed pair-launch surface.

Session-backed launch SHALL NOT require a separate public install step to preload compatibility profile state before launch.

When the resolved native launch target has no role binding or no matching role package, session-backed launch SHALL remain valid and SHALL treat that launch as a brain-only launch with an empty system prompt.

#### Scenario: Session-backed top-level launch resolves a native selector without install
- **WHEN** an operator runs `houmao-mgr launch --agents gpu-kernel-coder --provider codex`
- **THEN** `houmao-mgr` resolves `gpu-kernel-coder` from the effective native agent-definition root for that launch
- **AND THEN** the resolved native target comes from the selected tool lane's recipe store rather than a preinstalled compatibility profile
- **AND THEN** the launch does not require prior `houmao-mgr install` or any preloaded compatibility profile state

#### Scenario: Namespaced compatibility launch accepts a brain-only native target
- **WHEN** an operator runs `houmao-mgr cao launch ...` and the resolved native launch target has no role package
- **THEN** `houmao-mgr` still launches that session-backed agent through the supported pair
- **AND THEN** the launch uses an empty system prompt instead of failing for missing role metadata

## MODIFIED Requirements

### Requirement: `houmao-mgr` reserves the top-level namespace for Houmao-owned pair commands
`houmao-mgr` SHALL reserve its top-level command namespace for Houmao-owned pair semantics.

CAO-compatible command entrypoints SHALL live only under the explicit `houmao-mgr cao ...` namespace.

Top-level CAO verbs such as `info`, `shutdown`, `init`, `flow`, `mcp-server`, and `install` SHALL NOT remain supported as top-level aliases.

Top-level `launch` MAY remain, but it SHALL be documented and implemented as a Houmao-owned pair command rather than as a top-level CAO compatibility verb.

#### Scenario: Removed top-level CAO verb is replaced by the explicit `cao` namespace
- **WHEN** an operator needs the CAO-compatible info command through `houmao-mgr`
- **THEN** the supported invocation is `houmao-mgr cao info`
- **AND THEN** `houmao-mgr` does not require top-level `info` compatibility to remain available

#### Scenario: Top-level pair launch workflow remains available after the boundary reset
- **WHEN** an operator wants the canonical pair launch workflow
- **THEN** the operator uses top-level `houmao-mgr launch`
- **AND THEN** that command is treated as Houmao-owned pair UX rather than a CAO compatibility alias

#### Scenario: Removed top-level install does not remain part of the pair workflow
- **WHEN** an operator tries to use top-level `houmao-mgr install`
- **THEN** that command is not part of the supported top-level `houmao-mgr` surface
- **AND THEN** migration guidance points the operator at native agent-definition-based launch instead of preinstalled compatibility profiles

### Requirement: `houmao-mgr` exposes a CAO-compatible command surface
The system SHALL expose a CAO-compatible command surface on a dedicated service-management binary named `houmao-mgr`.

For the supported `cao` version pinned by this capability, `houmao-mgr` SHALL accept the CAO-compatible command family under the explicit `houmao-mgr cao ...` namespace rather than as a drop-in top-level alias for `cao`.

At minimum, the CAO-compatible command family under `houmao-mgr cao` SHALL include:

- `flow`
- `info`
- `init`
- `launch`
- `mcp-server`
- `shutdown`

This capability SHALL NOT require aliasing `cao` directly to `houmao-mgr`, and it SHALL NOT require top-level `houmao-mgr` commands to preserve CAO command identity.

This capability SHALL NOT repurpose the existing `houmao-cli` binary as the CAO-compatible service-management surface.

#### Scenario: Explicit `cao` namespace accepts supported CAO-compatible command patterns
- **WHEN** an operator invokes a supported CAO-compatible command pattern through `houmao-mgr cao ...`
- **THEN** `houmao-mgr` accepts that command pattern with CAO-compatible behavior
- **AND THEN** the operator does not need top-level CAO verb compatibility to access the explicit compatibility surface

### Requirement: Session-backed compatibility commands use Houmao-owned pair authority
When a supported `houmao-mgr cao ...` command creates, inspects, mutates, or shuts down a session in the supported pair, `houmao-mgr` SHALL execute that behavior through Houmao-owned pair APIs rather than through an external `cao` subprocess.

This requirement applies at minimum to `houmao-mgr cao launch`, `houmao-mgr cao info`, and `houmao-mgr cao shutdown`.

#### Scenario: Namespaced compatibility launch uses the pair authority directly
- **WHEN** an operator runs `houmao-mgr cao launch ...` against the supported pair
- **THEN** `houmao-mgr` launches the session through Houmao-owned pair authority
- **AND THEN** it does not shell out to an external `cao` executable to complete the launch

#### Scenario: Namespaced compatibility info stays within the supported pair
- **WHEN** an operator runs `houmao-mgr cao info`
- **THEN** `houmao-mgr` reads compatibility-significant session information through Houmao-owned pair authority
- **AND THEN** the command does not require a raw `cao-server` deployment as its supported target

### Requirement: `houmao-mgr` compatibility SHALL be verified against a real `cao` CLI
The implementation SHALL include verification that compares the explicit `houmao-mgr cao ...` command surface to the pinned CAO source and exercises the compatibility commands through the Houmao-owned implementations that replace external `cao` delegation.

Where a real CAO CLI invocation remains the most direct parity oracle, verification MAY use it as an oracle. The supported product path SHALL NOT depend on that CLI being present.

That compatibility verification SHALL cover at minimum:

- command availability under the `cao` namespace
- argument parsing for the CAO-compatible command family
- script-facing exit-code and machine-readable output behavior
- pair-aware wrapper behavior where explicit pair routing replaces blind passthrough
- local compatibility-helper behavior for namespaced commands that remain local-only
- supported-pair enforcement where Houmao intentionally rejects mixed-pair usage

Houmao-owned CLI behavior SHALL be tested directly and more strictly. That verification SHALL cover at minimum:

- native headless top-level `launch --headless`
- session-backed top-level `launch` registration and runtime artifact materialization
- namespaced compatibility launch/info/shutdown through the pair
- native selector resolution for both headless and session-backed launch, including brain-only empty-prompt behavior

#### Scenario: Compatibility verification catches namespace regressions
- **WHEN** a `houmao-mgr cao` command changes in a way that breaks CAO-compatible invocation shape or compatibility-significant behavior
- **THEN** compatibility verification detects the divergence
- **AND THEN** the implementation can reject that change before claiming namespaced CAO compatibility

#### Scenario: Houmao-owned verification catches pair-command regressions
- **WHEN** a top-level or namespaced Houmao-owned command changes in a way that breaks pair launch, native selector resolution, or compatibility-wrapper behavior
- **THEN** direct Houmao behavior verification detects the regression
- **AND THEN** the implementation can reject that change even though no external `cao` subprocess is involved

## REMOVED Requirements

### Requirement: Pair-targeted install routes through `houmao-server`
**Reason**: Public install is being removed from the supported pair workflow because compatibility profile state is no longer a preinstalled operator-managed primitive.

**Migration**: Launch directly from native agent definitions through `houmao-mgr launch` or `houmao-mgr cao launch`; any compatibility profile artifacts needed by the CAO-backed transport are synthesized internally at launch time.

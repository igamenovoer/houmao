## Context

Houmao's current local and pair-managed tmux workflows are manifest-first. Runtime control, gateway attach, relaunch, and shared-registry discovery all assume there is a durable session root with a persisted manifest, gateway capability artifacts, and tmux-published discovery pointers such as `AGENTSYS_MANIFEST_PATH`.

That works for sessions launched through Houmao-owned code paths, and a similar pattern already exists for server-backed sessions that need placeholder runtime artifacts after an external launcher creates the live terminal surface. What is missing is a native local adoption flow for user-started tmux sessions, especially when the user has already launched a Codex or Claude Code TUI manually or is keeping a native headless tmux session alive between turns.

The requested `houmao-mgr agents join` command therefore needs to create the same control-plane envelope around an existing tmux session instead of inventing a separate lightweight registry-only record. That is the only way later `state`, `show`, `prompt`, `interrupt`, `gateway attach`, and `relaunch` commands can keep using the current manifest-first control model.

## Goals / Non-Goals

**Goals:**

- Adopt a user-started supported provider TUI into the same local managed-agent control plane used by native launches.
- Adopt a tmux-backed native headless logical session between turns using persisted provider resume metadata.
- Reuse the existing manifest, gateway, tmux-env, and shared-registry contracts instead of adding a join-only discovery store.
- Make required inputs explicit and fail before publication when adoption context is incomplete or inconsistent.

**Non-Goals:**

- Reconstruct the original brain build, launch recipe, or provider environment exactly as if Houmao had started the current process.
- Retroactively inject role bootstrap, mailbox skill projection, or other launch-time side effects into an already-running external process.
- Support arbitrary target windows, split-pane layouts, or cross-session adoption in v1.
- Join a mid-turn native headless worker process that is already actively streaming output.

## Decisions

### 1. Join is a manifest-first adoption flow, not a registry overlay

`houmao-mgr agents join` will create a normal runtime session root for the adopted session and will materialize the same core artifacts expected by the current control plane:

- placeholder `agent_def/` content,
- placeholder `brain_manifest.json`,
- persisted session manifest,
- session-local `gateway/` artifacts,
- tmux session environment pointers, and
- shared-registry publication.

This keeps the rest of the system unchanged. Later control paths keep resolving the same manifest-backed authority rather than learning a join-only shortcut.

The join path should not treat the placeholder `brain_manifest.json` as the source of runtime launch truth. Instead, it should construct joined-session launch-plan state directly from the join inputs:

- resolved backend and provider tool,
- working directory,
- structured launch args and launch env specs,
- headless resume-selection state when applicable.

The placeholder brain-manifest file may still exist to satisfy current artifact invariants and path expectations, but runtime control and relaunch should read the joined-session launch plan and manifest authority rather than attempting to reconstruct behavior from that placeholder file.

Alternative considered: publish only a shared-registry record and skip the session root. Rejected because the current runtime, gateway, and current-session discovery logic all rely on a persisted manifest and session-local artifacts.

### 2. V1 adopts only the current tmux session and only window `0`, pane `0`

The command will be required to run inside the target tmux session. V1 will always treat tmux window `0`, pane `0` as the canonical managed agent surface:

- for live TUI adoption, the provider process must already be running there,
- for native headless adoption, that surface represents the logical headless console between turns.

This matches the existing window-`0` contract already used by runtime-owned and pair-managed tmux sessions, and it avoids broadening the first version into arbitrary pane selection or split-pane reconciliation.

Alternative considered: support `--target-window` and `--target-pane` immediately. Rejected because it would add more tmux topology surface area than the current request needs and would complicate current-session assumptions elsewhere in the system.

### 3. TUI join auto-detects the provider; headless join uses explicit resume-selection semantics

For live TUI adoption, the command will inspect the process tree rooted at window `0`, pane `0` and detect a single supported provider (`claude_code`, `codex`, or `gemini_cli`) when `--provider` is omitted. If the caller supplies `--provider`, it must agree with the detected live process.

For live TUI adoption, the command may additionally accept repeatable `--launch-args <arg>` and repeatable `--launch-env <env-spec>` inputs. The provider executable itself remains implied by `--provider` or provider auto-detection, so these flags describe only the provider launch options that Houmao should later reuse for relaunch.

For native headless adoption, the command will require `--provider` and at least one `--launch-args <arg>`. It may also accept repeatable `--launch-env <env-spec>` entries and optional `--resume-id <selector>`. Headless join is a between-turn adoption of a logical session, not best-effort discovery of a currently running worker. `--working-directory` remains optional in both modes and will default from the primary pane current path when tmux exposes it.

`--resume-id` will have three meanings:

- omitted: do not resume a known provider chat; later headless work starts from a fresh provider session,
- `last`: resume the most current known provider chat for that tool at execution time,
- any other non-empty value: resume that exact provider-specific chat or session id.

`--launch-env` will follow Docker `--env` style for transparency:

- `NAME=value` persists a literal env binding,
- `NAME` means "inherit the current value for `NAME` from the adopted tmux session environment at relaunch time".

The intended CLI shape is:

```bash
houmao-mgr agents join \
  --agent-name <name> \
  [--agent-id <id>] \
  [--provider claude_code|codex|gemini_cli] \
  [--launch-args <arg> ...] \
  [--launch-env <env-spec> ...] \
  [--working-directory <path>]
```

For native headless adoption:

```bash
houmao-mgr agents join --headless \
  --agent-name <name> \
  [--agent-id <id>] \
  --provider claude_code|codex|gemini_cli \
  --launch-args <arg> ... \
  [--launch-env <env-spec> ...] \
  [--resume-id <provider-resume-selector>] \
  [--working-directory <path>]
```

Example values:

```bash
houmao-mgr agents join --headless \
  --agent-name reviewer \
  --provider codex \
  --launch-args exec \
  --launch-args=--json \
  --launch-env CODEX_HOME \
  --launch-env OPENAI_API_KEY \
  --resume-id last
```

Using the `--launch-args=<arg>` form is recommended when the argument itself begins with `-`, so option parsing stays unambiguous.

Alternative considered: make headless join infer provider and resume posture entirely from the tmux session alone. Rejected because tmux metadata cannot reliably identify whether the operator wants a fresh chat, the latest chat, or one exact persisted chat id.

### 4. Persist joined-session relaunch posture in manifest authority

Joined sessions need truthful restart semantics. The persisted tmux-backed relaunch authority will therefore be extended to record both session origin and the adopted relaunch posture. V1 needs at minimum these postures:

- `runtime_launch_plan`: native Houmao-built relaunch,
- `tui_launch_options`: operator-supplied launch args and Docker-style env specs for restarting a joined TUI with the provider executable implied by the persisted tool,
- `headless_launch_options`: operator-supplied headless launch args and Docker-style env specs paired with persisted provider resume selection semantics,
- `unavailable`: adopted session can be controlled while live but cannot be restarted by Houmao.

These additions should remain backward-compatible extensions of the current session manifest v4 model rather than forcing a v5 manifest split for this change. New relaunch fields should therefore be optional/defaulted, followed by regeneration of the packaged session-manifest schema and schema-consistency validation.

The relaunch posture should use an explicit tagged model via `posture_kind`. Runtime code should not infer joined-session posture from field presence alone.

This allows joined TUI sessions without any structured launch options to participate in `state`, `show`, `prompt`, `interrupt`, and `gateway attach` while still failing clearly on later relaunch attempts.

The storage split should be explicit:

- `agent_launch_authority` in the persisted session manifest is the source of truth for secret-free relaunch posture, including `posture_kind`, structured `launch_args`, structured `launch_env`, tmux session identity, and working directory.
- backend-specific manifest sections remain the source of truth for provider continuity state that is not generic relaunch posture. For native headless join, that means persisting whether later work should use no known-chat resume, `last`, or one explicit provider chat id in the provider-specific backend section such as Claude or Gemini `session_id` and Codex `thread_id`, or a tagged successor field if the model is widened.
- the tmux session environment is not a persistence store for relaunch posture. It is used only for the existing manifest-discovery pointers and for resolving deferred `--launch-env NAME` inheritance at relaunch time.
- the shared registry is not a persistence store for relaunch posture. It remains a discovery and pointer surface rather than a second copy of launch metadata.

`launch_env` should be stored structurally rather than as opaque strings:

- `NAME=value` becomes a literal binding record such as `{mode: "literal", name: "NAME", value: "value"}`,
- `NAME` becomes an inherited binding record such as `{mode: "inherit", name: "NAME"}`.

Alternative considered: store one opaque launch command string in a separate ad hoc metadata file. Rejected because relaunch already flows through manifest-backed authority, and structured args plus env specs are more transparent for operators and safer to validate than an opaque shell command.

### 5. Join owns later registry lifecycle even though the current process was user-started

After a successful join, the adopted session's shared-registry publication will be treated as runtime-owned for later refresh and teardown. The original provider process may have been started manually, but the act of joining makes Houmao responsible for the managed-agent registry lifecycle from that point onward.

That means join must publish a normal live record, gateway-capability state, and tmux discovery pointers only after all required artifacts are in place, and later runtime-managed updates must refresh that same record instead of expecting another external publisher.

Because `join` itself is a one-shot adoption command, v1 should not add a background lease-renewal daemon. The initial shared-registry publication for joined sessions should instead use a long sentinel lease so the adopted session remains discoverable until explicit `agents stop` or operator cleanup. Opportunistic lease refresh on later control commands is fine, but it should not be required for correctness.

Alternative considered: keep joined sessions permanently marked as externally published. Rejected because there is no second launcher in the join workflow that can reliably refresh gateway or stop-state changes later.

Alternative considered: spawn a background lease-renewal helper after join. Rejected because it adds new process lifecycle machinery to what should remain a one-shot adoption flow.

### 6. Joined sessions get control-plane parity, not retroactive build-time parity

The placeholder role and brain-manifest artifacts exist only to satisfy current manifest and controller invariants. They do not claim that the already-running external process was built by Houmao or that start-time bootstrap steps already ran inside that process.

This boundary should stay explicit in code and docs. The local state or detail views for joined TUI sessions should report the adopted tmux window metadata truthfully instead of assuming the launch-time `agent` window name from runtime-owned launches.

Alternative considered: attempt to reconstruct full launch-time bootstrap metadata from the live external process. Rejected because that information is either unavailable or too unreliable to turn into a contractual invariant.

## Risks / Trade-offs

- [Risk] Joined sessions will not have full build-time parity with native launches. → Mitigation: keep the contract scoped to control-plane parity, persist explicit session-origin metadata, and document that launch-time bootstrap side effects are not recreated retroactively.
- [Risk] Operator-supplied launch args or env specs may drift from reality or may still reference sensitive values. → Mitigation: persist structured launch metadata rather than an opaque command string, treat `NAME` env specs as deferred tmux-env lookups, document that explicit `NAME=value` entries should stay secret-free, and make relaunch failures explicit when the stored options no longer work.
- [Risk] Process-tree provider detection may fail for wrappers or unexpected argv shapes. → Mitigation: keep `--provider` as an explicit override for TUI join and produce clear unsupported or mismatch errors instead of guessing.
- [Risk] Partial artifact creation could leave a misleading local session root. → Mitigation: stage join publication so registry and tmux discovery pointers are written only after manifest, gateway artifacts, and identity inputs are complete, and clean up newly created partial paths on failure.
- [Risk] Long sentinel leases can leave stale joined registry records behind after operators abandon sessions. → Mitigation: keep `agents stop` and `cleanup-registry` as the explicit cleanup path, and allow later control commands to refresh the same record opportunistically without requiring a renewal daemon.

## Migration Plan

No stored-data migration is required. `houmao-mgr agents join` writes new session roots for adopted sessions only when an operator explicitly invokes the new flow.

Implementation rollout should follow this order:

1. add the CLI and tmux inspection path,
2. add joined-session launch-plan construction, artifact materialization, and manifest-schema updates,
3. wire relaunch, registry refresh, and managed-agent views through the joined-session metadata,
4. add regression tests and docs.

Rollback is straightforward: remove the join command and joined-session runtime path, then stop or delete any locally joined session roots if they are no longer needed. Existing native launch flows are unaffected.

## Open Questions

None for this change.

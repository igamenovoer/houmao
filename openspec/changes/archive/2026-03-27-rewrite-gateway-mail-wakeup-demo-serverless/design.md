## Context

The archived `gateway-mail-wakeup-demo-pack` capability still describes a demo-owned `houmao-server` plus `houmao_server_rest` session flow, a single default Codex lane, and verification centered on pair-backed artifacts. The target rewrite keeps the same teaching goal, but the operator path is now the serverless `houmao-mgr` workflow for local interactive managed agents with filesystem mailbox bindings and post-launch gateway attachment.

This change is cross-cutting because it touches the pack runner surface, generated-state layout, tracked inputs and expected report, README guidance, automated coverage, and likely some tracked fixture defaults under `tests/fixtures/agents`. The user also wants a hard ownership boundary: every generated artifact, including the mailbox root, must live under the demo pack directory and remain ignored by git.

## Goals / Non-Goals

**Goals:**
- Teach the gateway mail wake-up flow through serverless `houmao-mgr` commands rather than through demo-owned `houmao-server`.
- Support both Claude Code and Codex while keeping one live agent per run.
- Keep all generated state under `scripts/demo/gateway-mail-wakeup-demo-pack/outputs/<tool>/` by default, including mailbox state.
- Preserve the copied dummy-project and lightweight mailbox-demo fixture posture for narrow mailbox work.
- Verify the filesystem mailbox contract more directly by checking processed-message read state in addition to notifier and output-file evidence.
- Keep the demo pack runnable stepwise and automatically from its own directory.

**Non-Goals:**
- Preserving backward compatibility with the old pair-managed output layout or `tmp/demo/...` roots.
- Running Claude Code and Codex concurrently in one shared live run.
- Changing the general mailbox or gateway protocol; this change only rewrites the demo around existing contracts.
- Keeping the existing artifact names or helper-script layout if a module-based demo implementation is cleaner.

## Decisions

### Use the public serverless `houmao-mgr` workflow as the demo control plane

The pack will drive lifecycle steps through `houmao-mgr mailbox init`, `houmao-mgr agents launch`, `houmao-mgr agents mailbox register`, `houmao-mgr agents gateway attach`, `houmao-mgr agents gateway mail-notifier enable`, `houmao-mgr agents mail ...`, and `houmao-mgr agents stop` instead of demo-owned `houmao-server`.

This keeps the demo aligned with the operator-facing serverless path the repository now wants to teach. It also removes the need to explain pair authority, server ownership, and `houmao_server_rest` just to show one mail wake-up example.

Alternative considered:
- Reusing runtime-internal Python APIs directly. Rejected because that would hide the actual operator contract the demo is supposed to teach.

### Keep one selected tool per run and add an explicit matrix path for both tools

The rewritten pack will require tool selection for startup and automatic runs, with supported values `claude` and `codex`. A higher-level matrix path can run both sequentially, but each live run owns exactly one agent and one output root.

This keeps the demo simple, keeps artifacts attributable to one provider, and matches the desired “same purpose, same functionality” scope better than a two-agent orchestration.

Alternative considered:
- Launching both tools in one run. Rejected because it complicates ownership, reporting, and failure analysis without adding new teaching value.

### Make the demo directory the hard ownership boundary for all generated state

The default generated-state roots will live under `scripts/demo/gateway-mail-wakeup-demo-pack/outputs/<tool>/`. The pack will redirect runtime, registry, mailbox, and jobs roots into that selected output root so no generated state lands in operator defaults outside the pack.

This decision directly matches the stated requirement that every output artifact, including the filesystem mailbox root, must live in the demo directory and be ignored locally by git.

Alternative considered:
- Continuing to use `tmp/demo/...` or a repo-global temp root. Rejected because it weakens ownership, makes inspection harder, and conflicts with the requested containment model.

### Use gateway-owned state plus mailbox-local read-state as the authoritative verification boundary

The demo will treat the attached gateway’s runtime-owned artifacts and tracked state as the authoritative observer for local interactive prompt lifecycle evidence. Verification will also inspect mailbox-local read-state so the demo proves the processed unread message was actually completed through the filesystem mailbox contract.

Concretely, the verification contract should combine:
- gateway status and notifier status,
- durable notifier audit history in `queue.sqlite`,
- gateway event and log artifacts,
- mailbox-local SQLite state under the demo-owned mailbox root,
- the demo-owned output file.

Alternative considered:
- Continuing to treat output-file creation plus unread-mail presence as sufficient. Rejected because it proves wake-up side effects but not completion of the filesystem mailbox action contract.

### Keep operator-side mail injection on the managed filesystem delivery boundary

The pack will continue to stage canonical Markdown mail and commit delivery through the managed filesystem mailbox boundary rather than mutating SQLite directly.

This preserves the narrow contract the demo is meant to teach: unread filesystem mail exists, the notifier detects it, the gateway wakes the agent, and the session completes the later mailbox work through supported mailbox and gateway contracts.

Alternative considered:
- Shortcutting injection through direct SQLite writes. Rejected because it bypasses the mailbox transport boundary and would make the demo less honest.

### Decouple live demo credential selection from the old single-lane defaults

The archived pack is tied to a single Codex default lane. The rewrite will need explicit tracked serverless defaults for both Claude and Codex under `tests/fixtures/agents`, with the demo reading those tool-specific defaults instead of assuming one lane.

The implementation can satisfy that either by adding dedicated demo-facing recipe or blueprint variants or by refactoring the selected existing fixture definitions. The important design point is that the live credential and config choices stay in `tests/fixtures/agents`, not in pack-local secrets.

Alternative considered:
- Hard-coding pack-local credential behavior. Rejected because the repository’s fixture model already makes `tests/fixtures/agents` the source of truth.

## Risks / Trade-offs

- [Provider readiness differs between Claude and Codex] → Mitigation: keep tool-specific readiness polling and persist explicit inspect artifacts for failed startup and failed wake-up runs.
- [The archived spec and tests assume pair-managed artifacts] → Mitigation: update all conflicting requirement blocks and rewrite the report contract instead of layering compatibility shims on top.
- [Generated outputs accumulate under the pack directory] → Mitigation: use tool-scoped output roots, a pack-local `.gitignore`, and explicit stop or cleanup behavior.
- [Fixture defaults may drift from the live credential profiles expected for real-agent testing] → Mitigation: add preflight checks and keep tool-specific tracked defaults under `tests/fixtures/agents` rather than relying on ambient operator state.
- [Gateway and mailbox state can race immediately after delivery] → Mitigation: poll gateway status, notifier status, mailbox read-state, and output-file state with bounded waits and persist the raw intermediate artifacts for diagnosis.

## Migration Plan

1. Replace the old pack runner and helper layout with the new serverless runner surface while keeping the same pack path under `scripts/demo/gateway-mail-wakeup-demo-pack/`.
2. Move default generated outputs from `tmp/demo/...` to pack-local `outputs/<tool>/`.
3. Rewrite tracked inputs, expected report, README, and tests around the serverless flow.
4. Treat previously generated pair-managed output roots as stale. The rewritten pack should fail clearly or reprovision rather than silently mixing old and new layouts.
5. If the rewrite needs new tracked Claude/Codex demo defaults under `tests/fixtures/agents`, add them before switching the pack to those defaults.

Rollback is straightforward because this is a demo-pack rewrite rather than a data migration: revert the change set and remove the new pack-local outputs.

## Open Questions

- Should the pack keep a single `auto` command that requires `--tool`, or should `auto` implicitly run a two-tool matrix? Current recommendation: keep `auto --tool <claude|codex>` and add a separate matrix command for both-tool coverage.
- Should the tracked live defaults reuse the existing `mailbox-demo-*` fixture names or introduce demo-specific selectors? Current recommendation: keep the lightweight mailbox-demo role family but allow new demo-specific selectors if that is the cleanest way to express tool-specific serverless credential defaults.

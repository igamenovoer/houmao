## Context

This repo launches Claude Code sessions in two primary ways:

- Headless Claude sessions (`backend=claude_headless`) run `claude -p ...` as a subprocess with an environment derived from the caller process plus allowlisted credential-profile variables.
- CAO-backed Claude sessions (`backend=cao_rest`, `provider=claude_code`) create a tmux session, inherit the full caller environment, overlay the credential env file, apply brain-owned overlays, and rely on CAO’s Claude Code provider to launch `claude` inside tmux.

Today, neither path explicitly sets `--model`, so Claude Code uses its own default model selection. For “full pipeline” tests and reproducible behavior, we need a deterministic way to select Opus (or pin a specific Opus version) without patching CAO internals.

Upstream Claude Code supports model selection via environment variables (and documents precedence among `/model`, `--model`, env vars, and settings). We will adopt those upstream controls and make sure our runtime preserves them consistently.

## Goals / Non-Goals

**Goals:**

- Support selecting the Claude Code model for orchestrated sessions using Claude Code’s environment-variable configuration (primarily `ANTHROPIC_MODEL`, optional `ANTHROPIC_SMALL_FAST_MODEL`, optional alias pinning vars like `ANTHROPIC_DEFAULT_OPUS_MODEL`, and optional `CLAUDE_CODE_SUBAGENT_MODEL`).
- Ensure the model selection configuration works for both:
  - `backend=claude_headless` (subprocess env composition), and
  - `backend=cao_rest` (tmux session env propagation).
- Document how to run a CAO-backed Claude agent with Opus enabled using env vars.
- Add tests that validate our “env propagation + allowlist” behavior without requiring live API calls.

**Non-Goals:**

- Adding a new first-class CLI flag like `start-session --model ...` (we can consider later; the requested mechanism is env-based).
- Modifying CAO’s Claude provider to pass `--model` (we’ll avoid this by relying on upstream env var support).
- Proving end-to-end model usage via network calls in CI (tests should be hermetic).

## Decisions

- Decision: Use Claude Code’s env-based model selection as the supported mechanism.
  - Rationale: avoids CAO provider patching and works for both CAO-backed interactive and headless invocations.
  - Primary control: `ANTHROPIC_MODEL` (set to an alias like `opus` or a fully qualified model name).
  - Optional pinning: `ANTHROPIC_DEFAULT_OPUS_MODEL` (and related `*_MODEL` vars) to pin what an alias resolves to.
  - Optional small/fast model pinning: `ANTHROPIC_SMALL_FAST_MODEL` (when unset, Claude Code defaults apply).
  - Optional subagent pinning: `CLAUDE_CODE_SUBAGENT_MODEL`.

- Decision: Expand the Claude credential env allowlist to include model-selection variables (including `ANTHROPIC_MODEL`, `ANTHROPIC_SMALL_FAST_MODEL`, `ANTHROPIC_DEFAULT_*_MODEL`, and `CLAUDE_CODE_SUBAGENT_MODEL`).
  - Rationale: headless launches currently read allowlisted variables from the credential profile env file into the subprocess env; without allowlisting, setting model vars in `agents/brains/api-creds/claude/<profile>/env/vars.env` would not take effect for `backend=claude_headless`.
  - CAO-backed launches already overlay the credential env file into tmux session env; keeping the allowlist expansion still improves consistency and reduces surprise across backends.

- Decision: Keep the optional interactive harness script under dedicated pipeline-harness work (see `openspec/changes/interactive-pipeline-test`), rather than duplicating scripts in this change.
  - Rationale: this change is an env propagation + docs/tests contract; the interactive harness is a separate DX artifact.

## Risks / Trade-offs

- Risk: Upstream Claude Code changes env var names/precedence. -> Mitigation: keep this change small, document which upstream vars we rely on, and add unit tests for our allowlist/env propagation so regressions are localized.
- Risk: Credential env policy differs between tmux-isolated CAO sessions (full credential env overlay) and headless launches (allowlist-gated injection). -> Mitigation: expand allowlist for Claude to include model vars and document the difference clearly.
- Risk: Users may want per-session overrides even if credential profile pins a model. -> Mitigation: document that tmux env follows the platform precedence policy (caller env base, credential env overlay), and consider a future `--model` flag that maps to `ANTHROPIC_MODEL` as a higher-precedence launch overlay for explicit per-run overrides.

## Migration Plan

- No data migrations.
- Safe incremental rollout:
  - Update allowlist + docs first.
  - Add tests.
- Rollback: revert allowlist changes and docs; no stateful artifacts are introduced.

## Open Questions

<!-- None -->

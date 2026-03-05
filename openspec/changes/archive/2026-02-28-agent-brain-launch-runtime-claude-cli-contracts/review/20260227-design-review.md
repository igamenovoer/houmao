# Design Review: agent-brain-launch-runtime-claude-cli-contracts

**Reviewer:** Claude (explore mode)
**Date:** 2026-02-27
**Artifacts reviewed:** proposal.md, design.md, tasks.md, specs/claude-cli-noninteractive-startup/spec.md, specs/component-agent-construction/spec.md
**Codebase cross-referenced:** cao_rest.py, headless_base.py, claude_headless.py, claude.yaml adapter, cli-configs/claude/default/, api-creds/claude/personal-a-default/

**Note (2026-02-28):** Subsequent decisions were captured in `discuss/discuss-open-questions.md` and the change artifacts were updated accordingly; this review reflects the pre-decision state as of 2026-02-27.

---

## Executive Summary

The change correctly identifies and addresses a real, well-diagnosed problem: Claude Code v2.x interactive first-run flows blocking non-interactive orchestrated sessions. The design is grounded in actual debugging evidence (three rounds of code review logs) and the proposed contracts are reasonable. However, the design has several gaps between the stated contracts and the current implementation, some internal contradictions, and open questions that deserve concrete answers before implementation proceeds.

**Verdict:** Sound in intent, needs refinement in specifics. The issues below range from structural gaps to minor inconsistencies.

---

## Issue 1: Bootstrap Helper Scope Mismatch (Implementation vs. Design)

### The Problem

Design Decision 3 says:
> Implement a shared helper in the brain launch runtime that prepares a Claude home (seed files + validate required settings) and call it from each backend that launches Claude.

Task 1.3 says:
> Invoke the bootstrap helper from all Claude launch paths (`cao_rest`, `claude_headless`, and any direct launcher entrypoints)

But the current implementation (`_seed_claude_home_config` in `cao_rest.py`) is:
1. **Private to the CAO backend** — defined as a module-level private function in `cao_rest.py`
2. **Not called from `claude_headless`** — the headless backend at `headless_base.py:60` does `env = os.environ.copy(); env.update(self._plan.env); env[self._plan.home_env_var] = str(self._plan.home_path)` with no `.claude.json` seeding
3. **Only handles `.claude.json`** — doesn't validate that `settings.json` exists or is correct

### Why It Matters

The headless backend (`claude -p`) also sets `CLAUDE_CONFIG_DIR` to a fresh home. If `claude -p` ever triggers onboarding flows (plausible — the CLI may still read `.claude.json` even in pipe mode), the headless path silently breaks while the CAO path works. This is exactly the "backend drift" the design warns about.

### Recommendation

The design is right; the implementation hasn't caught up. The shared helper should:
- Live in a shared location (e.g., a `claude_bootstrap.py` module under `backends/` or at the `brain_launch_runtime` package level)
- Be called from both `CaoRestSession._start_terminal()` and `ClaudeHeadlessSession.__init__()` (or `send_prompt()` before first turn)
- Validate both `.claude.json` materialization AND `settings.json` presence

---

## Issue 2: `.claude.json` Template vs. Generation — Unclear Boundary

### The Problem

The design says (Decision 2):
> Store a `.claude.json` template in Claude credential profiles under `agents/brains/api-creds/claude/<cred-profile>/...`

But the current `_seed_claude_home_config()` generates `.claude.json` from scratch — it doesn't read any template. The credential profile `personal-a-default/files/` contains only an empty `credentials.json` (`{}`). There is **no `.claude.json` template file anywhere** in the repository today.

This creates a question: **what's actually in the template vs. what's in the overlay?**

The design mentions the template may contain `mcpServers` entries. But the spec says:
> Materialized runtime config preserves template MCP settings

If the template is just `{}` (or doesn't exist yet), the "merge template + overlay" logic is indistinguishable from "generate from scratch." The template concept only adds value if there are real profile-specific entries (MCP servers, custom settings, etc.) that differ across credential profiles.

### Recommendation

Clarify in the design:
1. **What concrete fields does the template carry** that differ from the overlay? If the answer is "nothing yet, but MCP servers in the future," say so explicitly and document that the initial template may be empty or minimal.
2. **Where exactly does the template file live?** The proposal says `agents/brains/api-creds/claude/<cred-profile>/...` but doesn't name the file. Is it `files/.claude.json`? A new `templates/` directory? This needs to be explicit. Suggestion: `agents/brains/api-creds/claude/<cred-profile>/templates/claude.json` (distinct name to avoid confusion with the runtime artifact).
3. **What happens if the template file doesn't exist?** The spec says "fail with a clear configuration error." But the current code silently generates from scratch. These are contradictory behaviors. Pick one: fail-fast (strict, safer) or fall-back-to-empty (pragmatic, easier migration).

---

## Issue 3: Proxy Env Inheritance Design vs. Current Implementation

### The Problem

The design says (Decision 4):
> Proxy-related environment variable inheritance from the calling process SHALL be disabled by default

But the current implementation (`_forwarded_process_env()` in `cao_rest.py`) **always** forwards proxy vars with no opt-out. There's no `launch.inherit_proxy_env` flag in the tool adapter, no `AGENTSYS_BRAIN_INHERIT_PROXY` parsing, and `_forwarded_process_env()` is unconditionally called in `_start_terminal()`.

This means the design proposes a **behavioral regression from the current implementation** (proxy forwarding currently works, and the design wants to disable it by default).

### Why It Matters

This was a real bug that was fixed (the proxy env forwarding was added specifically to make CAO work in proxied environments). Changing the default to "off" risks re-breaking users who depend on it. The design acknowledges this ("can be impractical in proxied environments") but the migration path isn't clear.

### Recommendation

The design should explicitly address the migration:
1. **Is the plan to break the current default and then require users to set `AGENTSYS_BRAIN_INHERIT_PROXY=1`?** If so, document the migration step clearly.
2. **Or should the initial default be "on" (matching current behavior) with the option to turn it off?** This is safer but contradicts the design's stated preference for determinism.
3. Consider: maybe the first release keeps the current behavior (always forward) and the tool-adapter flag is added as an opt-out. A follow-up change flips the default once the credential-profile env injection path (task 2.4) is proven.

---

## Issue 4: `_FORWARDED_ENV_NAMES` Includes Non-Proxy Variables

### The Problem

The spec explicitly enumerates proxy variables:
> Proxy-related environment variables are: `http_proxy`, `HTTP_PROXY`, `https_proxy`, `HTTPS_PROXY`, `all_proxy`, `ALL_PROXY`, `no_proxy`, `NO_PROXY`.

But `_FORWARDED_ENV_NAMES` in `cao_rest.py` includes five additional variables:
```python
"SSL_CERT_DIR", "SSL_CERT_FILE",
"REQUESTS_CA_BUNDLE",
"CURL_CA_BUNDLE",
"NODE_EXTRA_CA_CERTS",
```

These are TLS/CA certificate variables, not proxy variables. The design and spec don't mention them at all. Should they:
- Be governed by the same `inherit_proxy_env` flag? (Confusing — they're not proxy vars.)
- Have their own inheritance flag? (More correct but more complex.)
- Always be forwarded? (Pragmatic — TLS certs are rarely environment-specific in the same way proxies are.)
- Be injected via the credential profile env? (Most deterministic.)

### Recommendation

Add TLS/CA variables to the spec's enumeration or create a separate category. They're arguably more important than proxy vars — if you strip TLS CA bundles, API calls fail with certificate verification errors even without a proxy. The simplest fix: expand the spec's variable list to include them, or split into two categories (`proxy` and `tls`) with the same inheritance behavior.

---

## Issue 5: Spec Duplicates Proxy Requirements Across Two Delta Specs

### The Problem

Proxy env inheritance requirements appear in both:
- `specs/claude-cli-noninteractive-startup/spec.md` (5 scenarios covering all proxy behavior)
- `specs/component-agent-construction/spec.md` (4 scenarios covering the same proxy behavior)

The `component-agent-construction` delta spec defines proxy inheritance in terms of "tool adapters" and "tmux-based launches" generically. The `claude-cli-noninteractive-startup` spec defines it specifically for "Claude sessions in tmux." But the behavior is identical.

### Why It Matters

When these delta specs are synced to main specs, both will carry overlapping requirements. Future readers must reconcile whether the tool-adapter-level spec and the Claude-specific spec are the same or different. Maintainers updating one may forget to update the other.

### Recommendation

Proxy env inheritance is a **platform-level** concern (it applies to any tool launched via tmux, not just Claude). The canonical requirement should live in `component-agent-construction` spec only. The `claude-cli-noninteractive-startup` spec should reference it rather than restate it.

---

## Issue 6: Task 2.4 Is Underspecified

### The Problem

Task 2.4 says:
> If proxy env vars are needed without inheritance, support declaring them via the Claude brain credential profile (adapter allowlist + env injection)

This is vague. The current credential profile `env/vars.env` only allowlists `ANTHROPIC_API_KEY` and `ANTHROPIC_BASE_URL` (per `claude.yaml`). Adding proxy vars to the credential profile means:
1. Adding them to `vars.env` in each credential profile
2. Adding them to the `allowlist` in `claude.yaml`

But the design says proxy vars are "not tool-specific" — they're environment infrastructure. Putting `http_proxy` in a **Claude** credential profile is semantically wrong (it's not a Claude credential). Putting it in the tool adapter allowlist is also odd.

### Recommendation

Consider a separate mechanism for infrastructure env vars:
- A `brain-wide` or `environment` env file that applies to all tools (not per-credential-profile)
- Or: document that the allowlist in `claude.yaml` should be extended with proxy var names when needed, and the proxy values go in `vars.env` alongside the API key
- Or: accept the semantic impurity as pragmatic and document it

---

## Issue 7: Missing `--dangerously-skip-permissions` in Headless Backend

### The Problem

Task 2.1 says:
> Ensure orchestrated Claude launches include a non-interactive bypass mechanism (for example `--dangerously-skip-permissions`)

The CAO backend relies on the CAO `claude_code` provider to pass `--dangerously-skip-permissions`. But looking at `claude_headless.py`, the headless backend's `_bootstrap_args()` only returns `--append-system-prompt` — it does NOT include `--dangerously-skip-permissions` or `-p` (which implies `--no-interactive`).

The `-p` flag may implicitly disable permission prompts (headless mode), but this isn't stated. If it doesn't, the headless backend has the same prompt-blocking risk.

### Recommendation

Verify whether `claude -p` mode suppresses all interactive prompts by design. If yes, document this assumption explicitly. If no, add `--dangerously-skip-permissions` to the headless bootstrap args as well.

---

## Issue 8: `numStartups: 1` — Fragile Assumption

### The Problem

`_seed_claude_home_config()` writes `"numStartups": 1` into `.claude.json`. This field is not mentioned anywhere in the design, proposal, or spec. It was added based on reverse-engineering Claude Code's behavior.

### Why It Matters

If Claude Code uses `numStartups` to gate behavior (e.g., showing tips after N startups, or triggering re-onboarding after a version upgrade), hardcoding `1` could cause unexpected behavior. The spec should either:
- Explicitly include `numStartups` as a required field with rationale, or
- Remove it and verify Claude Code works without it

### Recommendation

Document why `numStartups: 1` is set. If it's not required for non-interactive startup, remove it. If it is required, add it to the spec's materialization requirements alongside `hasCompletedOnboarding`.

---

## Issue 9: No Versioning or Compatibility Contract

### The Problem

The design's risk section mentions:
> **[Claude Code changes bootstrap keys/paths]** → Mitigation: keep bootstrap minimal, version-pin assumptions in tests/docs

But there's no actual version pinning. The spec says the bootstrap contract may evolve as upstream behavior changes, and the non-goal explicitly disclaims future compatibility. Yet there's no:
- Record of which Claude Code version the current assumptions are based on (the issue doc mentions v2.1.62, but neither the spec nor the design does)
- Test that validates the assumed `.claude.json` schema against the actual Claude Code binary
- Mechanism to detect when assumptions break

### Recommendation

Add to the design or spec:
1. A comment or metadata field recording the assumed Claude Code version (currently v2.1.62 based on the issue analysis)
2. A test (even a manual one) that launches Claude Code with the seeded config and verifies non-interactive startup
3. Task 4.2 (the end-to-end demo run) partially covers this but should explicitly assert "no interactive prompts were shown"

---

## Answers to Open Questions

### OQ1: Should the bootstrap helper be invoked for all Claude launchers (including headless/pipe-mode flows), or only for interactive/orchestrated sessions?

**Proposed answer: Yes, for all Claude launchers.**

Rationale:
- `claude -p` still reads `$CLAUDE_CONFIG_DIR/.claude.json` and may trigger onboarding in future versions
- The cost of seeding is trivial (one JSON file write)
- Backend drift is a stated risk — the best mitigation is making bootstrap universal
- If `claude -p` truly doesn't need it, the seeding is harmless
- The headless backend already sets `CLAUDE_CONFIG_DIR` to a fresh home, so it's already in the blast zone

### OQ2: Do we want a single canonical "orchestrated Claude launch command" definition (flags + defaults) in one place, or is it acceptable to keep part of it in the vendored CAO provider?

**Proposed answer: Keep the CAO provider's command as-is, but codify the invariants separately.**

Rationale:
- The CAO `claude_code` provider owns `claude --dangerously-skip-permissions` (the actual command). This is an implementation detail of the provider.
- What matters for the contract is the **invariants**: "the launched Claude process MUST have `--dangerously-skip-permissions` (or equivalent), a seeded `.claude.json`, and `settings.json` with `skipDangerousModePermissionPrompt: true`."
- These invariants should be documented in the spec (they mostly are already).
- Trying to unify the command across backends is impractical — the headless backend uses `claude -p --resume`, the CAO provider uses `claude --dangerously-skip-permissions`, and they have different flag sets.
- A shared constant or helper for common flags could reduce drift, but it's not a hard requirement now.

### OQ3: Should we capture an explicit upstream Claude Code version compatibility matrix in docs/tests?

**Proposed answer: Yes, lightweight. Not a formal matrix, but a documented assertion.**

Rationale:
- A full compatibility matrix is overkill for one tool's config format
- But the current assumptions (onboarding keys, API key suffix format, settings.json path) are version-specific
- Document the tested Claude Code version in:
  1. The design doc (e.g., "Verified against Claude Code v2.1.62")
  2. A comment in the bootstrap helper source code
  3. The end-to-end demo test output
- When Claude Code updates, the demo script serves as the compatibility smoke test
- If we want to get fancier later, a `claude --version` check in the bootstrap helper could warn if the version is untested

---

## Additional Open Questions (Newly Identified)

### NEW-OQ1: What is the merge strategy for `.claude.json` template + overlay?

The spec says "preserve template `mcpServers` entries unless explicitly overridden." But what about other fields? Is this:
- **Shallow merge** (overlay keys replace template keys at top level)
- **Deep merge** (nested objects are merged recursively)
- **Selective overlay** (only specific keys are overridden, everything else preserved)

This matters because `.claude.json` may contain nested structures like:
```json
{
  "mcpServers": { ... },
  "customApiKeyResponses": { "approved": [...] },
  "projects": { ... }
}
```

If the overlay sets `customApiKeyResponses`, does it replace the entire object or merge into it? The design should specify the merge semantics explicitly.

**Proposed answer:** Shallow merge at top level. The overlay produces a small set of top-level keys (`hasCompletedOnboarding`, `customApiKeyResponses`, `numStartups`). These replace the template values. All other template keys are preserved as-is. This is the simplest correct behavior and matches what `_seed_claude_home_config` effectively does today (starts empty, which is equivalent to "template is `{}`").

### NEW-OQ2: Should the credential profile template be gitignored or tracked?

The credential profile directory (`agents/brains/api-creds/`) is gitignored (it contains secrets in `vars.env`). But the `.claude.json` template may contain no secrets (just MCP server configs, etc.). Should it be:
- Gitignored (consistent with the rest of the cred profile directory)
- Tracked (it contains no secrets and is useful to share across machines)
- Mixed (template tracked via an explicit git include rule, env file still ignored)

**Proposed answer:** Keep it gitignored for now (consistency with the credential profile convention). If sharing templates across machines becomes a need, extract the non-secret parts to a separate tracked location (e.g., `cli-configs/` or a new `templates/` directory under `agents/brains/`). The credential profile should only contain credential-adjacent material.

### NEW-OQ3: What happens to `_forwarded_process_env()` during the transition?

Today, `_forwarded_process_env()` unconditionally forwards proxy + TLS vars. The design wants to make this configurable with default=off. But:
1. Task 2.2 adds the tool-adapter flag
2. Task 2.3 adds the env override
3. Task 2.4 adds credential-profile-based injection

These three tasks must be implemented atomically or in the right order, or there's a window where proxy forwarding is removed but no replacement is available.

**Proposed answer:** Implement in this order:
1. First, add the tool-adapter flag with default=**true** (preserves current behavior)
2. Add `AGENTSYS_BRAIN_INHERIT_PROXY` parsing (allows per-run override)
3. Add credential-profile env injection for proxy vars (provides the deterministic alternative)
4. Finally, flip the default to **false** once the alternative path is proven

This avoids a regression window.

### NEW-OQ4: Does the bootstrap helper need to handle concurrent launches?

If two sessions are constructed from the same credential profile simultaneously, and both try to materialize `.claude.json` into separate fresh homes, there's no conflict (each home is unique). But if for some reason the same home path is reused (shouldn't happen, but worth confirming), concurrent writes to `.claude.json` could race.

**Proposed answer:** Not a concern currently. `build_brain_home()` generates UUID-stamped home directories, so concurrent launches always get different paths. The `claude_json_path.exists()` early-return in `_seed_claude_home_config()` is a reasonable guard. No additional synchronization needed.

### NEW-OQ5: Should `settings.json` be part of the bootstrap helper's responsibility?

Currently, `settings.json` is projected via `config_projection` during brain construction (handled by `brain_builder.py`). The bootstrap helper (`_seed_claude_home_config`) only handles `.claude.json`. This means:
- `settings.json` correctness depends on the config profile contents (static, set by the developer)
- `.claude.json` correctness depends on the bootstrap helper (dynamic, computed at launch)

The design says the bootstrap helper should "prepare a Claude home (seed files + validate required settings)." Should the helper also **validate** that `settings.json` exists and contains `skipDangerousModePermissionPrompt: true`?

**Proposed answer:** Yes, the bootstrap helper should validate (not create) `settings.json`. The file is already projected by the brain builder, so the helper doesn't need to create it. But a quick validation check (`settings.json` exists and contains the required key) provides defense-in-depth and catches misconfigurations early with a clear error message.

---

## Summary of Issues

| # | Severity | Issue | Status |
|---|----------|-------|--------|
| 1 | High | Bootstrap helper is CAO-private, not shared | Gap between design and implementation |
| 2 | Medium | Template file location and empty-template behavior undefined | Design underspecified |
| 3 | Medium | Default proxy=off is a regression from current proxy=always-on | Migration path missing |
| 4 | Low | TLS/CA vars not covered in spec | Spec incomplete |
| 5 | Low | Proxy requirements duplicated across two specs | Maintainability concern |
| 6 | Medium | Task 2.4 mechanism underspecified | Task vague |
| 7 | Medium | Headless backend may need `--dangerously-skip-permissions` | Unverified assumption |
| 8 | Low | `numStartups: 1` undocumented in spec | Fragile implicit behavior |
| 9 | Low | No Claude Code version pinning | Risk mitigation gap |

## Summary of Open Question Answers

| Question | Proposed Answer |
|----------|----------------|
| OQ1 (bootstrap for all launchers?) | Yes, all Claude launchers |
| OQ2 (canonical launch command?) | Keep backend-specific commands, codify shared invariants |
| OQ3 (version compatibility matrix?) | Lightweight — documented version + demo as smoke test |
| NEW-OQ1 (merge strategy?) | Shallow merge at top level |
| NEW-OQ2 (template gitignored?) | Yes, gitignored for now (consistency) |
| NEW-OQ3 (transition order?) | Add flag default=on first, then flip after alt path proven |
| NEW-OQ4 (concurrent launches?) | Not a concern — UUID homes prevent races |
| NEW-OQ5 (validate settings.json?) | Yes, validate (not create) in bootstrap helper |

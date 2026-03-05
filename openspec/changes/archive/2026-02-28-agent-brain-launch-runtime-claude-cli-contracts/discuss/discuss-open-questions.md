# Claude CLI Contracts: Open Questions Discussion

Date: 2026-02-27

This note collects open questions and underspecified points for the `agent-brain-launch-runtime-claude-cli-contracts` change. The goal is to converge crisp decisions that can be captured back into [design.md](../design.md), [tasks.md](../tasks.md), and the delta specs under [specs/](../specs/).

Primary references:
- [proposal.md](../proposal.md)
- [design.md](../design.md)
- [specs/claude-cli-noninteractive-startup/spec.md](../specs/claude-cli-noninteractive-startup/spec.md)
- [specs/component-agent-construction/spec.md](../specs/component-agent-construction/spec.md)
- [review/20260227-design-review.md](../review/20260227-design-review.md)

## Ground Truth Snapshot (Current Repo State)

- `agents/brains/cli-configs/claude/default/settings.json` exists and sets `skipDangerousModePermissionPrompt: true`.
- `src/agent_system_dissect/agents/brain_launch_runtime/backends/cao_rest.py` seeds `$CLAUDE_CONFIG_DIR/.claude.json` if missing (`hasCompletedOnboarding`, `numStartups`, and `customApiKeyResponses` derived from `ANTHROPIC_API_KEY` suffix).
- `src/agent_system_dissect/agents/brain_launch_runtime/backends/cao_rest.py` forwards proxy plus TLS/CA env vars into tmux unconditionally (via `_FORWARDED_ENV_NAMES`).
- `src/agent_system_dissect/agents/brain_launch_runtime/backends/claude_headless.py` runs Claude in headless mode, and `build_launch_plan()` injects `-p` for `claude_headless`, but there is no `.claude.json` seeding on the headless path today.
- `agents/brains/tool-adapters/claude.yaml` allowlists only `ANTHROPIC_API_KEY` and `ANTHROPIC_BASE_URL`.
- `agents/brains/tool-adapters/claude.yaml` defines no `credential_projection.file_mappings` (so credential-profile files are not projected into the runtime home).

Implication: the change artifacts describe contracts that diverge from current behavior in a few places (template-required vs generate-from-scratch; full caller-env inheritance for tmux vs the current curated forwarding list; credential-profile file mappings not yet defined in the tool adapter).

## Open Questions And Recommendations

### 1) Bootstrap Helper Scope: All Claude Launchers or Orchestrated Only?

Question: Should the Claude home bootstrap/validation logic be invoked for all Claude launchers (`cao_rest`, `claude_headless`, and any future backend), or only for tmux-orchestrated runs?

Option A: All Claude launchers. Pros: avoids backend drift; aligns with Design Decision 3 and Task 1.3; future-proofs against headless mode changing behavior; seeding cost is tiny. Cons: requires clarifying how the template is located for non-CAO launchers; may add validation failures for users who only use headless.

Option B: CAO/tmux only. Pros: minimal scope; avoids affecting the default Claude backend (`claude_headless`) until proven necessary. Cons: reintroduces drift risk; contradicts the stated design intent; encourages future bugs when new backends appear.

> RECOMMENDATION: Invoke the bootstrap helper for all Claude launchers, but keep it narrowly scoped (materialize `.claude.json` when needed and validate `settings.json` exists and contains `skipDangerousModePermissionPrompt: true`).

> **DECISION: Option A — All Claude launchers.**
> Agree with the recommendation. The code confirms the drift risk is real: `cao_rest.py` has `_seed_claude_home_config` as a private function while `claude_headless.py` does zero config seeding. Even though `-p` (headless) currently suppresses onboarding, this is an unverified assumption about upstream behavior. The seeding cost is near-zero (one JSON write), and extracting a shared helper to a common module (e.g., `brain_launch_runtime/claude_bootstrap.py`) is straightforward. The "validation failures for headless-only users" concern is mitigated by accepting an empty `{}` template as valid (see Q3). This is cheap insurance against backend drift and upstream behavior changes.

### 2) `.claude.json` Template: Exact Location, Naming, and Discovery at Launch Time

Question: Where exactly does the credential-profile `.claude.json` template live, what is its filename, and how does launch-time code find it?

Option A: Keep template in the credential profile and project it into the runtime home under a non-conflicting name (via `credential_projection.file_mappings`). Pros: launch-time code can locate the template relative to `home_path` without needing to thread credential-profile paths through the launch plan; template remains local-only because api-creds stays uncommitted; works for both CAO and headless. Cons: requires a new adapter mapping and a decision on template destination path; template becomes a file inside the runtime home (still secret-free if we enforce that).

Option B: Keep template only in the credential profile and read it from the credential profile directory at launch time. Pros: template never lands in the runtime home; no adapter mapping needed. Cons: current `LaunchPlan` does not surface `credentials.profile_path`; implementation would need to derive it indirectly (e.g., from the env source file path) or add new launch-plan metadata; more fragile and harder to test hermetically.

Option C: Do not support templates (generate from scratch). Pros: simplest and matches current `cao_rest.py` behavior. Cons: contradicts the change’s stated goal of supporting profile-specific state (e.g., MCP server config) while keeping launch invariants enforced.

> RECOMMENDATION: Option A. Define the template file as a local-only credential-profile input (stored under `agents/brains/api-creds/claude/<cred-profile>/files/`), but map it into the runtime home as something like `claude_state.template.json` (not `.claude.json`) so the bootstrap helper can read it and then write the actual `$CLAUDE_CONFIG_DIR/.claude.json`.

> **DECISION: Option A — Project template into runtime home under a non-conflicting name.**
> Agree with the recommendation. The key insight from the code is that `LaunchPlan` does not expose `credentials.profile_path`, making Option B fragile. Option C (generate from scratch) is what exists today and works, but blocks the stated goal of supporting profile-specific MCP server configs. Option A threads the needle: the template stays in the local-only `api-creds/` tree (never committed), gets projected via `credential_projection.file_mappings` into the runtime home as `claude_state.template.json`, and the bootstrap helper reads it there. This requires adding a `file_mappings` entry to `claude.yaml` — a small, clean change. The non-conflicting name (`claude_state.template.json`) is important to avoid the create-vs-update ambiguity in Q6. Concrete path: `agents/brains/api-creds/claude/<cred-profile>/files/claude_state.template.json` → projected to `$CLAUDE_CONFIG_DIR/claude_state.template.json`.

### 3) Missing Template Behavior: Fail Fast, Fallback, or Hybrid?

Question: What should happen when the selected credential profile does not provide a template?

Option A: Fail fast with a clear configuration error (as the delta spec currently states). Pros: makes the contract explicit; avoids silent misconfiguration where users expect MCP settings but don’t get them; easier to reason about. Cons: migration friction for existing profiles; requires every developer to create at least an empty `{}` template.

Option B: Treat missing template as `{}` (continue seeding only the overlay fields). Pros: backwards compatible with current behavior; avoids requiring new local files. Cons: easy to miss that profile-specific template state is not being applied; makes “template support” feel unreliable.

Option C: Hybrid: accept missing template for now but emit a loud warning and plan a future tightening. Pros: smooth migration while still surfacing the issue. Cons: policy drift; introduces a “two-phase contract” that’s harder to explain and test.

> RECOMMENDATION: Option A, with an explicit note in the design/spec that the initial template may be an empty JSON object (`{}`) and is still “valid input”.

> **DECISION: Option A — Fail fast, but `{}` is valid.**
> Agree with the recommendation. Current code in `cao_rest.py` generates `.claude.json` from scratch with no template — so today there is effectively an implicit empty template. By requiring the file to exist (even as `{}`), we make the contract explicit and avoid the silent-misconfiguration trap where someone expects MCP servers to be injected but the template is simply missing. The migration cost is minimal: create `agents/brains/api-creds/claude/<cred-profile>/files/claude_state.template.json` containing `{}` for each existing credential profile. The fail-fast error message should name the expected path and the credential profile, making it immediately actionable.

### 4) Merge Semantics: Shallow vs Deep vs Selective Overlay

Question: When we combine template + launcher overlay, what is the merge algorithm?

Option A: Shallow merge at the top level (overlay replaces template keys at the top level). Pros: simplest; predictable; matches the current generate-from-scratch behavior; avoids surprising deep merges. Cons: if the template contains nested objects that overlap (e.g., `customApiKeyResponses`), the overlay replaces the entire object.

Option B: Deep merge (recursive merge for nested objects). Pros: “preserve template” semantics feel stronger. Cons: ambiguous for arrays and nested objects; easy to get wrong; can accidentally preserve stale/unsafe nested state; harder to test and document.

Option C: Selective overlay (only a fixed allowlist of keys are overwritten; everything else preserved). Pros: tight control of what launch-time enforces; safer against upstream template drift. Cons: requires maintaining the allowlist; still needs defined behavior for template-provided values of those keys.

> RECOMMENDATION: Option A. Specify shallow top-level merge, with the overlay producing a small fixed set of top-level keys (at minimum `hasCompletedOnboarding` and API key approval state; include `numStartups` only if we decide it is actually required).

> **DECISION: Option C — Selective overlay with a fixed allowlist of enforced keys.**
> Diverging from the recommendation here. Looking at the actual `.claude.json` structure seeded by `cao_rest.py`, the overlay touches `hasCompletedOnboarding`, `numStartups`, and `customApiKeyResponses`. With shallow merge, if the template also contains `customApiKeyResponses` (e.g., for a different key or additional response metadata), the overlay would replace the entire nested object — potentially losing template-provided state. Deep merge is too risky and ambiguous. Selective overlay is the sweet spot: define a fixed allowlist of keys the launcher enforces (`hasCompletedOnboarding`, `customApiKeyResponses`, and conditionally `numStartups`), overwrite only those, and preserve everything else from the template verbatim. This is effectively what the current `_seed_claude_home_config` does (it writes a fixed set of keys), just formalized. The implementation is `template.copy()` then `template[k] = overlay[k]` for each enforced key — as simple as shallow merge but with explicit intent. On `numStartups`: include it for now (it matches the reverse-engineered working state), and document it as "may be removable pending upstream verification."

### 5) Overlay Shape: What Exactly Is “Approved API Key” In `.claude.json`?

Question: Should the spec name the exact `.claude.json` keys used to “mark the API key approved” (e.g., `customApiKeyResponses.approved`), or keep it high-level?

Option A: Specify the concrete key names and JSON shape (as an explicit contract). Pros: testable; removes ambiguity for implementers; aligns with existing tests in `test_cao_client_and_profile.py`. Cons: more likely to break if upstream Claude Code changes its state schema; requires a versioning story.

Option B: Keep it high-level (“mark approved using last 20 chars”) and let implementation encode the details. Pros: flexible; spec remains stable if implementation details change. Cons: unclear to implementers; tests become “implementation-defined” rather than “contract-defined.”

> RECOMMENDATION: Option A, but pair it with explicit version pinning (see question 12). This is already effectively version-specific; making it explicit is less risky than leaving it implicit.

Additional edge case to decide: What if `ANTHROPIC_API_KEY` is shorter than 20 characters? Storing “last 20 chars” would store the full key, violating the “do not write full key” rule. Recommendation: treat “too-short” keys as invalid and fail with a clear error.

> **DECISION: Option A — Specify concrete key names and JSON shape, but no minimum key length.**
> Agree with the recommendation to specify the concrete shape. The current `cao_rest.py` encodes:
>
> - `customApiKeyResponses.approved: [<api_key_suffix>]`
> - `customApiKeyResponses.rejected: []`
>
> where `<api_key_suffix> = ANTHROPIC_API_KEY[-20:]` (and for keys shorter than 20 characters, Python slicing yields the full key). This is tested in the existing test suite. Making it implicit while the implementation is version-specific anyway just adds confusion — better to be explicit and document the tested version (Q12).
>
> **Diverge on the “too-short key” edge case:** Do NOT enforce a 20-character minimum. API keys from third-party providers (e.g., yunwu.ai proxies, Azure OpenAI-compatible endpoints, other relay services) have no guaranteed format or minimum length. Python's `[-20:]` slice already handles short strings gracefully (returns the full string). The spec should state: “use the last 20 characters of the key (or the full key if shorter than 20 characters) as the approval lookup key in `customApiKeyResponses`.” For short keys this implies writing the full key into `.claude.json`; this is an acceptable tradeoff for real-world provider diversity, since the key is already present in the process environment.

### 6) Create vs Update: Should the Bootstrap Helper Rewrite Existing `.claude.json`?

Question: Earlier drafts of the delta spec said “create or update” runtime `.claude.json`, but current code skips if the file exists. Which behavior is the contract?

Option A: Create-only (do not rewrite if `.claude.json` exists). Pros: safer for long-lived/resumed sessions; avoids clobbering tool-written state; matches current implementation and tests. Cons: if a template is projected into the home as `.claude.json`, the helper would skip and fail to enforce invariants.

Option B: Update/merge if it exists (apply overlay fields even when file exists). Pros: enforces invariants more robustly; can support `.claude.json` being present before bootstrap. Cons: risk of overwriting runtime state in resumed sessions; requires careful merge semantics and a “when is it safe to update?” story.

> RECOMMENDATION: Option A, and avoid projecting the template into the runtime home as `.claude.json`. Keep the template as a separate input file and have the helper write `.claude.json` only when missing (fresh-home path).

> **DECISION: Option A — Create-only.**
> Agree with the recommendation. This is consistent with the Q2 decision to project the template as `claude_state.template.json` (not `.claude.json`), which eliminates the "template already occupies the target path" concern. The current `_seed_claude_home_config` already checks `if not (home_path / ".claude.json").exists()` before writing. Create-only is safer for resumed/long-lived sessions where Claude Code may have mutated its own state file. The bootstrap helper contract becomes: "if `.claude.json` is missing, create it from template + overlay; if it exists, do nothing." This is simple, testable, and avoids an entire class of merge-on-update edge cases.

### 7) Headless Backend Invariants: Is `-p` Sufficiently Non-Interactive?

Question: Does `claude -p` (headless) reliably suppress the onboarding and permission/trust dialogs that motivated this change, or do we need additional flags (like `--dangerously-skip-permissions`) and/or config seeding?

Option A: Treat `-p` as sufficient, and only document it. Pros: simplest; matches how `build_launch_plan()` currently builds headless commands. Cons: unverified assumption; could break on upstream changes.

Option B: Treat headless as in-scope for the same bootstrap (seed `.claude.json`, validate `settings.json`), while still relying on `-p` for interactivity suppression. Pros: lowest-risk; “cheap insurance”; keeps behavior consistent. Cons: adds more coupling between headless and the config contract.

Option C: Add `--dangerously-skip-permissions` to headless as well (if supported), and treat it as a required invariant. Pros: stronger guarantee. Cons: may be unsupported in headless mode; adds another version-sensitive detail.

> RECOMMENDATION: Option B. Seed/validate config for headless too, but keep the “non-interactive bypass mechanism” wording flexible for headless (the invariant may be “use `-p`” rather than “use `--dangerously-skip-permissions`”).

> **DECISION: Option B as foundation, but broadened — user-configurable arglist for headless launches, with documented reserved args and conflict detection.**
> Agree that headless should share the bootstrap helper (seed `.claude.json`, validate `settings.json`) per Q1. However, the question of which CLI flags ensure non-interactivity should not be answered by hardcoding flags in backend code.
>
> Currently, `build_launch_plan()` hardcodes `-p` for all headless backends (line 71 of `launch_plan.py`), and `_bootstrap_args()` hardcodes `--append-system-prompt`. This is brittle: upstream Claude Code may add, rename, or deprecate flags; third-party providers behind `ANTHROPIC_BASE_URL` may need provider-specific flags; and users cannot add flags like `--dangerously-skip-permissions` without code changes.
>
> **Proposed contract:** Let the tool adapter (`claude.yaml`) or brain manifest declare the base argument list for headless launches. Backend code injects only a documented set of **reserved args** that are inherent to the backend protocol. Concretely:
>
> **User-configured args** (via `claude.yaml` `launch.args`):
> - Mode flags: `-p` (headless/pipe mode)
> - Permission flags: `--dangerously-skip-permissions`
> - Any provider-specific or upstream-version-specific flags
> - Example: `args: ["-p", "--dangerously-skip-permissions"]`
>
> **Backend-reserved args** (injected by code, documented in spec):
> - `--resume <session_id>` — session continuation (headless backend protocol)
> - `--output-format <format>` — output parsing contract (headless backend protocol)
> - `--append-system-prompt <text>` — role injection (when `role_injection.method == "native_append_system_prompt"`)
>
> **Conflict detection:** If the user's `launch.args` contains any backend-reserved arg (i.e., `--resume`, `--output-format`, or `--append-system-prompt`), `build_launch_plan()` must raise a `LaunchPlanError` naming the conflicting arg and explaining that it is backend-managed. This prevents silent double-injection or argument ordering bugs.
>
> This keeps the bootstrap helper (Q1) and config seeding intact as cheap insurance, while making the CLI invocation shape flexible and user-controlled. If a future Claude Code version requires `--no-onboarding` instead of `-p`, the fix is a YAML edit, not a code change. The reserved-arg boundary is small, stable (tied to the backend protocol, not upstream CLI), and explicitly documented.

### 8) Proxy Env Inheritance: Default Off vs Current Always-On (Migration Plan)

Question: Earlier drafts of the design/spec wanted proxy inheritance disabled by default for tmux launches, but the current CAO backend forwards proxy/TLS env vars unconditionally. How do we avoid regressions while moving to the desired contract?

Option A: Flip default to off immediately. Pros: matches the desired determinism; aligns contract and implementation quickly. Cons: likely breaks proxied environments unless users notice and opt in.

Option B: Transitional order (safe migration): keep current behavior until explicit configuration exists, then flip. Pros: avoids regressions; gives time to document and validate the alternative path (explicit env injection via profile). Cons: contract vs implementation mismatch during transition; requires discipline to actually flip later.

> RECOMMENDATION: Use Option B as the implementation/migration strategy, but keep the contract aimed at the steady state (default off) and explicitly document a transition plan and order of work (flag/override first, deterministic injection path next, default flip last).

> **DECISION: Follow upstream CAO practice — default to inheriting all env vars from the calling process.**
> The upstream CAO project (`cli-agent-orchestrator`) creates tmux sessions with `environment = os.environ.copy()` (`clients/tmux.py:create_session`, line 89), inheriting **all** caller env vars. Our CAO backend diverged from this by creating bare tmux sessions and manually injecting only curated vars — then we had to add `_FORWARDED_ENV_NAMES` as a bugfix to compensate for our own stricter isolation.
>
> **Architecture clarification:** Our project does not import or depend on the upstream `cli-agent-orchestrator` as a library. The `extern/orphan/cli-agent-orchestrator/` clone is reference-only (gitignored). The `uv tool` installation (`cao-server`) runs the CAO REST server, which our own `agent_system_dissect.cao.rest_client` talks to over HTTP. Critically, our `cao_rest.py` backend **manages tmux sessions directly** via `subprocess.run(["tmux", ...])`, bypassing upstream's `TmuxClient` entirely. So when our backend creates a terminal, the upstream `os.environ.copy()` code path never runs — our own `_create_tmux_session` creates a bare session, and `_set_tmux_session_environment` injects only curated vars. The proxy forwarding gap was a consequence of this architecture.
>
> Rather than maintaining a parallel, more restrictive tmux env model and then patching it with selective forwarding lists, **follow upstream's established practice as a design principle**: pass the calling process environment to the tmux session by default. This:
> - Aligns with the proven upstream CAO approach to tmux env management
> - Eliminates the need for `_FORWARDED_ENV_NAMES` and `_forwarded_process_env()` entirely
> - Makes proxy, TLS/CA, and any other env-dependent tooling work out of the box
> - Removes an entire class of "why doesn't my env var reach the tmux session" bugs
>
> **Implementation:** Change our `_create_tmux_session` to pass the full calling process environment to the tmux session (e.g., via `tmux new-session -d -e` or by setting all vars via `tmux set-environment`), then overlay launch-specific vars (`CLAUDE_CONFIG_DIR`, `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL`, etc.) on top. Launch-specific vars take precedence over inherited env.
>
> The `AGENTSYS_BRAIN_INHERIT_PROXY` override and `launch.inherit_proxy_env` flag become unnecessary for the default case. If we ever need a "strict isolation" mode in the future, it can be added as an opt-in flag — but that is not this change.

### 9) “Proxy” vs “TLS/CA”: What Env Vars Are In Scope?

Question: The spec enumerates proxy vars only, but the current CAO backend also forwards TLS/CA-related env vars (`SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, `NODE_EXTRA_CA_CERTS`, etc.). What is the contract?

Option A: Expand the spec’s enumerated list and rename the concept to “network env vars” (proxy + TLS/CA). Pros: matches reality; avoids hidden coupling to CAO backend behavior; reduces certificate-related failures in proxied/corporate environments. Cons: broadens scope beyond “proxy” and may reduce determinism unless gated.

Option B: Split into two categories with separate flags (proxy vs TLS/CA). Pros: precise control; clearer semantics. Cons: more knobs; more documentation/testing burden.

Option C: Always forward TLS/CA vars but gate proxy vars. Pros: pragmatic; TLS/CA tends to be required for basic HTTPS to work in many environments. Cons: still forwards some caller env implicitly.

> RECOMMENDATION: Decide explicitly between A and C. If the primary motivation is “avoid hidden dependencies”, A is cleaner (one explicit allowlist under an explicit inheritance policy). If the primary motivation is “keep things working”, C is a lower-friction compromise.

> **DECISION: Question is superseded by Q8 decision.**
> With Q8 deciding to follow upstream CAO and inherit the full calling process environment, there is no need to enumerate, categorize, or selectively gate proxy vs TLS/CA vars. All env vars — proxy, TLS/CA, and everything else — are inherited by default. The `_FORWARDED_ENV_NAMES` constant and the concept of a curated forwarding list are removed entirely. If we ever add a “strict isolation” mode in the future, we would need to revisit this question then, but that is out of scope for this change.

### 10) Spec Duplication: Proxy Inheritance Requirements Live In Two Delta Specs

Question: Proxy inheritance requirements are currently duplicated in both delta specs. Should one be canonical?

Option A: Make `component-agent-construction` canonical (platform-level), and have the Claude-specific spec reference it. Pros: single source of truth; easier maintenance. Cons: requires cross-spec reference discipline.

Option B: Keep duplication for readability. Pros: each capability spec is self-contained. Cons: drift risk; future edits may update one but not the other.

> RECOMMENDATION: Option A.

> **DECISION: Option A — `component-agent-construction` is canonical for env inheritance policy.**
> Agree. Env inheritance is a platform-level concern (it applies to any tool launched in tmux isolation, not just Claude). With Q8 deciding to inherit all env vars by default, the platform spec should document this as the default tmux session env policy. The Claude-specific spec should reference the platform spec rather than restating env inheritance rules. This prevents the drift risk identified in the review where edits to one spec miss the other.

### 11) Task 2.4 Underspecification: Where Do “Explicit Proxy Vars” Belong?

Question: If we want determinism without inheriting caller env, where do proxy values live and how are they injected?

Option A: Put proxy vars in Claude credential profiles (`env/vars.env`) and expand the `claude.yaml` allowlist. Pros: no new mechanism; leverages existing env injection. Cons: semantically odd (proxy vars are not Claude credentials); encourages duplicating the same infra config across tools.

Option B: Introduce a brain-wide “infrastructure env” layer (applies to all tools) separate from credential profiles. Pros: conceptually correct; avoids tool-specific duplication. Cons: likely out of scope for this change; would require new schema and projection rules.

Option C: Rely only on caller-env inheritance (turn it on when needed) and do not support explicit injection. Pros: simplest. Cons: undermines determinism goal; makes tmux runs dependent on developer shell state.

> RECOMMENDATION: If we want the smallest coherent step, pick Option A and document the semantic compromise. If we want the clean architecture, add a scoped follow-up change for Option B (but do not block this contract on it).

> **DECISION: Question is largely superseded by Q8 decision, but with an important implementation requirement.**
> With Q8 deciding to inherit the full calling process environment (matching upstream CAO), the primary use case for explicit proxy var injection disappears — proxy/TLS vars reach the tmux session automatically via `os.environ.copy()`. No `claude.yaml` allowlist expansion or infrastructure-env layer is needed for the default case.
>
> **However, credential profile env vars must also reach the tmux session regardless of the allowlist.** Currently, `parse_allowlisted_env()` in `loaders.py` filters `vars.env` through the `claude.yaml` allowlist — only `ANTHROPIC_API_KEY` and `ANTHROPIC_BASE_URL` pass through. If a user adds `http_proxy` or any other var to `vars.env` as a workaround for an env issue, it gets silently dropped. This must be fixed: **all env vars declared in the credential profile's `vars.env` must be injected into the tmux session environment**, not just allowlisted ones. The allowlist's role should be limited to documenting expected/required vars, not gating injection.
>
> This gives users a reliable escape hatch: if any env var needs to override the inherited env or fill a gap, they can add it to `agents/brains/api-creds/claude/<cred-profile>/env/vars.env` and it will take effect. The precedence order becomes: `os.environ` (base) → `vars.env` (credential profile overlay) → launch-specific vars (`CLAUDE_CONFIG_DIR`, etc.).
>
> Option B (brain-wide infrastructure env) remains the clean architecture for a future follow-up if cross-tool env sharing is needed, but is out of scope for this change.

### 12) Version Pinning And Compatibility Signals

Question: The contract is based on reverse-engineered upstream behavior (e.g., Claude Code v2.1.62 per `context/logs/code-reivew/20260227-140000-cao-claude-fresh-config-dir-bugfix.md`). Where do we record this, and what is the expected upgrade workflow?

Option A: Record a single “verified against” version in design/spec/docs, and treat the demo script as the compatibility smoke test. Pros: lightweight; realistic. Cons: still manual; may be missed.

Option B: Maintain a compatibility matrix. Pros: more explicit. Cons: overkill for this use case.

> RECOMMENDATION: Option A. Record a tested version (and date) in the design/spec, and require Task 4.2 to explicitly assert “no interactive prompts were shown.”

> **DECISION: Option A — Document tested version, no version pinning or enforcement.**
> Record the tested Claude Code version (v2.1.62) and date in the design doc for reference. No version pinning, no compatibility check at runtime, no `claude --version` gate. If something breaks on a newer version, the documented version tells us what last worked — that's sufficient. Task 4.2 (end-to-end demo) serves as the compatibility smoke test.

## Proposed “Decide Next” Checklist

All decisions are now resolved:

1. ~~Bootstrap helper scope~~ → All Claude launchers (Q1).
2. ~~Template strategy~~ → Project as `claude_state.template.json` via `credential_projection.file_mappings` (Q2).
3. ~~Missing-template policy~~ → Fail fast; `{}` is valid (Q3).
4. ~~Merge semantics~~ → Selective overlay with fixed enforced-key allowlist (Q4).
5. ~~Proxy inheritance default and migration~~ → Follow upstream CAO, inherit all env vars (Q8).
6. ~~TLS/CA env vars contract~~ → Superseded by Q8 (Q9).
7. ~~`.claude.json` shape and version pinning~~ → Specify concrete shape; document tested version, no enforcement (Q5, Q12).

## Decision Summary

| # | Question | Decision | Diverges from Rec? |
|---|----------|----------|--------------------|
| 1 | Bootstrap scope | **All Claude launchers** (Option A) | No |
| 2 | Template location | **Project into runtime home as `claude_state.template.json`** (Option A) | No |
| 3 | Missing template | **Fail fast; `{}` is valid** (Option A) | No |
| 4 | Merge semantics | **Selective overlay with fixed allowlist** (Option C) | Yes — rec was shallow merge |
| 5 | Overlay shape | **Specify concrete JSON shape; no min key length** (Option A, edge case revised) | Partially — rec wanted fail-fast on short keys |
| 6 | Create vs update | **Create-only** (Option A) | No |
| 7 | Headless invariants | **Bootstrap + user-configurable arglist** (Option B broadened) | Yes — rec was fixed `-p`; now args are config |
| 8 | Proxy migration | **Inherit all env vars (follow upstream CAO)** | Yes — rec was default-off; now default-inherit-all |
| 9 | Proxy vs TLS/CA | **Superseded by Q8** (inherit all) | Yes — no selective forwarding needed |
| 10 | Spec duplication | **`component-agent-construction` canonical for env policy** (Option A) | No |
| 11 | Proxy var injection | **All `vars.env` entries injected (no allowlist gating); user escape hatch** | Yes — allowlist must not block injection |
| 12 | Version pinning | **Document tested version only; no enforcement** (Option A) | No |

**Notable divergences:**

**Q4 (Merge Semantics):** Chose selective overlay over shallow merge. The overlay keys (`hasCompletedOnboarding`, `customApiKeyResponses`, `numStartups`) are a known, small, stable set. Selective overlay gives the same simplicity as shallow merge but avoids accidentally clobbering nested template state under `customApiKeyResponses`. The implementation difference is one `for k in ENFORCED_KEYS` loop vs a `{**template, **overlay}` spread — negligible complexity for meaningful safety.

**Q5 (Short Key Edge Case):** Dropped the recommended 20-character minimum and fail-fast on short keys. Third-party API providers (yunwu.ai, Azure relays, etc.) use arbitrary key formats with no guaranteed minimum length. Python's `[-20:]` slice already returns the full string for short inputs — no special handling needed. Failing on short keys would break real-world proxy setups for no security gain (the key is already in the process environment).

**Q7 (Headless Invariants):** Broadened from "bootstrap + rely on `-p`" to "bootstrap + user-configurable arglist with reserved-arg conflict detection." Currently `build_launch_plan()` hardcodes `-p` for headless backends — this should become configuration in `claude.yaml`'s `launch.args`. Backend code only injects a documented set of reserved args (`--resume`, `--output-format`, `--append-system-prompt`). If user-configured args collide with reserved args, `build_launch_plan()` raises a `LaunchPlanError` — fail-fast, no silent double-injection.

**Q8/Q9/Q11 (Env Inheritance):** Decided to follow upstream CAO practice and inherit the full calling process environment (`os.environ.copy()`), rather than the spec's original "default off with selective forwarding" approach. This eliminates `_FORWARDED_ENV_NAMES`, the curated forwarding list, the `launch.inherit_proxy_env` flag, and the `AGENTSYS_BRAIN_INHERIT_PROXY` override. Additionally, Q11 requires that **all** env vars from the credential profile's `vars.env` are injected into the tmux session — the `claude.yaml` allowlist must not gate injection, so users can add arbitrary env vars to `vars.env` as a workaround for env issues. Precedence: `os.environ` (base) → `vars.env` (credential profile overlay) → launch-specific vars.

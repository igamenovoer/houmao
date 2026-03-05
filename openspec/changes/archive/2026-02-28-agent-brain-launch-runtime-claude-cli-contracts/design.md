## Context

The brain launch runtime constructs isolated per-run tool homes and sets tool-specific home selector environment variables (for Claude Code, `CLAUDE_CONFIG_DIR`). Claude Code v2.x treats a fresh/empty config directory as first-run and can enter interactive onboarding / approval flows. In orchestrated tmux-backed sessions (for example CAO), these prompts can block unattended startup and cause terminal initialization timeouts.

In addition, Claude Code’s first-run onboarding may contact `api.anthropic.com` for feature flags regardless of `ANTHROPIC_BASE_URL`. In constrained network environments, this makes a “fresh home” launch unreliable unless the first-run flow is bypassed.

This change codifies contracts for:
- what a Claude brain home must contain to avoid interactive first-run flows, and
- how orchestrated Claude launches must be configured (env + flags) to be non-interactive.

## Goals / Non-Goals

**Goals:**
- Ensure orchestrated Claude Code sessions can start non-interactively with a fresh `CLAUDE_CONFIG_DIR`.
- Make the required Claude brain-home bootstrap artifacts explicit and testable (files + minimal state).
- Preserve the “fresh-by-default” principle while clarifying that minimal deterministic bootstrap config/state is allowed.
- Keep credential secrets out of manifests and avoid writing full secrets into bootstrap state.

**Non-Goals:**
- Guarantee compatibility with all future Claude Code versions without updates (the bootstrap contract may evolve as upstream behavior changes).
- Replace or redesign CAO provider behavior (for example, the trust-prompt handler remains an implementation detail of CAO’s Claude provider).
- Solve all Claude output parsing/extraction edge cases (separate concern from startup bootstrapping).

## Decisions

### 1) Treat `settings.json` as a tool config-profile artifact

**Decision:** Store the non-interactive settings needed for orchestrated Claude launches as a tracked config-profile file under `agents/brains/cli-configs/claude/<profile>/settings.json`.

**Rationale:** This keeps non-secret launch behavior in an auditable, declarative place aligned with existing “config profiles” mechanics.

**Alternatives considered:**
- Generate settings at runtime: makes behavior harder to audit and reason about across profiles.

### 2) Use credential-profile `claude_state.template.json` + launcher overlay

**Decision:** Store a Claude state template JSON file in Claude credential profiles under `agents/brains/api-creds/claude/<cred-profile>/files/` (local-only), and have launch-time preparation materialize the final `$CLAUDE_CONFIG_DIR/.claude.json` by starting from that template and then overriding/adding required runtime fields.

To avoid ambiguity and accidental collisions, the template file MUST NOT be named `.claude.json` itself. It SHOULD be mapped into the runtime home under a non-conflicting name (for example `claude_state.template.json`) and then used as input to materialize the runtime `.claude.json`.

Template input naming:
- Credential profile source file: `files/claude_state.template.json` (recommended default name).
- Runtime-home input filename: `claude_state.template.json` (recommended default name).

Missing-template policy:
- Launch MUST fail with a clear configuration error if the template file is missing.
- An empty JSON object (`{}`) is a valid template (it is still “provided input”).

Merge semantics:
- Selective overlay with a fixed allowlist of enforced top-level keys (no deep merge). The launcher starts from the template JSON and overwrites only the enforced keys; all other template keys are preserved verbatim.

At minimum, launcher overlay logic must enforce:
- `hasCompletedOnboarding: true`
- `numStartups: 1` (version-specific; keep it minimal and re-verify when Claude Code changes)
- When `ANTHROPIC_API_KEY` is set, it MUST set:
  - `customApiKeyResponses.approved: [<api_key_suffix>]`
  - `customApiKeyResponses.rejected: []`
  - where `<api_key_suffix>` is the last 20 characters of `ANTHROPIC_API_KEY` (or the full key if shorter than 20 characters).
- The materialized `.claude.json` MUST NOT contain the full `ANTHROPIC_API_KEY` value when the key is longer than the suffix length.

The overlay contract MUST name the concrete fields used for approval state (for example `customApiKeyResponses.approved` and `customApiKeyResponses.rejected`) and SHOULD record the Claude Code version it was verified against (documented only; no enforcement). Verified against Claude Code v2.1.62 (2026-02-27).

**Rationale:** MCP and related Claude state lives naturally with credential-local configuration, while launch-time overlay guarantees startup-critical invariants and avoids baking environment-specific values directly into templates.

**Alternatives considered:**
- Generate `.claude.json` from scratch at launch time: simpler implementation, but risks losing profile-specific MCP/template state.
- Materialize final `.claude.json` only at build time: reduces launch logic but weakens coupling to effective runtime credentials.

### 3) Centralize “Claude home bootstrap” as a shared helper

**Decision:** Implement a shared helper in the brain launch runtime that prepares a Claude home (materialize `.claude.json` + validate required settings) and call it from each backend that launches Claude (including `cao_rest` and `claude_headless`).

The helper MUST be safe for resumed/long-lived homes:
- It SHOULD create/materialize `.claude.json` only when it is missing (fresh-home path), and MUST NOT clobber an existing `.claude.json` written by the tool.
- It SHOULD validate (not create) `settings.json` (projected via config profiles) and fail fast if required keys are missing.

**Rationale:** Avoids backend drift (CAO vs headless vs other launchers) and keeps contract enforcement in one place.

**Alternatives considered:**
- Backend-local seeding only: quicker but risks missing paths (and reintroducing startup flakiness).

### 4) Headless launch args are tool-adapter-configurable

**Decision:** Claude headless base args (for example `-p` and/or `--dangerously-skip-permissions`) SHALL be declared in the Claude tool adapter (`agents/brains/tool-adapters/claude.yaml:launch.args`) rather than hardcoded in backend code.

Backend code injects only a documented set of backend-reserved args tied to the headless protocol:
- `--resume <session_id>`
- `--output-format <format>`
- `--append-system-prompt <text>` (only when role injection uses native `--append-system-prompt`)

The launch-plan builder MUST fail fast with a clear error if user-configured `launch.args` contains any backend-reserved arg (to prevent double-injection or argument ordering bugs).

**Rationale:** Upstream Claude CLI flags are version/provider-specific. Making the base arglist configuration-driven avoids backend drift and lets users adapt without code changes.

**Alternatives considered:**
- Hardcode `-p` and other flags in `build_launch_plan()`: simple but brittle and hard to evolve.

### 5) Tmux session environment inherits the caller process env

**Decision:** For tmux-isolated launch paths (for example CAO), the tmux session SHALL inherit the full calling process environment (`os.environ`), matching upstream CAO practice, and then apply overlays in this precedence order:
1) calling process environment (base),
2) credential-profile `vars.env` (overlay), and
3) launch-specific environment variables (overlay; e.g. home selector env var, tool-specific env overrides).

Credential-profile `vars.env` injection MUST NOT be gated by a tool-adapter allowlist; all entries in the env file MUST be injected. (Allowlists remain useful for documentation and validation of expected vars, but MUST NOT silently drop declared vars.)

This is a platform-level concern. The canonical env inheritance requirements SHOULD live in the `component-agent-construction` capability spec; the Claude-specific startup spec SHOULD reference it rather than duplicating it.

**Rationale:** This aligns tmux backends with `subprocess.Popen`-based launchers (which already inherit `os.environ`) and eliminates an entire class of "env var didn't reach tmux" failures (proxy, TLS/CA, corporate certs, etc.) without maintaining curated forwarding lists.

**Alternatives considered:**
- Maintain a curated list of forwarded env vars: hard to keep correct; brittle across environments.
- Default-off inheritance with opt-in flags/overrides: more knobs and still easy to misconfigure; contradicts upstream CAO practice.

## Risks / Trade-offs

- **[Claude Code changes bootstrap keys/paths]** → Mitigation: keep bootstrap minimal, document tested-version assumptions in docs/tests, and validate via the demo script as an end-to-end check.
- **[Template shape drift across credential profiles]** → Mitigation: validate required JSON shape during launch-time overlay and fail with clear diagnostics if invalid.
- **[Bootstrap state leaks credential material]** → Mitigation: store only the minimum derived identifier needed (for example, API key suffix) and avoid writing the full API key into `.claude.json` when the key is longer than the suffix length.
- **[“Fresh home” semantics become confusing]** → Mitigation: clarify the definition in `component-agent-construction` and distinguish “prior-run history/log/session artifacts” from deterministic bootstrap config/state.
- **[Backends drift in behavior]** → Mitigation: require all Claude-launching backends to call the shared bootstrap helper and cover with unit tests.

## Migration Plan

Bootstrap/template:
- Add the Claude state template file to active Claude credential profiles under `agents/brains/api-creds/claude/<cred-profile>/files/claude_state.template.json` (local-only). The template may be `{}`.
- Map the template into the runtime home as `claude_state.template.json` (do not pre-seed `.claude.json` directly from the profile).
- During launch, materialize runtime-home `.claude.json` only when it is missing by applying the selective overlay of enforced keys onto the template.
- Invoke the shared bootstrap helper from all Claude launch paths (`cao_rest`, `claude_headless`, and any direct launcher entrypoints).

Headless args:
- Move headless base args from hardcoded launch-plan construction into the Claude tool adapter (`agents/brains/tool-adapters/claude.yaml:launch.args`).
- Document backend-reserved args and add conflict detection for user-configured args.

Tmux environment:
- For tmux-isolated launch paths (for example CAO), inherit the full calling process environment into the tmux session, then overlay credential-profile `vars.env`, then apply launch-specific env vars.
- Ensure credential-profile `vars.env` injection into tmux is not gated by a tool-adapter allowlist (inject all declared vars).
- Remove curated forwarding lists and proxy-specific toggles/overrides from the platform contracts and implementation.

Rollback strategy:
- Gate/disable the bootstrap helper and revert to generate-from-scratch seeding for troubleshooting.
- Temporarily revert CAO tmux env propagation back to a curated forwarding list if troubleshooting requires it.

Validation:
- Re-run the CAO Claude demo script end-to-end in an environment that uses `CLAUDE_CONFIG_DIR` isolation and explicitly assert that no interactive prompts are shown.
- Record the tested Claude Code version in docs/tests (lightweight, not a full compatibility matrix). Verified against Claude Code v2.1.62 (2026-02-27).

## Resolved Open Questions

- Bootstrap helper scope: invoke for all Claude launchers (including headless/pipe-mode flows).
- Headless launch args: tool-adapter-configurable base arglist with backend-reserved args and conflict detection.
- Tmux environment: inherit the full calling process environment and overlay credential-profile `vars.env` plus launch-specific vars (no curated forwarding lists).
- Canonical launch command: keep backend-specific commands, but codify shared invariants (seeded `.claude.json`, validated `settings.json`, and non-interactive flags/modes appropriate to the backend).
- Version compatibility: lightweight version assertion (document tested version + use the demo script as the compatibility smoke test), not a formal matrix.

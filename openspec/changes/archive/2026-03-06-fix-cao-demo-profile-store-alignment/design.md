## Context

`gig-agents` demo packs currently include multiple CAO-backed session scripts (`cao-codex-session`, `cao-claude-tmp-write`, `cao-claude-esc-interrupt`, and `cao-claude-session`). Recent investigation showed these scripts can fail with `Agent profile not found` even when fixture credential files exist, and in several cases that condition is reported as `SKIP: missing credentials`.

Two technical mismatches drive this:

1. CAO launcher context (`home_dir`) and runtime profile install path are not consistently aligned in demo start-session calls.
2. Local loopback demo startup can accept an already-healthy, externally managed `cao-server`, creating implicit context drift (profile store and working-directory policy drift), while demo scripts may drift toward ad-hoc process management despite an existing launcher module.

## Goals / Non-Goals

**Goals:**
- Make CAO-backed demo runs deterministic for local loopback usage.
- Ensure demo session startup uses a profile store path aligned with the launcher-managed CAO home context.
- Ensure demo scripts use the existing CAO launcher module as the single lifecycle interface.
- Make skip/fail diagnostics explicit so profile-store mismatch errors are not mislabeled as missing credentials.
- Keep behavior consistent across Claude and Codex CAO demo packs.

**Non-Goals:**
- Redesign core runtime/CAO APIs.
- Remove existing safe `SKIP:` behavior for missing prerequisites.
- Expand local-only Claude demos to support arbitrary remote CAO endpoints.
- Introduce a broad demo framework refactor beyond what is needed to restore reliability.
- Replace `gig_agents.cao.tools.cao_server_launcher` with new process-management primitives.

## Decisions

### 1) Enforce demo-local CAO context tuple alignment
Each CAO-backed session demo will treat the following as one coherent context tuple:

- launcher `home_dir`
- resolved CAO profile-store path
- demo runtime root/workspace

Session startup will pass the resolved profile-store path explicitly (`--cao-profile-store`) so runtime-generated agent profiles are installed where the launched CAO server reads them.

Alternative considered:
- Rely on process `HOME` defaults and implicit profile-store resolution.
  - Rejected because demo orchestration invokes launcher/runtime in separate process contexts and defaults drift too easily.

### 2) Use launcher module as the sole CAO lifecycle authority
CAO-backed demo scripts SHALL manage CAO lifecycle only through `python -m gig_agents.cao.tools.cao_server_launcher` (`status`, `start`, `stop`) and launcher JSON outputs.

Scripts SHALL NOT implement direct process-discovery or direct signal-delivery logic (for example `/proc` scanning + manual `SIGTERM`/`SIGKILL`) as part of demo server management.

For loopback-only demos, if launcher output indicates reuse of an untracked healthy process (for example `reused_existing_process=true` with no tracked PID for demo ownership), demos SHALL handle this via launcher-driven control flow and explicit diagnostics (for example launcher-mediated retry path or explicit fail-fast), not out-of-band process termination.

Alternative considered:
- Always accept any healthy server at `localhost:9889`.
  - Rejected because this directly causes profile-store and working-directory policy mismatches that invalidate the demo contract.

Alternative considered:
- Implement custom process scan/kill fallback in demo scripts.
  - Rejected because it duplicates launcher responsibilities, increases operational risk, and diverges demo behavior from canonical CAO lifecycle tooling.

### 3) Split skip taxonomy for profile-store mismatch vs missing credentials
Demo skip classifiers will treat CAO profile-load failures (for example `Agent profile not found` / `Failed to load agent profile`) as a dedicated mismatch category rather than `missing credentials`.

Alternative considered:
- Keep existing broad `missing credentials` bucket.
  - Rejected because it obscures root cause and blocks operator remediation.

### 4) Keep remediation script-scoped in this change
Apply fixes directly to affected demo scripts and their READMEs in this change while preserving launcher-module-centered lifecycle behavior. Shared-library consolidation for demo helpers can be evaluated later.

Alternative considered:
- Introduce a shared shell helper layer immediately.
  - Rejected for now to reduce blast radius and keep this reliability fix focused.

## Risks / Trade-offs

- [Risk] Strict launcher-only lifecycle handling may fail fast more often in dirty local environments where port `9889` is already occupied by unknown processes.
  - Mitigation: emit explicit remediation instructions and keep demo behavior predictable rather than implicit.

- [Risk] Regex-based skip classification can drift as CAO error strings evolve.
  - Mitigation: keep explicit pattern coverage for known failure families and validate against current demo logs.

- [Risk] Script-local fixes may duplicate logic across demo packs.
  - Mitigation: apply consistent requirements in specs/tasks and consider a follow-up helper unification change.

## Migration Plan

1. Update affected CAO session demo scripts to align launcher home/profile store/session start arguments.
2. Update demo startup handling for untracked local server reuse using launcher-module outputs and control flow only (no ad-hoc process signaling).
3. Update skip classifiers and README troubleshooting text.
4. Re-run CAO-backed demos sequentially (single-port local CAO) and record outcomes.
5. Keep rollback simple by reverting demo-script/doc changes if regressions appear.

## Open Questions

- Should all CAO-backed demo scripts share one shell helper in a follow-up to prevent drift?
- Should codex/claude demo packs enforce an identical local-only startup policy, or keep per-demo flexibility for external CAO endpoints while still requiring launcher-only lifecycle handling?

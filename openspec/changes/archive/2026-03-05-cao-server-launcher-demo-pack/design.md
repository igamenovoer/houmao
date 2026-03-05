## Context

`cao-server-launcher` now exists in the main package, including CLI commands for
`status`, `start`, and `stop`. The repo already has robust CAO demo packs under
`scripts/demo/` with predictable structure, skip behavior, report verification,
and snapshot refresh support.

For launcher onboarding, we need a dedicated tutorial pack that demonstrates the
launcher workflow itself (instead of only using launcher indirectly from other
demos), while staying safe and reproducible.

Constraints:

- Keep demos non-destructive and workspace-scoped.
- Preserve the existing `scripts/demo/*` conventions (logging, `SKIP:` behavior,
  verification script, expected report snapshot).
- Use launcher CLI from package module path; do not call vendored CAO sources.
- Align README/tutorial content with the updated tutorial-pack instruction that
  requires explicit inline steps, inline critical outputs, and appendix tables.

## Goals / Non-Goals

**Goals:**

- Add one self-contained demo pack under `scripts/demo/` focused on CAO launcher usage.
- Demonstrate end-to-end `status -> start -> status -> stop -> status` behavior.
- Capture structured launcher JSON outputs and validate them through a tracked
  expected report contract.
- Provide a step-by-step README that mirrors tutorial-pack guidance in
  `magic-context/instructions/explain/make-api-tutorial-pack.md`.

**Non-Goals:**

- Changing launcher core semantics (`server_launcher.py`).
- Adding new launcher API fields purely for demo needs.
- Replacing existing CAO session demos.

## Decisions

1. **Create a new demo pack directory under `scripts/demo/`**
   - This keeps consistency with existing demo discovery and avoids mixing
     launcher tutorials into unrelated docs folders.
   - Alternative considered: place under `docs/tutorials/`; rejected because
     user explicitly requested `scripts/demo` and existing operational demos live there.

2. **Use explicit sanitize + verify workflow for expected reports**
   - `run_demo.sh` produces `report.json` in workspace.
   - `scripts/sanitize_report.py` normalizes non-deterministic values before any
     expected-report updates.
   - A verification helper may compare sanitized output against
     `expected_report/report.json` (following repo demo patterns).
   - Alternative considered: assert inline in shell only; rejected because
     tracked expected-report snapshots are easier to review and update.

3. **Model deterministic checks around launcher artifacts**
   - Validate host-port artifact directory layout and key files (`pid`, `log`,
     optional launcher result json) to match launcher contract.
   - Include fields that are stable and sanitize workspace-specific paths.
   - Alternative considered: assert only health booleans; rejected because it
     misses key lifecycle artifact guarantees.

4. **Use explicit SKIP behavior for missing runtime prerequisites**
   - If CAO tooling or local environment prerequisites are missing, exit `0`
     with `SKIP:` for deterministic demo behavior in heterogeneous environments.
   - Alternative considered: hard-fail on missing CAO; rejected due flakiness in
     developer and CI-like local runs.

5. **README is treated as a transparent tutorial, not wrapper-only docs**
   - The README must inline meaningful commands performed by `run_demo.sh`
     (workspace setup, input copy, launcher invocations, verification).
   - The README must inline critical output snippets, not just file references.
   - The README must include critical example code blocks with inline comments
     and an appendix table/list for key parameters and file inventory.
   - Alternative considered: short README pointing to script; rejected by updated
     tutorial-pack requirements.

## Risks / Trade-offs

- [Risk] Local CAO service state may vary (already running vs not running), causing
  unstable assertions.
  -> Mitigation: encode expected behavior with tolerant checks (e.g. either reuse
  or started-new-process with explicit fields) and verify command outcomes instead
  of a single fixed path.

- [Risk] Paths/timestamps in report snapshots may cause noisy diffs.
  -> Mitigation: sanitize non-deterministic fields in `verify_report.py` before
  comparison/snapshot updates.

- [Risk] Demo scripts can accidentally affect tracked repo state.
  -> Mitigation: enforce workspace under `tmp/`, and only allow tracked-file
  mutation during explicit `--snapshot-report` mode.

## Migration Plan

1. Add demo pack scaffold under `scripts/demo/`.
2. Implement `run_demo.sh` with prerequisite checks + launcher flow.
3. Add sanitizer script (and optional verify script) plus initial expected report snapshot.
4. Add README tutorial and snapshot refresh instructions.
5. Run demo in snapshot mode once to establish golden output.

Rollback:

- Remove the new demo directory if issues arise; no runtime contract changes are
  required in launcher code.

## Open Questions

- Should this demo be added to a higher-level CI/manual test matrix in a future
  change, or remain opt-in like existing CAO demo packs?

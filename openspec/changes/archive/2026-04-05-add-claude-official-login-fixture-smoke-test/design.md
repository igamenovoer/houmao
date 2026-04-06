## Context

Houmao already projects Claude vendor login-state into isolated runtime homes and already skips `claude_state.template.json` when `.claude.json` is present. What is missing is one maintained local fixture and one reproducible validation flow that prove the contract with real-looking vendor login files instead of the older local fixture layout.

The current `tests/fixtures/agents/tools/claude/auth/` tree still reflects older local filenames such as `credentials.json`, while the live Claude adapter and recent project auth import work now expect `.credentials.json` and `.claude.json`. The fixture tree is also explicitly local-only host state, so the validation path must work without assuming plaintext secrets are committed or available in CI.

## Goals / Non-Goals

**Goals:**
- Define one supported local-only Claude fixture name, `official-login`, for vendor-login smoke validation.
- Keep `.credentials.json` opaque while allowing `.claude.json` to be minimized aggressively.
- Provide one reproducible temp-workdir launch flow that exercises the maintained `houmao-mgr agents launch` path with `HOUMAO_AGENT_DEF_DIR` pointed at `tests/fixtures/agents`.
- Make the no-template behavior explicit for this lane so the runtime contract is no longer inferred from implementation details alone.

**Non-Goals:**
- Making local secret-backed fixture validation part of CI.
- Introducing a new public user-facing auth bundle format beyond the existing vendor login-state files.
- Bulk-migrating every existing local Claude auth fixture in this change.
- Adding new tracked role presets solely for `official-login`.

## Decisions

### Keep `.credentials.json` verbatim and minimize `.claude.json`

`official-login` will use the vendor `.credentials.json` as-is under `files/.credentials.json`. Houmao should treat this file as opaque vendor state rather than attempting to normalize or prune individual keys. In contrast, `files/.claude.json` will be allowed to be a minimized valid JSON object, with `{}` as the baseline target shape for the smoke path.

This split matches the current runtime behavior: projected `.credentials.json` is preserved untouched, while launch-policy hooks already merge strategy-owned onboarding, trust, and approval state into `.claude.json` before launch. The alternatives were weaker:
- Omitting `.claude.json` entirely would fall back to the template-required path.
- Copying a full vendor `.claude.json` would add unnecessary host-specific noise and make the local fixture harder to reason about.

### Use `server-api-smoke` plus CLI auth override instead of a new tracked preset

The smoke path will launch the existing lightweight `server-api-smoke` Claude preset and override its auth with `--auth official-login`. That keeps the tracked preset catalog stable and avoids baking a local-only auth name into tracked YAML.

The main alternative was adding a dedicated tracked preset for `official-login`, but that would couple committed fixture metadata to a local-only secret bundle name and create extra preset maintenance for little value.

### Validate from a fresh temp workdir under `tmp/`

The maintained verification path will run from a fresh temp workdir under `tmp/<subdir>` while setting `HOUMAO_AGENT_DEF_DIR` to `tests/fixtures/agents`. This directly tests the project/workdir boundary that matters for vendor-login startup: the launched Claude session sees a clean workdir, while its agent-definition root still resolves to the shared fixture tree.

Using the repo root as the workdir would blur that distinction and make it easier to miss launch bugs tied to fresh-workdir trust or bootstrap behavior.

### Keep the verification flow local-only and reproducible

Because `official-login` depends on local secret material, the repository will treat the smoke launch as a supported local maintainer workflow rather than a CI test. The implementation can use a small helper script, a manual test, or tightly scoped README instructions, but it must remain reproducible from repo-owned instructions and must record the exact command shape needed for the validation.

## Risks / Trade-offs

- [Minimal `.claude.json` becomes insufficient for a future Claude version] → Keep the smoke flow explicit and adjust the maintained minimal fixture shape if vendor startup begins requiring additional seed keys.
- [Local-only validation drifts because CI cannot enforce it] → Put the command sequence in a repo-owned script or clearly versioned fixture guidance so maintainers run the same flow each time.
- [Legacy local Claude fixtures still use older filenames] → Scope this change to `official-login` and the documented smoke path, and leave broader fixture-tree normalization for a follow-up if needed.

## Migration Plan

1. Define the `official-login` local fixture shape under `tests/fixtures/agents/tools/claude/auth/`.
2. Update the Claude runtime and fixture guidance so a minimized projected `.claude.json` is an explicit supported lane.
3. Add the repo-owned smoke-validation flow that launches `server-api-smoke` from `tmp/<subdir>` with `--auth official-login`.
4. Run the local smoke flow and capture the result as implementation validation.

## Open Questions

- Whether the smoke workflow should live as a small helper script or as a documented manual command sequence can be decided during implementation; either is acceptable if the flow remains reproducible and repo-owned.

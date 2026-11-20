# Design

## Context

See `proposal.md` for motivation. The current fixture always creates its managed specialist with `--no-system-skills` in `scripts/agents/test-fixtures/fixturelib/prepare.py`, which writes `launch.system_skills.mode: none` into the generated preset. The product default for a managed launch is the `agent` pack from `src/houmao/agents/assets/system_skills/manifest.toml`.

The fixture already has a resolved configuration model and records a sanitized `configuration` summary in `run.json`. The change should use that existing path rather than add a parallel metadata mechanism.

## Goals / Non-Goals

**Goals:**

- Make manager-surface fixture runs exercise the same managed-launch `agent` system-skill default as normal launches.
- Keep an explicit, documented opt-out for isolation cases.
- Make the effective choice visible in `run.json` and test output.
- Cover both the default and opt-out paths with focused tests.

**Non-Goals:**

- No production runtime, gateway, mailbox, or system-skill lifecycle changes.
- No change to raw-surface fixture behavior; raw preparation does not create a managed specialist.
- No change to the historical `scripts/explore/houmao-3-0-interactive-review/iter1_dsh.py` helper.
- No attempt to pin a specific pack version or add a second system-skill selector beyond the default and opt-out.

## Decisions

### Use the managed default instead of pinning `replace agent`

The fixture should omit the system-skill policy entirely on the default path. This tests the same default a normal managed launch uses, so a future product default regression is visible in fixture qualification. The alternative, storing `mode: replace` with `packs: [agent]`, would make the fixture deterministic but would hide changes to the product default.

### Represent the choice as a two-value policy on `ResolvedConfig`

Add a `system_skill_policy: Literal["default", "none"] = "default"` field to `ResolvedConfig`. The existing `summary()` then records it in `run.json.configuration` without a second serializer. `--no-system-skills` maps to `"none"`; omission maps to `"default"`.

Alternative considered: a boolean `enable_system_skills`. The string matches the existing `launch.system_skills.mode` vocabulary and reads more clearly in reports.

### Apply the opt-out only to manager-surface preparation

`_prepare_project()` is the only fixture path that creates a managed specialist. The opt-out should be accepted only when `--surface manager` is selected. Raw preparation has no managed home to apply it to, and passive-server birth builds its own home from assets rather than the project specialist. Rejecting the flag on those surfaces avoids a silently inert option.

### Leave `check` and `prepare` aligned

Add the flag to the shared case arguments so `fixture.py check` and `fixture.py prepare` resolve the same configuration. `check` can report the selected policy without launching.

### Record the effective policy in `run.json`

The `configuration` block from `ResolvedConfig.summary()` is the authoritative record. When the policy is `"default"`, the generated specialist should contain no `launch.system_skills` entry. When it is `"none"`, the specialist contains `mode: none` and the run metadata says so.

## Risks / Trade-offs

- **Extra files in managed fixture homes** → System-skill projection adds the four agent-pack directories. Tests that assert an empty `skills/` directory must be updated or made policy-aware. The opt-out remains available for isolation cases.
- **Slower manager fixture launches** → The agent pack projection is local and small; the cost is bounded. The existing manager integration test already launches a harmless client and can absorb one more assertion.
- **Hidden test dependence on the old default** → Existing tests that rely on no system skills may change behavior. Search for `--no-system-skills` and `system_skills` in fixture tests and update them explicitly.
- **Fixture-specific skill names becoming a maintenance burden** → Assertions should check for the current `agent` pack entrypoints (`houmao-agent-entrypoint`, `houmao-shared-routines`) through the system-skill discovery helper, not by hardcoding a full recursive tree list.

## Migration Plan

1. Add the configuration field and CLI flag.
2. Stop passing `--no-system-skills` on the default manager path; pass it only for the opt-out.
3. Update fixture guidance and tests.
4. Run the fixture integration suite and the focused system-skill tests.
5. No data migration or rollback steps are required; prepared runs are disposable and each run records its own policy.

## Open Questions

None.

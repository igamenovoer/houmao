## Context

`houmao-agent-loop-pairwise` currently points at the enriched pairwise skill tree that absorbed responsibilities beyond the earlier stable pairwise contract. That enriched tree now covers authoring, prestart, and expanded run control, while the historical stable pairwise skill only exposed a simpler master-owned authoring plus `start|status|stop` surface.

The requested change deliberately splits those two contracts:

- `houmao-agent-loop-pairwise` becomes the restored stable skill name and behavior.
- `houmao-agent-loop-pairwise-v2` becomes the explicit versioned home for the enriched workflow.

This is cross-cutting because the skill asset tree, packaged catalog, install selection, visible home projections, docs, and catalog-driven tests all derive from the same skill inventory.

Constraints:

- Both skills must remain manual-invocation-only.
- `user-control` must include both skills, which means managed-home auto-install and CLI-default install both pick them up through set expansion.
- The stable `houmao-agent-loop-pairwise` surface is intentionally breaking back to the earlier contract rather than preserving backward compatibility.
- The change should not revive `houmao-loop-planner`; the split is between the old pairwise contract and the current enriched pairwise contract.

## Goals / Non-Goals

**Goals:**

- Restore the earlier `houmao-agent-loop-pairwise` contract under the original skill name and asset directory.
- Introduce `houmao-agent-loop-pairwise-v2` as the versioned home for the current enriched pairwise skill tree.
- Keep both skills manual-invocation-only in their descriptions, prompts, and guardrails.
- Make packaged catalog resolution, system-skills CLI output, and projected tool-home installs expose both skills through `user-control`.
- Update narrative and reference docs so readers can distinguish the stable pairwise skill from the enriched v2 skill.

**Non-Goals:**

- Reviving `houmao-loop-planner` as an installable packaged skill.
- Preserving the enriched workflow under the stable `houmao-agent-loop-pairwise` name.
- Introducing alias-based backward compatibility where invoking `houmao-agent-loop-pairwise` silently routes to v2.
- Reworking relay-skill behavior beyond any doc or catalog wording needed for consistency.

## Decisions

### Decision: Restore the stable pairwise skill from the pre-rewrite asset tree

`houmao-agent-loop-pairwise` will be restored from the pre-`6f7cbae1` packaged asset tree rather than approximated by manually deleting pages from the current enriched tree.

Rationale:

- The historical asset tree already captures the intended stable surface (`start|status|stop`) and manual-only wording.
- Using the historical tree avoids leaving accidental enriched wording, extra pages, or stale tests in the restored stable skill.

Alternatives considered:

- Trim the current enriched tree in place.
  Rejected because it is easy to miss embedded references to `initialize`, `peek`, `pause`, or other v2-only behavior.

### Decision: Create `houmao-agent-loop-pairwise-v2` by copying the current enriched tree verbatim first, then renaming internal identifiers

The new v2 skill will be created from the current enriched pairwise tree at implementation time, then its internal skill identifiers, descriptions, prompts, docs, and tests will be updated to use `houmao-agent-loop-pairwise-v2`.

Rationale:

- The user explicitly wants the current version to become v2.
- Copying the current tree preserves all currently shipped enriched behavior instead of re-deriving it from older commits.
- This keeps the split mechanical and reviewable: restore old stable tree, copy current enriched tree to v2, then update catalog/docs/tests.

Alternatives considered:

- Reconstruct v2 from git history before the latest local edits.
  Rejected because that would not actually preserve the current version.

### Decision: Keep both skills in `user-control`

The packaged catalog will list both `houmao-agent-loop-pairwise` and `houmao-agent-loop-pairwise-v2` in the `user-control` set, which means managed launch, managed join, and CLI-default installation all receive both through existing set expansion.

Rationale:

- The user explicitly requested this policy.
- It keeps the current auto-install model simple: both pairwise surfaces are available wherever `user-control` is installed.

Alternatives considered:

- Keep v2 installable only by explicit `--skill`.
  Rejected because it conflicts with the requested default availability.

### Decision: Treat the stable-name rollback as a documented breaking change rather than adding compatibility shims

The stable name will change behavior back to the older contract, and callers that need the enriched workflow must move to `houmao-agent-loop-pairwise-v2`.

Rationale:

- The repository already permits breaking changes during active development.
- Hidden compatibility shims would make the skill inventory ambiguous and undermine the point of explicit versioning.

Alternatives considered:

- Keep both names but make `houmao-agent-loop-pairwise` a wrapper that points to v2.
  Rejected because it would not restore the previous stable behavior under the original name.

## Risks / Trade-offs

- [Behavioral break for current pairwise callers] → Document the rollback clearly in proposal, specs, docs, and release-facing summaries; require enriched callers to switch to `houmao-agent-loop-pairwise-v2`.
- [Catalog and installer churn expands test fallout] → Update catalog-driven tests and projected-home assertions in the same change so the new inventory is validated end-to-end.
- [Stable and v2 trees drift inconsistently during the split] → Restore the stable tree from the historical asset snapshot and create v2 from the current tree before making targeted rename edits.
- [Docs become ambiguous about which pairwise skill to use] → Add explicit stable-versus-v2 wording in README, system-skills overview, and CLI reference coverage.

## Migration Plan

1. Restore the pre-rewrite pairwise asset tree under `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise/`.
2. Copy the current enriched pairwise asset tree to `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v2/`.
3. Rename internal skill ids, descriptions, prompts, and doc references inside the copied v2 tree.
4. Update `catalog.toml`, named-set membership, and any installer-facing expectations so both skills resolve through `user-control`.
5. Update docs and tests to reflect the stable rollback plus the new `-v2` skill.
6. Reinstall or rebuild managed homes as needed so projected skill trees reflect the new catalog inventory.

Rollback strategy:

- Revert the change set to restore the single enriched `houmao-agent-loop-pairwise` inventory if the split proves unusable.

## Open Questions

- None for the proposal stage; the requested default-set policy and manual-invocation-only posture are already decided.

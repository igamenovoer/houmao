## Context

`houmao-utils-llm-wiki` is currently a packaged Houmao-owned system skill under `src/houmao/agents/assets/system_skills/`, listed in `catalog.toml`, included in the `all` set, installed by CLI-default explicit `system-skills install`, and referenced by docs, tests, and OpenSpec requirements. The user intent for this change is a complete removal from Houmao's system-skill surface, not a soft retirement that keeps hidden cleanup or compatibility behavior.

The existing system-skill installer distinguishes current catalog skills from known retired loop skills. That retired path is useful for loop migrations, but it would hide this removal by continuing to treat `houmao-utils-llm-wiki` as Houmao-owned. This change should instead make the name unknown to Houmao.

## Goals / Non-Goals

**Goals:**

- Remove the packaged `houmao-utils-llm-wiki` asset tree from the repository.
- Remove the skill from the packaged current catalog, `all` set, auto-install/default resolution, docs, tests, and examples.
- Ensure explicit system-skill selection of `houmao-utils-llm-wiki` fails clearly as an unknown system skill.
- Keep existing system-skill cleanup boundaries honest: user-managed symlinks or stale external installed copies are outside this change.

**Non-Goals:**

- Do not add `houmao-utils-llm-wiki` to `retired_skill_names`.
- Do not add special-case cleanup for `.claude`, `.codex`, `.github`, `.kimi-code`, managed-home, or other externally installed `houmao-utils-llm-wiki` copies.
- Do not migrate user recipes, profiles, launch dossiers, or local skill-home symlinks that mention the removed skill.
- Do not remove or redesign unrelated LLM Wiki material that is not part of Houmao's packaged system-skill catalog unless implementation discovers it is only reachable through the removed package.

## Decisions

1. Hard-remove rather than retire in the catalog.

   `catalog.toml` should remove `[skills.houmao-utils-llm-wiki]` and should not add the name to `retired_skill_names`. This makes list/install/status/uninstall behavior match the new ownership boundary: Houmao no longer recognizes the skill.

   Alternative considered: add the name to `retired_skill_names` so system-skill install and uninstall can clean stale projections. That would be friendlier operationally, but it contradicts the requested "remove completely, do not hide it" behavior by keeping the name as a known Houmao-owned projection.

2. Preserve generic policy mechanics, replace examples with a surviving current skill.

   Source and profile system-skill policy support remains. Tests and docs that use `houmao-utils-llm-wiki` merely as an example valid explicit skill should switch to `houmao-utils-workspace-mgr` or another current skill. Tests that are specifically about removed names should assert unknown-skill failures.

   Alternative considered: remove additive utility examples entirely. That would reduce coverage for explicit skill policy behavior, so it is better to keep the generic behavior covered with a current skill.

3. Treat stale installed copies as user-managed external state.

   A target home containing `skills/houmao-utils-llm-wiki/` should no longer have that path reported as current or retired Houmao-owned state, and Houmao should not remove it through system-skill install/sync/uninstall. Operators can delete such paths manually.

   Alternative considered: add a one-time migration cleanup. That again creates hidden ownership of a supposedly removed skill and risks deleting user-managed copies.

## Risks / Trade-offs

- Existing stored configs can break on next launch if they still request `houmao-utils-llm-wiki` as a system skill → The failure should be explicit and identify the unknown system skill, making the stale selector visible rather than silently ignored.
- Stale installed copies remain on disk → This is intentional; external/user-managed symlinks and copies are out of scope and the user will clean them.
- Docs and specs have many historical references → Implementation should update current docs and main specs, but archived OpenSpec changes may retain historical references.

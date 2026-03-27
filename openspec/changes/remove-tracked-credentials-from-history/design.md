## Context

The current `origin/devel` history still contains a tracked Codex auth payload at `tests/fixtures/agents/tools/codex/auth/personal-a-default/files/auth.json`. Because that commit remains reachable from the branch tip, a fresh clone still downloads the credential-bearing blob. The repo also mixes tracked auth fixture templates with ignored local-only env files, which leaves the policy unclear and makes it easy to accidentally commit new credential files under fixture trees.

This change crosses git history management, remote ref hygiene, fixture layout policy, and ignore rules. It also has operational consequences because collaborators with existing clones will retain the old objects until they resync or reclone, and the leaked credentials must be rotated outside the repo cleanup.

## Goals / Non-Goals

**Goals:**
- Remove the tracked `auth.json` from reachable branch history so normal new clones do not materialize that payload.
- Define a repeatable repo workflow for force-updating refs after the rewrite and checking that no fetched refs still point at the leaked commit.
- Tighten ignore rules so credential env files, auth payloads, OAuth token dumps, and similar files remain local-only by default.
- Preserve fixture structure only where tests need secret-free placeholders or templates.
- Make the tracked-fixture contract explicit in specs so future changes do not reintroduce real credentials.

**Non-Goals:**
- Guarantee removal of unreachable objects from GitHub storage or caches after the rewrite.
- Preserve compatibility for local clones that already contain the leaked history.
- Automate credential rotation for external providers.
- Redesign the agent fixture layout beyond credential hygiene requirements.

## Decisions

### Rewrite reachable history instead of deleting the file in a forward commit

Deleting `auth.json` in a new commit is insufficient because fresh clones would still receive the old blob through reachable history. The change will instead rewrite the relevant branch history so the tracked Codex `auth.json` is absent from reachable refs, then force-update the remote branch.

Alternative considered:
- Forward deletion only. Rejected because it does not satisfy the new-clone requirement.

### Scope the history rewrite to tracked credential payloads, not every auth-related template

The rewrite should remove the tracked Codex `auth.json` from reachable history. Secret-free structural fixtures such as empty `credentials.json`, `claude_state.template.json`, or placeholder-only `oauth_creds.json` may remain tracked where tests need them.

Alternative considered:
- Remove every tracked file under `*/auth/*` from history. Rejected because several tracked fixtures are valid templates and removing them would weaken fixture coverage.

### Prefer explicit repo ignore patterns for credential-bearing files plus path-level fixture protection

The repo already ignores generic secret-like patterns such as `*.env` and `*credentials*`, but that is not sufficient to communicate policy or protect files like `auth.json` consistently across fixture trees. The change should add explicit ignore coverage for auth payload file names and auth directory content while preserving tracked placeholders and templates through targeted negations where needed.

Alternative considered:
- Rely on the existing broad ignore globs. Rejected because the current rules still allowed tracked credential payloads and do not document the intended auth-file policy.

### Require secret-free tracked fixture auth files by spec, not by convention only

The tracked-fixture contract should be enforceable at the spec layer: tracked auth fixtures may only contain placeholders, empty objects, or bootstrap templates with no live tokens. Real credentials must live in ignored local-only files.

Alternative considered:
- Keep this as README guidance only. Rejected because the existing guidance proved insufficient.

## Risks / Trade-offs

- [History rewrite disrupts collaborators with old clones] → Document the resync procedure and expect force-reset or reclone after the remote ref update.
- [A remote tag or side branch still points at the leaked commit] → Inventory all fetched refs before and after the rewrite, and delete or move any remaining refs that keep the old commit reachable.
- [Overly broad ignore rules block intentional tracked templates] → Use explicit negations for known safe template files and verify fixture paths after updating `.gitignore`.
- [GitHub still retains unreachable objects internally] → Treat ref cleanup as the requirement for new clones, and separately handle provider rotation plus any GitHub support follow-up if deeper purge is needed.

## Migration Plan

1. Rotate or revoke the leaked credential outside the repo.
2. Replace the tracked `auth.json` in the working tree with a safe placeholder or remove it from tracked fixtures, depending on the final fixture policy.
3. Update `.gitignore` and any fixture-local ignore files so auth payloads and credential env files remain untracked by default, while explicitly allowing safe templates.
4. Rewrite local history to remove the tracked `auth.json` from all refs that will remain reachable.
5. Force-update the canonical remote branch refs and remove any tags or auxiliary refs that still expose the leaked commit.
6. Verify that the cleaned branch tip and fetched refs no longer expose the old `auth.json`, then communicate the resync requirement to collaborators.

Rollback strategy:
- Keep a local backup ref before rewriting so the team can recover pre-rewrite state if the cleanup plan needs adjustment before the force-push.
- Do not restore the leaked commit to public remote refs once cleanup has started; if the rewrite is flawed, rebuild and force-push a corrected sanitized history instead.

## Open Questions

- Should the sanitized tracked Codex fixture remain as an empty or placeholder `auth.json`, or should the tracked file disappear entirely with only ignored local copies supported?
- Do any repo-owned tags or non-default branches currently need to remain publicly accessible while still pointing at the leaked commit?
- Should the repo add a pre-commit or CI guard that rejects tracked auth payload files under fixture auth directories in addition to `.gitignore` hardening?

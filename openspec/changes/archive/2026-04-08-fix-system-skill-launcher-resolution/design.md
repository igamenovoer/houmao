## Context

The current packaged system skills teach agents to "resolve the correct `houmao-mgr` launcher" by searching development-environment paths before trying the ordinary installed command. In practice, that makes agents inspect `.venv`, Pixi, and project-local uv state even when `houmao-mgr` is already available on `PATH`, and it biases the skill contract toward repository-maintainer workflows instead of the documented end-user install path in `README.md`.

This is a cross-cutting wording change rather than a runtime-behavior change. The implementation surface spans seven top-level skill routers, one shared launcher reference page, dozens of action pages that inherit the launcher abstraction, and tests/specs that currently lock in the old precedence.

## Goals / Non-Goals

**Goals:**

- Make the packaged skill contract prefer `command -v houmao-mgr` as the normal first step.
- Make uv the default fallback when the PATH lookup fails.
- Keep development-environment launchers available, but only after the default PATH and uv options fail or when the user explicitly requests them.
- Ensure all affected skills describe the same launcher policy and the same user-override behavior.
- Reduce action-page wording that encourages agents to re-invent launcher probing logic.

**Non-Goals:**

- Changing `houmao-mgr` runtime behavior or the CLI itself.
- Changing project developer documentation such as the Pixi-based repo workflow unless it is needed to explain the skill contract.
- Removing support for Pixi, repo-local `.venv`, or project-local `uv run` launchers.

## Decisions

### 1. The default launcher contract will become PATH first, not repo-hint first

The skill text will explicitly tell agents to run `command -v houmao-mgr` first and treat that resolved command as the ordinary launcher for the current turn.

Why:

- It matches how installed commands are normally discovered.
- It avoids expensive ad hoc probing of development-only paths.
- It works equally for global installs, shell shims, and user-managed PATH setups.

Alternative considered:

- Keep the current repo-hint-first search order. Rejected because it optimizes for a narrow development case and causes unnecessary probing in the normal case.

### 2. The ordinary fallback after PATH failure will be a uv-tool launcher

When `command -v houmao-mgr` fails, the skills will direct agents to try a uv-managed fallback aligned with the documented installation path, specifically `uv tool run --from houmao houmao-mgr`.

Why:

- The documented install path is `uv tool install houmao`.
- A uv-tool fallback is a better match for an end-user install than project-local `uv run houmao-mgr`.
- It keeps the fallback semantics tied to the packaged Houmao tool rather than to the current repo checkout.

Alternative considered:

- Use `uv run houmao-mgr` as the default fallback. Rejected because that is a project-local development lane, not the documented ordinary install lane.

### 3. Development launchers will remain supported, but as later or explicit lanes

The updated skills will still allow `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, and project-local `uv run houmao-mgr`, but only after PATH lookup and uv-tool fallback do not satisfy the turn, or when the user explicitly asks for one of those launchers.

Why:

- Maintainers still need development-lane guidance.
- The user explicitly asked to keep those options, but not as the default first search.

Alternative considered:

- Remove development launchers from the skills entirely. Rejected because the repo still uses those workflows in development and testing.

### 4. Explicit user launcher instructions override the default order

Each affected skill will state that if the user says to use Pixi, a repo `.venv`, project-local `uv run`, or another specific launcher, the skill must follow that instruction instead of substituting the default PATH-first launcher.

Why:

- It makes the exception path unambiguous.
- It prevents the new default order from fighting explicit operator intent.

Alternative considered:

- Leave override behavior implicit. Rejected because the user requested it explicitly and ambiguity would leak back into agent behavior.

### 5. Action pages should stop encouraging independent launcher-search logic

Implementation should update action pages that currently say "Use the launcher resolved from the top-level skill" and show `<resolved houmao-mgr launcher>` so they align with the new contract. The action pages may still refer to a chosen launcher, but they should not preserve wording that nudges agents back toward multi-path manual probing.

Why:

- The current placeholder is repeated 45 times and is part of how the old search behavior propagates.
- A top-level-only rewrite would leave latent ambiguity in the downstream action text.

Alternative considered:

- Update only the top-level routers. Rejected because the action pages would still encode a vague resolution step that models can re-expand into the old behavior.

## Risks / Trade-offs

- [Risk] Changing the written launcher contract may invalidate tests and archived assumptions that currently expect `uv run houmao-mgr` or repo-hint-first wording. → Mitigation: update the affected OpenSpec capability specs and unit tests in the same implementation change.
- [Risk] `uv tool run --from houmao houmao-mgr` may be more verbose than the old wording. → Mitigation: keep it only as the fallback lane; PATH-first remains the normal case.
- [Risk] Some action pages may still imply launcher re-resolution after the top-level edit. → Mitigation: include the repeated action-page placeholder cleanup in the implementation tasks.
- [Risk] The historical spec name `houmao-create-specialist-skill` does not match the packaged skill name `houmao-manage-specialist`. → Mitigation: modify the existing capability in place and state that mapping explicitly in proposal/spec text.

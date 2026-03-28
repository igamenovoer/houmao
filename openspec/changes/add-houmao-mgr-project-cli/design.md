## Context

Houmao currently has two awkward onboarding assumptions for local operator workflows:

- the operator will manually copy or assemble an agent-definition tree before the CLI can do useful work, and
- local auth bundles will be created by hand under that tree with no first-class CLI support.

The existing runtime model already distinguishes between per-user Houmao-owned roots under `~/.houmao` and workspace-local scratch under `<working-directory>/.houmao/jobs/`, but there is no first-class repo-local Houmao project overlay that represents "local Houmao state for this arbitrary repository". At the same time, the packaged build explicitly excludes `tests/`, so `project init` cannot depend on `tests/fixtures/agents/` as its starter source.

This change is cross-cutting because it affects:

- the `houmao-mgr` top-level command tree,
- default agent-definition-root resolution used by build and launch flows,
- packaging of starter project assets,
- local auth-bundle authoring workflows, and
- getting-started documentation.

## Goals / Non-Goals

**Goals:**

- Introduce a first-class repo-local Houmao project overlay rooted at `.houmao/`.
- Add `houmao-mgr project` as the supported local project bootstrap and inspection surface.
- Make `.houmao/houmao-config.toml` the project-local source of truth for project-aware defaults.
- Seed a usable local `agents/` tree from packaged secret-free assets rather than from test fixtures.
- Add credential-authoring commands that write directly into the existing tool auth-bundle layout under `.houmao/agents/tools/<tool>/auth/<name>/`.
- Keep the entire repo-local Houmao overlay untracked by default through `.houmao/.gitignore` without mutating the repository root `.gitignore`.
- Preserve existing explicit CLI and env-var overrides and keep legacy `.agentsys/agents` fallback behavior when no project config exists.

**Non-Goals:**

- Replacing the per-user shared Houmao roots under `~/.houmao` for runtime, registry, or mailbox state.
- Redesigning the auth-bundle projection contract, tool adapters, or runtime bootstrap rules.
- Introducing a second credential registry format separate from `tools/<tool>/auth/<name>/`.
- Making project-local mailbox-root resolution or job-root resolution project-aware in this change.
- Auto-generating shareable tracked role or preset content for the repository; the project overlay remains local operator state.

## Decisions

### Decision 1: Define a repo-local Houmao overlay rooted at `<repo>/.houmao/`

The project-local Houmao surface is one hidden directory tree rooted at:

```text
<project-root>/.houmao/
```

At minimum, `project init` creates:

- `.houmao/houmao-config.toml`
- `.houmao/.gitignore`
- `.houmao/agents/`

The config file lives inside `.houmao/` rather than at the repo root so the local overlay stays self-contained and can be ignored as one unit.

Rationale:

- The user explicitly wants local-only Houmao state that does not pollute the visible repo root.
- Keeping config, generated local sources, and local credentials under one hidden root avoids a split-brain contract.
- This does not conflict with the existing per-user `~/.houmao` root because the distinction is based on anchor location: project-local overlay vs per-user shared ownership.

Alternatives considered:

- Put `houmao-config.toml` at the repo root: rejected because it pollutes arbitrary git repos and weakens the "all local Houmao state is under `.houmao/`" rule.
- Reuse `.agentsys/` as the new local project root: rejected because the user explicitly wants `.houmao/`, and the repository has already standardized Houmao naming elsewhere.

### Decision 2: Use nearest-ancestor `.houmao/houmao-config.toml` discovery for project-aware defaults

Project-aware resolution will walk upward from the caller's current working directory looking for the nearest ancestor `.houmao/houmao-config.toml`.

For agent-definition-root resolution, precedence is:

1. explicit CLI `--agent-def-dir`,
2. `AGENTSYS_AGENT_DEF_DIR`,
3. nearest discovered project config,
4. legacy fallback `<cwd>/.agentsys/agents`.

The project config stores relative paths relative to the config directory itself, so `agent_def_dir = "agents"` resolves to `<project-root>/.houmao/agents`.

Rationale:

- Operators will often invoke `houmao-mgr` from subdirectories of a working repo, not only from the repo root.
- The existing explicit override and env-var surfaces are already established and should remain strongest.
- Keeping the legacy fallback avoids breaking non-project workflows that still rely on `.agentsys/agents`.

Alternatives considered:

- Discover only from the immediate current directory: rejected because it makes project behavior brittle from repo subdirectories.
- Add a separate new env var for project root: rejected because existing explicit and env override surfaces are already sufficient for v1.

### Decision 3: `project init` writes only inside `.houmao/` and uses `.houmao/.gitignore` with `*`

`project init` will not touch the repository root `.gitignore`.

Instead, it creates:

```text
.houmao/.gitignore
```

with content:

```gitignore
*
```

This keeps the entire project-local Houmao overlay untracked by default, including local credentials, local agent-definition content, and future local project metadata.

Rationale:

- The user explicitly wants the overlay to remain local-only.
- Mutating the repo root `.gitignore` would be invasive in arbitrary repositories and violates the desired ownership boundary.
- Ignoring the entire subtree is simpler and safer than trying to curate subpath-specific ignore rules for a local-only overlay.

Alternatives considered:

- Write selective ignore rules only for credential paths: rejected because the user wants the whole overlay local-only.
- Add `!.gitignore` to keep `.houmao/.gitignore` tracked: rejected because that would make the local helper file itself appear in `git status`.

### Decision 4: Seed `.houmao/agents/` from packaged starter assets, not from `tests/fixtures/agents/`

`project init` seeds `.houmao/agents/` from bundled package assets that ship with Houmao. Those assets will include:

- the canonical directory skeleton,
- current supported tool adapters,
- current supported secret-free tool setup bundles,
- minimal placeholder content for local-only project authoring where appropriate.

They will not depend on `tests/fixtures/agents/`, because `tests/**` is excluded from built distributions.

Rationale:

- The packaged CLI must be able to initialize a project without requiring repository-only fixture trees.
- Tool adapters and secret-free setups are part of the supported operator surface, so `project init` needs a packaged source of truth for them.
- Keeping starter assets packaged separately from tests avoids shipping test-only fixture baggage and avoids coupling runtime behavior to repository layout.

Alternatives considered:

- Copy directly from `tests/fixtures/agents/`: rejected because those files are not shipped in wheel or sdist outputs.
- Generate adapters and setup bundles entirely in code: rejected because the repository already has file-based adapters and setup content that should remain human-inspectable assets.

### Decision 5: `project credential` writes tool-aware auth bundles into the existing source layout

`houmao-mgr project credential add <tool> ...` will author local auth bundles directly under:

```text
.houmao/agents/tools/<tool>/auth/<name>/
```

The command surface is tool-aware rather than pretending every tool uses the same auth inputs. In v1:

- Claude writes env-backed auth input and any required local bootstrap template files for the current adapter contract.
- Codex writes env-backed auth input and optional compatible local auth files such as `auth.json` when supplied.
- Gemini writes env-backed auth input and optional local auth files required by the current adapter contract.

`project credential list` enumerates local bundles already present in the project overlay, and `project credential remove` removes one named bundle for one tool.

Rationale:

- The current runtime model already treats auth as a tool-specific on-disk bundle, not as a separate abstract credential database.
- Writing directly into the existing bundle shape keeps builder and runtime compatibility simple.
- Tool-aware subcommands let the CLI remain honest about Claude/Codex/Gemini differences instead of hiding them behind an underspecified generic flag set.

Alternatives considered:

- Create a separate project credential registry and translate it later during build: rejected because it duplicates the existing auth-bundle model and adds another sync problem.
- Make `credential add` fully generic with one common flag schema: rejected because the current adapters have materially different env/file requirements.

### Decision 6: Keep mailbox and job-root project integration out of scope for v1

This change will not make `.houmao/houmao-config.toml` redefine:

- default mailbox-root resolution for `houmao-mgr mailbox ...`, or
- workspace-local job-root resolution for runtime scratch output.

Those surfaces remain on their current contracts for now.

Rationale:

- The user's immediate need is project bootstrap, local agent-definition source setup, and local credential authoring.
- Mailbox-root and job-root precedence changes would expand the change into additional spec areas with separate behavioral consequences.
- Deferring them keeps the first project-local CLI slice coherent and implementable.

Alternatives considered:

- Make every existing `.houmao/*` path project-aware immediately: rejected because it would widen the change substantially and entangle unrelated defaults.

## Risks / Trade-offs

- [Risk] Operators may confuse project-local `.houmao/` with per-user `~/.houmao/`. → Mitigation: document the distinction explicitly in CLI and getting-started docs as local overlay vs shared Houmao-owned roots.
- [Risk] Bundled starter assets may drift from the canonical repository fixture layouts over time. → Mitigation: keep starter assets as repo-owned package data derived from the same maintained tool adapter and setup definitions, and test `project init` against packaged assets directly.
- [Risk] Credential commands that accept secret values as CLI flags can leak into shell history. → Mitigation: document that trade-off clearly in help/docs for v1 and keep the on-disk bundle layout compatible with future safer input modes.
- [Risk] Upward project discovery could select an unexpected ancestor in nested repositories. → Mitigation: use nearest-ancestor semantics and expose `project status` so operators can inspect the resolved project root and agent-definition root.
- [Risk] Keeping legacy `.agentsys/agents` fallback could prolong mixed workflows. → Mitigation: update docs to prefer `project init` while preserving fallback only as a compatibility path.

## Migration Plan

1. Add packaged project-starter assets for supported tool adapters and secret-free setup bundles.
2. Add a project-context resolver that discovers `.houmao/houmao-config.toml` and resolves project-relative paths.
3. Introduce `houmao-mgr project init`, `project status`, and `project credential ...`.
4. Update build and launch agent-definition-root resolution to consult the discovered project config before falling back to legacy `.agentsys/agents`.
5. Update CLI and getting-started docs to present `project init` as the supported local onboarding path.
6. Keep legacy `.agentsys/agents` fallback behavior in place until a later explicit retirement change removes it.

## Open Questions

No open questions remain for this change. Mailbox-root and job-root project integration are explicitly deferred rather than left ambiguous.

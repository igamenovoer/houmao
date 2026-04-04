## Context

The feature worktree already introduced a repo-local `.houmao/` overlay and a `houmao-mgr project credential ...` command family that writes auth bundles into the existing tool-local storage model. That storage model is already documented as:

```text
.houmao/agents/tools/<tool>/auth/<name>/
```

The mismatch is purely at the CLI vocabulary layer: the command says "credential", while the filesystem, docs, and tool adapters already say "tool auth bundle". Because this change is still confined to the feature worktree and the repository explicitly allows breaking CLI changes during active development, the better move is to reshape the project subtree now instead of freezing the wrong noun and aliasing around it later.

This redesign is still cross-cutting because it touches:

- the `houmao-mgr project` command tree,
- project CLI help text and focused tests,
- project auth-bundle read/write semantics (`add` vs `set` vs `get`),
- and multiple docs that currently teach `project credential ...`.

## Goals / Non-Goals

**Goals:**

- Align project-local auth-bundle commands with the existing `.houmao/agents/tools/<tool>/auth/<name>/` layout.
- Make the tool name a first-class path segment in the CLI rather than a hidden parameter of a top-level `credential` noun.
- Expose explicit CRUD semantics for local auth bundles through `list`, `add`, `get`, `set`, and `remove`.
- Preserve the existing on-disk auth-bundle layout and project-overlay discovery rules.
- Leave room for future tool-scoped project commands such as setup or adapter inspection without another naming reset.

**Non-Goals:**

- Changing `.houmao/` overlay layout, project discovery precedence, or the tool adapter projection contract.
- Introducing a second credential database or manifest file.
- General-purpose editing for arbitrary unknown custom tools in this slice.
- Expanding the project subtree to manage roles, skills, or compatibility profiles in this same change.

## Decisions

### Decision 1: Replace `project credential` with `project agent-tools`

The `project` subtree will keep `init` and `status`, but the auth-management branch becomes:

```text
houmao-mgr project agent-tools ...
```

Rationale:

- `agent-tools` matches the actual subtree under `.houmao/agents/tools/`.
- `credential` incorrectly suggests a separate registry abstraction that does not exist.
- `agent-tools` leaves room for future subtrees under a tool, such as `setups` or `adapter`, without another rename.

Alternatives considered:

- Keep `project credential` and only improve help text: rejected because the CLI noun would still disagree with the source tree.
- Use `project agents tools ...`: rejected because it mirrors the directory tree too literally and makes the operator-facing CLI noisier than necessary.

### Decision 2: Structure the subtree as `project agent-tools <tool> auth <verb>`

The supported path becomes:

```text
houmao-mgr project agent-tools <tool> auth <verb>
```

In v1, the supported tool command families remain Houmao-owned tools:

- `claude`
- `codex`
- `gemini`

Rationale:

- The command path mirrors the source tree order: tools first, then one tool, then its auth bundles.
- Tool-specific flags remain honest about adapter differences.
- Static tool families preserve clean `--help` output and stable parsing for tool-specific flags.

Alternatives considered:

- A generic `project agent-tools auth <tool> ...` command with one union of flags: rejected because it obscures the tree shape and makes help output harder to understand.
- A generic raw editor for env vars and files: rejected because the current operator surface is intentionally tool-aware, not a low-level bundle editor.

### Decision 3: Make `auth` a CRUD surface with explicit create/read/update/delete behavior

Each supported tool exposes:

- `auth list`
- `auth add --name ...`
- `auth get --name ...`
- `auth set --name ...`
- `auth remove --name ...`

Semantics:

- `add` creates a new auth bundle and fails if the named bundle already exists.
- `get` inspects one existing auth bundle.
- `set` updates one existing auth bundle and fails if the named bundle does not exist.
- `remove` deletes one existing auth bundle.
- `list` enumerates bundle names for one tool.

Rationale:

- Once both `add` and `set` exist, the CLI should stop overloading "add" to mean create-or-update.
- Explicit CRUD semantics make the command family predictable and easier to test.
- This still maps directly to one auth-bundle directory on disk rather than inventing a higher-level data model.

Alternatives considered:

- Keep `add` as create-or-update and introduce `set` as an alias: rejected because it makes the verbs redundant.
- Use `show` instead of `get`: rejected because `get/set/remove` is a tighter bundle and mirrors read/update/delete semantics better.

### Decision 4: Keep tool-specific flags, but treat env/file storage as an implementation detail

The CLI remains tool-aware:

- Claude maps flags such as `--api-key`, `--auth-token`, `--base-url`, and `--state-template-file` onto its adapter allowlist and files.
- Codex maps `--api-key`, `--base-url`, `--org-id`, and `--auth-json`.
- Gemini maps `--api-key`, `--google-api-key`, `--use-vertex-ai`, and `--oauth-creds`.

The storage layout remains:

```text
.houmao/agents/tools/<tool>/auth/<name>/
├── env/vars.env
└── files/...
```

Rationale:

- The adapters already define the env/file contract, so the CLI should speak in tool-level option names rather than raw directory editing primitives.
- Preserving the storage layout avoids any migration or translation layer.

Alternatives considered:

- Expose raw env-var names and file destinations directly in the CLI: rejected because that leaks adapter internals and makes the operator surface harder to learn.

### Decision 5: `auth get` redacts secret values by default, and `auth set` uses patch semantics

`auth get` will return structured data for one bundle, but secret-like values such as API keys and auth tokens are redacted by default. File-backed auth material is reported as presence/path metadata rather than dumping raw contents.

`auth set` only changes fields explicitly provided on the command line. Unspecified fields remain unchanged. If the CLI supports removal of specific fields, that removal should require explicit `--clear-*` flags rather than omission.

Rationale:

- The project overlay is local, but command output still lands in terminals and logs.
- Patch semantics make partial updates safe and avoid accidental deletion when the operator only wants to change one field.

Alternatives considered:

- Print raw secrets by default from `get`: rejected because that creates needless terminal-exposure risk.
- Treat missing flags on `set` as deletion: rejected because it makes updates error-prone.

### Decision 6: Remove `project credential` instead of keeping a long-term alias

This redesign should replace the current `project credential` subtree rather than keep both names active.

Rationale:

- The current project CLI is new and not merged; this is the cheapest point to correct the surface.
- Keeping both trees would prolong mixed terminology in docs, help text, and tests.

Alternatives considered:

- Keep a hidden compatibility alias for one release: rejected because it adds maintenance work to preserve a shape we already know is the wrong mental model.

### Decision 7: Reserve space for future tool-scoped operations, but keep this change auth-focused

The new shape intentionally leaves room for future commands such as:

```text
houmao-mgr project agent-tools claude setups ...
houmao-mgr project agent-tools claude adapter ...
```

This change only specifies `auth ...`.

Rationale:

- The naming reset is worthwhile only if it creates a stable hierarchy for future project-local tool administration.
- Keeping the spec auth-focused prevents this redesign from ballooning into setup or adapter management work right away.

## Risks / Trade-offs

- [Risk] The CLI becomes one level deeper and slightly more verbose. → Mitigation: the extra depth mirrors the directory tree exactly and removes the more expensive mental mismatch.
- [Risk] Supported tool families remain explicit (`claude`, `codex`, `gemini`), so custom tool auth still requires manual editing. → Mitigation: document that limit clearly and reserve `agent-tools` for future generic/raw extension if it becomes necessary.
- [Risk] `auth get` can still expose sensitive metadata if designed carelessly. → Mitigation: require redaction by default and avoid dumping file contents.
- [Risk] Early adopters of the feature branch may already know `project credential`. → Mitigation: make the rename now, before merge, and update docs/tests atomically.

## Migration Plan

1. Add a follow-on OpenSpec change for the CLI reshape so the rename is explicit.
2. Refactor `src/houmao/srv_ctrl/commands/project.py` from `credential`-centric grouping to `agent-tools/<tool>/auth/...`.
3. Update auth-bundle helpers so `add` and `set` have distinct existence checks, and add a redacted `get` path.
4. Rewrite focused CLI tests and help-output expectations around `agent-tools`.
5. Update active docs to use `project agent-tools <tool> auth ...` and sweep stale `project credential` wording.
6. Verify no on-disk migration is needed because auth bundles remain under the same directories.

## Open Questions

No open questions remain for this design. Custom-tool raw editing is explicitly deferred, and the on-disk auth-bundle contract stays unchanged.

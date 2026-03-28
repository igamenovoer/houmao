## Context

`houmao-mgr project` currently mixes several concerns without a coherent view model.

- The low-level project CLI uses `agent-tools` and planned `agent-roles`, even though the canonical project-local source tree is `.houmao/agents/{roles,tools,skills,...}`.
- The active `add-project-role-and-tool-management-cli` change assumes that synthetic naming model and therefore bakes the mismatch deeper into the design.
- The project workflow still lacks a simpler high-level authoring UX for users who want to describe a reusable specialist without hand-assembling role, preset, tool auth, and skill paths.
- The generic mailbox CLI manages mailbox roots directly, but repo-local workflows increasingly want the same mailbox operations against the current project's `.houmao/mailbox` root without repeating `--mailbox-root`.

The exploration log `context/logs/explore/20260328-172545-project-agents-cli-namespace-design.md` converged on a three-view model:

- `project agents ...` for filesystem-oriented project source management,
- `project easy ...` for intent-oriented specialist and instance UX,
- `project mailbox ...` for project-scoped mailbox operations that reuse the same mailbox semantics as the generic `mailbox` CLI.

This is a cross-cutting change because it touches the project CLI tree, mailbox CLI reuse, project overlay helpers, parser-facing authoring flows, and the repo-owned docs/spec model.

## Revised CLI Shape

The intended public CLI shape after this change is:

```text
houmao-mgr
├── project
│   ├── init
│   ├── status
│   ├── agents
│   │   ├── roles
│   │   │   ├── list
│   │   │   ├── get
│   │   │   ├── init
│   │   │   ├── scaffold
│   │   │   ├── remove
│   │   │   └── presets
│   │   │       ├── list
│   │   │       ├── get
│   │   │       ├── add
│   │   │       └── remove
│   │   └── tools
│   │       └── <tool>
│   │           ├── get
│   │           ├── setups
│   │           │   ├── list
│   │           │   ├── get
│   │           │   ├── add
│   │           │   └── remove
│   │           └── auth
│   │               ├── list
│   │               ├── add
│   │               ├── get
│   │               ├── set
│   │               └── remove
│   ├── easy
│   │   ├── specialist
│   │   │   ├── create
│   │   │   ├── list
│   │   │   ├── get
│   │   │   ├── remove
│   │   │   └── launch
│   │   └── instance
│   │       ├── list
│   │       └── get
│   └── mailbox
│       ├── init
│       ├── status
│       ├── register
│       ├── unregister
│       ├── repair
│       ├── cleanup
│       ├── accounts
│       │   ├── list
│       │   └── get
│       └── messages
│           ├── list
│           └── get
└── mailbox
    ├── init
    ├── status
    ├── register
    ├── unregister
    ├── repair
    ├── cleanup
    ├── accounts
    │   ├── list
    │   └── get
    └── messages
        ├── list
        └── get
```

The key view distinction is:

- `project agents ...` manages the canonical `.houmao/agents/` source tree directly.
- `project easy ...` offers a higher-level specialist/instance UX that compiles into that same canonical source tree.
- `project mailbox ...` mirrors the generic `mailbox ...` operations but resolves the mailbox root as `<project>/.houmao/mailbox`.
- `mailbox ...` remains the canonical generic mailbox-root command family for arbitrary roots outside project scope.

## Goals / Non-Goals

**Goals:**

- Replace the synthetic `project agent-tools` / `project agent-roles` naming with a filesystem-oriented `project agents ...` tree that mirrors `.houmao/agents/...`.
- Keep the low-level project authoring surface explicit and file-backed for roles, presets, setups, and auth bundles.
- Add a high-level `project easy ...` workflow that compiles user intent into the canonical `.houmao/agents/` tree rather than inventing a second runtime contract.
- Extend the generic `houmao-mgr mailbox ...` surface so mailbox-root operators can inspect mailbox accounts and list/get messages directly from a selected mailbox address.
- Add `houmao-mgr project mailbox ...` as a project-root wrapper over that same mailbox-root functionality, automatically targeting `<project>/.houmao/mailbox`.
- Preserve a clear separation between mailbox-root administration and managed-agent mailbox binding.
- Supersede the current in-progress project role/tool design direction with a coherent project view model before implementation spreads further.

**Non-Goals:**

- A full inline editor for role prompts, preset YAML, tool adapters, or tool setup bundle contents.
- Persisted per-instance overrides or a second launch contract distinct from managed-agent runtime state.
- Mailbox send/reply composition through `project mailbox` in this change; the direct mailbox expansion is limited to account lifecycle plus message listing/get.
- Project-scoped mailbox semantics that diverge from the generic mailbox-root CLI.
- Backward-compatibility shims as the documented public surface for `project agent-tools`; this change optimizes for the corrected public model.

## Decisions

### Decision 1: `project` exposes three distinct views: `agents`, `easy`, and `mailbox`

The supported `houmao-mgr project` tree becomes:

```text
houmao-mgr project
├── init
├── status
├── agents
├── easy
└── mailbox
```

The three subtrees intentionally serve different operator postures:

- `project agents ...`: direct filesystem-oriented management of `.houmao/agents/...`
- `project easy ...`: intent-oriented specialist and instance UX
- `project mailbox ...`: project-scoped mailbox-root operations

Rationale:

- The filesystem tree and the high-level UX should not be forced into the same command style.
- `project mailbox` belongs on `project` because it is a repo-local convenience rooted in `.houmao/`, but its semantics still belong to the mailbox subsystem.
- Separating these views reduces the need for overloaded verbs and keeps help text legible.

Alternatives considered:

- Put everything under `project agents ...`: rejected because mailbox is not part of `.houmao/agents/`, and `easy` is intentionally a different mental model.
- Keep only one low-level project surface and force users to author files directly: rejected because the specialist workflow is a real UX gap.

### Decision 2: `project agents` replaces the synthetic `agent-tools` / `agent-roles` naming

The low-level project authoring surface becomes:

```text
houmao-mgr project agents roles ...
houmao-mgr project agents tools <tool> ...
```

The command tree is intentionally aligned with the canonical source layout:

```text
.houmao/agents/roles/  <->  project agents roles
.houmao/agents/tools/  <->  project agents tools
```

Rationale:

- The extra `agents` segment adds real information: it identifies the managed project-local source root.
- The renamed tree scales naturally to future subtrees such as `skills` or `compatibility-profiles`.
- The public CLI and the documented directory tree stop contradicting each other.

Alternatives considered:

- Keep `project agent-tools` and add `project agent-roles`: rejected because it preserves the core naming mismatch.
- Rename to `project roles` / `project tools`: rejected because it hides the `.houmao/agents/` root and makes future grouping more ambiguous.

### Decision 3: `project easy` compiles into the canonical `.houmao/agents/` tree and uses metadata only for UX reconstruction

`project easy` introduces two user-facing concepts:

- `specialist`: reusable blueprint
- `instance`: launched or inspectable realization of a specialist

For v1:

- `specialist` is persisted as high-level UX metadata
- `instance` is a view over real managed-agent runtime state rather than a new persisted config layer

`specialist create` compiles into:

- `roles/<specialist>/system-prompt.md`
- `roles/<specialist>/presets/<tool>/default.yaml`
- `tools/<tool>/auth/<credential>/...`
- copied/imported `skills/<skill>/...`

The high-level metadata lives under:

```text
.houmao/easy/specialists/<name>.toml
```

That metadata records enough information for `specialist get`, `specialist launch`, and future updates, but it is not a second build or launch input. The canonical runtime inputs remain the compiled `.houmao/agents/` artifacts.

Rationale:

- Users need a simpler mental model without compromising the existing parser, build, and launch contracts.
- Keeping the canonical tree authoritative avoids a split-brain system where `easy` and `agents` disagree.
- Treating `instance` as a view over managed-agent runtime state avoids inventing per-instance persistence too early.

Alternatives considered:

- Make `easy` the new authoritative project format: rejected because it would duplicate the canonical parser/build inputs and make low-level/manual workflows harder to reason about.
- Persist full instance definitions immediately: rejected because the current concrete need is launch/inspect convenience, not a second layer of stored overrides.

### Decision 4: Specialist creation uses simple user-facing tool names and compiles credentials directly into tool auth bundles

`project easy specialist create` accepts:

- exactly one system prompt source: `--system-prompt` or `--system-prompt-file`
- one tool selector: `claude`, `codex`, or `gemini`
- one credential name plus tool-specific auth payload
- repeated `--with-skill <skill-dir>` inputs

User-facing tool names map to existing runtime lanes:

- `claude` -> preset tool `claude`, launch provider `claude_code`
- `codex` -> preset tool `codex`, launch provider `codex`
- `gemini` -> preset tool `gemini`, launch provider `gemini_cli`

Gemini remains headless-only in v1, and that restriction is reflected in `specialist launch`.

Credential handling compiles directly into the existing tool auth bundle layout instead of inventing a new credential store. Repeated `--with-skill` imports copy the source skill directories into `.houmao/agents/skills/` so the resulting project overlay remains self-contained.

Rationale:

- User-facing nouns should be stable and short even when internal provider identifiers differ.
- Direct compilation into auth bundles and copied skill trees keeps `easy` reproducible and debuggable.
- Skill copy-import is simpler and more deterministic than symlink semantics for a first slice.

Alternatives considered:

- Expose internal provider identifiers directly in `easy`: rejected because that leaks implementation detail and weakens the UX goal.
- Keep skills as references to external absolute paths: rejected because it breaks project portability and makes the overlay incomplete.

### Decision 5: `houmao-mgr mailbox` and `project mailbox` share one mailbox-root command model

The generic mailbox-root CLI expands to cover:

- root bootstrap/status/repair/cleanup
- mailbox-address lifecycle (`register` / `unregister`)
- account inspection (`accounts list|get`) derived from mailbox registrations
- direct message reads (`messages list|get`) for a selected mailbox address

`project mailbox` is not a different mailbox subsystem. It is a project-root wrapper over the same operations:

```text
houmao-mgr project mailbox <verb> ...
==>
houmao-mgr mailbox <verb> --mailbox-root <project-root>/.houmao/mailbox ...
```

For v1, the project mailbox root is fixed by convention at:

```text
<project-root>/.houmao/mailbox
```

and does not require a separate project-config mailbox path.

Rationale:

- The user clarified that `project mailbox` should feel like the same mailbox CLI with project-scoped root selection.
- One mailbox command model avoids drift between top-level and project-scoped mailbox behavior.
- A fixed `.houmao/mailbox` root is good enough for the current project-local use case and avoids premature configuration complexity.

Alternatives considered:

- Make `project mailbox` a separate project-only mailbox interface: rejected because it duplicates mailbox semantics and creates two slightly different operator models.
- Add configurable `paths.mailbox_root` to project config immediately: rejected for the first slice because the current use case only needs a fixed project-local root.

### Decision 6: `agents mailbox` remains a managed-session binding surface

Even after the generic and project mailbox-root CLIs are aligned, `houmao-mgr agents mailbox ...` remains separate.

Reasoning:

- `mailbox` and `project mailbox` operate on mailbox-root state
- `agents mailbox` operates on one running managed-agent session's mailbox binding and activation posture

That boundary stays intact. This change does not collapse mailbox-root administration into managed-session binding, and it does not make `project mailbox` inspect or mutate agent-session mailbox activation.

Alternatives considered:

- Move mailbox binding under `project mailbox`: rejected because it would mix mailbox-root administration with managed runtime state and make agent-session behavior harder to reason about.

### Decision 7: The current in-progress project role/tool change is superseded rather than incrementally amended

The current `add-project-role-and-tool-management-cli` artifacts assume the older `agent-tools` / `agent-roles` direction. This change supersedes that direction instead of layering more edits onto it.

Rationale:

- The naming and view-model changes are architectural, not cosmetic.
- A fresh change makes the revised scope explicit: namespace correction, high-level UX, and mailbox integration.

Alternatives considered:

- Keep revising the old change in place: rejected because it was scoped around a narrower assumption and no longer represents the intended implementation target clearly.

## Risks / Trade-offs

- [Risk] The `project` tree becomes broader and potentially harder to scan. → Mitigation: keep the split explicit by mental model (`agents`, `easy`, `mailbox`) and keep each subtree internally coherent.
- [Risk] Removing the documented `project agent-tools` surface is a breaking change. → Mitigation: update docs and tests in the same change; optionally keep hidden aliases only if implementation friction proves high.
- [Risk] `project easy` could drift from the canonical `.houmao/agents/` tree. → Mitigation: compile directly into the canonical tree and treat `.houmao/easy/...` metadata as non-authoritative UX state only.
- [Risk] Message-reading commands added to the generic mailbox CLI could accidentally imply more mailbox workflow support than intended. → Mitigation: keep the first slice limited to account inspection plus message list/get; leave send/reply and richer mailbox operations for follow-up changes.
- [Risk] Project-scoped mailbox root conventions may be mistaken for mailbox-session binding. → Mitigation: keep `agents mailbox` separate and document the distinction clearly in CLI help and reference docs.

## Migration Plan

1. Land the new project change artifacts and mark the older `add-project-role-and-tool-management-cli` direction as superseded in planning and implementation discussion.
2. Implement the `project agents ...` tree and move tests/docs to the new command paths.
3. Implement `project easy ...` on top of canonical `.houmao/agents/` compilation plus `.houmao/easy/...` metadata.
4. Extend the generic mailbox CLI with account/message inspection operations.
5. Add `project mailbox ...` as a root-resolved wrapper over the mailbox helpers.
6. Update getting-started and CLI reference docs so the new public surface is taught consistently.

Rollback posture:

- Because this is a CLI-surface redesign in an unstable repository, rollback means reverting the change set and restoring the prior documented command surface; no durable data migration is required for the renamed project role/tool commands.
- `project easy` metadata is additive and local-only, so removing the feature does not invalidate the canonical `.houmao/agents/` tree.

## Open Questions

- Whether hidden undocumented compatibility aliases for `project agent-tools` are worth the extra maintenance cost if the implementation change set proves large.
- Whether future mailbox-root configuration should become project-config-driven after the fixed `.houmao/mailbox` convention is established.
- Whether future `project easy` iterations should add persisted per-instance overrides, or continue treating `instance` strictly as a runtime view.

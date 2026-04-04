# Explore Log: project agents CLI namespace design

**Date:** 2026-03-28
**Topic:** Revise `houmao-mgr project` so the command tree matches the repo-local `.houmao/agents/` directory structure directly
**Mode:** `openspec-explore`

## Short Answer

The current `houmao-mgr project` namespace is inconsistent with the actual source tree it manages.

Today the real project-local root is:

```text
.houmao/agents/
├── roles/
└── tools/
```

But the CLI exposes:

```text
houmao-mgr project agent-tools ...
houmao-mgr project agent-roles ...
```

That skips the real `agents/` root and introduces a synthetic naming layer.

The cleaner design is:

```text
houmao-mgr project
├── init
├── status
└── agents
    ├── roles
    └── tools
```

With concrete paths:

- `houmao-mgr project agents roles ...`
- `houmao-mgr project agents tools <tool> ...`

This makes the CLI map 1:1 to `.houmao/agents/roles/` and `.houmao/agents/tools/`.

## Problem Statement

The current design mixes two different naming models.

Filesystem model:

```text
project
  -> .houmao
     -> agents
        -> roles
        -> tools
```

CLI model:

```text
project
  -> agent-tools
  -> agent-roles
```

That mismatch causes two problems:

1. The CLI no longer mirrors the actual root object being managed.
2. Future growth becomes awkward because anything else under `.houmao/agents/` would need another synthetic `agent-*` namespace.

The inconsistency is visible in docs and specs:

- `project init` creates `.houmao/agents/roles/` and `.houmao/agents/tools/`
- docs explain the canonical tree as `.houmao/agents/...`
- the current CLI and active OpenSpec change name the command families `agent-tools` and `agent-roles`

## Current Evidence

Relevant code and docs inspected during this discussion:

- `src/houmao/project/overlay.py`
- `src/houmao/srv_ctrl/commands/project.py`
- `tests/unit/srv_ctrl/test_project_commands.py`
- `docs/getting-started/agent-definitions.md`
- `docs/getting-started/quickstart.md`
- `docs/reference/cli/houmao-mgr.md`
- `openspec/specs/houmao-mgr-project-cli/spec.md`
- `openspec/specs/houmao-mgr-project-agent-tools/spec.md`
- `openspec/specs/houmao-srv-ctrl-native-cli/spec.md`
- `openspec/changes/add-project-role-and-tool-management-cli/proposal.md`
- `openspec/changes/add-project-role-and-tool-management-cli/design.md`
- `openspec/changes/add-project-role-and-tool-management-cli/tasks.md`

Important observation:

The active design in `openspec/changes/add-project-role-and-tool-management-cli/design.md` explicitly rejected `project agents roles` and `project agents tools` in favor of `project agent-roles` and `project agent-tools`.

So this is not just a docs drift issue. It is a real design choice that now needs to be reconsidered.

## Proposed Namespace

Recommended shape:

```text
houmao-mgr project
├── init
├── status
└── agents
    ├── roles
    │   ├── list
    │   ├── get
    │   ├── init
    │   ├── scaffold
    │   ├── remove
    │   └── presets
    │       ├── list
    │       ├── get
    │       ├── add
    │       └── remove
    └── tools
        ├── list
        └── <tool>
            ├── get
            ├── setups
            │   ├── list
            │   ├── get
            │   ├── add
            │   └── remove
            └── auth
                ├── list
                ├── add
                ├── get
                ├── set
                └── remove
```

Direct mapping:

- `.houmao/agents/roles/` -> `houmao-mgr project agents roles ...`
- `.houmao/agents/tools/` -> `houmao-mgr project agents tools ...`
- `.houmao/agents/tools/<tool>/auth/` -> `houmao-mgr project agents tools <tool> auth ...`
- `.houmao/agents/tools/<tool>/setups/` -> `houmao-mgr project agents tools <tool> setups ...`

## Why This Is Better

### 1. The command tree mirrors the filesystem tree

This is the main argument.

Operators should be able to translate between CLI and disk layout mechanically:

```text
project agents roles
<-> .houmao/agents/roles

project agents tools
<-> .houmao/agents/tools
```

That is easier to teach, easier to remember, and easier to extend.

### 2. `agents` is meaningful structure, not noise

The prior design treated the extra `agents` segment as unnecessary depth.

In practice it is useful because it names the real managed subtree. The CLI is not just managing "tools" and "roles" in the abstract. It is managing the project-local agent definition tree.

### 3. It leaves room for future subtrees

If Houmao later wants first-class commands for:

- `skills/`
- `compatibility-profiles/`

then the CLI grows naturally:

```text
houmao-mgr project agents skills ...
houmao-mgr project agents compatibility-profiles ...
```

That is cleaner than introducing more `agent-*` siblings.

### 4. It aligns with existing documentation language

The docs already teach `.houmao/agents/` as the canonical local source root. The CLI should speak the same language.

## Compatibility Position

Preferred direction:

- make a clean breaking rename
- do not keep `agent-tools` and `agent-roles` as the documented public surface

Reasoning:

- this repository currently allows breaking CLI cleanup in active development
- `agent-roles` is not implemented yet
- the churn is mostly limited to the recent `agent-tools` surface plus docs and tests

Possible softer landing if needed:

- keep hidden compatibility aliases for one cycle
- keep them undocumented
- remove them once docs and downstream usage have moved

But the design target should still be the `project agents ...` tree.

## What Stays The Same

This discussion does not argue for changing the role and tool semantics themselves.

The existing active change already has a good semantic split:

- `roles` should be scaffold-and-inspect oriented
- `tools` should cover setup bundle inspection and cloning
- `auth` remains tool-specific CRUD under the tool subtree

The recommended change is mostly namespace shape, not capability behavior.

In other words:

- keep the role scaffold idea
- keep preset subcommands
- keep tool `get`
- keep `setups`
- keep `auth`
- move them under `project agents ...`

## Main Tradeoff

There is one real downside:

- `houmao-mgr project agents tools claude auth add ...` is longer than `houmao-mgr project agent-tools claude auth add ...`

This is a valid ergonomic cost.

My view from this discussion is that the clarity gain is worth it because:

- the longer version is structurally obvious
- the current shorter version hides the managed root and creates naming drift
- once the surface expands beyond auth-only workflows, structural clarity matters more than shaving one token

## Proposed OpenSpec Direction

If this discussion is accepted, the active change `add-project-role-and-tool-management-cli` should be revised rather than replaced.

Expected OpenSpec changes:

1. Update the proposal to describe `project agents roles` and `project agents tools`.
2. Rewrite the design decision that currently keeps `project agent-tools` and adds `project agent-roles`.
3. Update tasks to reflect the nested `agents` command group.
4. Update base specs so the supported `project` family includes `agents`, not `agent-tools`.
5. Rename or supersede the tool-specific capability/spec so it reflects `project agents tools`.
6. Update docs and tests to use the new command tree.

## Open Questions For Next Iteration

1. Should `project agents tools list` exist, or should discovery remain implicit through `--help` plus per-tool commands?
2. Should `project agents` itself expose a `status` or `tree` command, or is that unnecessary in v1?
3. Do we want temporary hidden aliases for `project agent-tools` during the rename, or should this be a hard cut immediately?
4. Should we also reserve a future `project agents skills ...` namespace now in the design, even if we do not implement it in this change?

## Working Recommendation

Adopt the following public design:

```text
houmao-mgr project agents roles ...
houmao-mgr project agents tools <tool> ...
```

Treat `agent-tools` and `agent-roles` as rejected naming because they do not reflect the actual `.houmao/agents/` tree cleanly enough.

## Second Thread: `project easy` As A Higher-Level UX View

A second design direction emerged after the namespace discussion:

- the low-level `project agents ...` tree should still mirror the real filesystem
- but ordinary users may need a simpler, intent-oriented view that is not tied directly to the directory structure

That suggests two complementary views:

```text
houmao-mgr project agents ...
  filesystem-oriented authoring and maintenance

houmao-mgr project easy ...
  intent-oriented authoring and launch UX
```

Under this design, `easy` is not a separate runtime system. It is a higher-level compiler onto the normal `.houmao/agents/` tree.

## `easy` User Concepts

The proposed `easy` surface introduces two user-facing concepts:

- `specialist`
- `instance`

The intended relationship is class/instance-like:

- a `specialist` is a reusable blueprint
- an `instance` is one realized or launched agent using that blueprint

The important implementation constraint is that a `specialist` must still compile into the existing role/preset/tool/auth/skill model rather than inventing a second runtime contract.

## `specialist` Input Model

When creating a `specialist`, the user defines:

1. system prompt
2. tool type
3. credential
4. skills

The proposed inputs are:

### 1. System prompt

The user should supply exactly one of:

- `--system-prompt <text>`
- `--system-prompt-file <path-to-md>`

This compiles to:

```text
.houmao/agents/roles/<specialist>/system-prompt.md
```

### 2. Tool type

User-facing tool choices should be short and stable:

- `claude`
- `codex`
- `gemini`

These map onto the existing internal lanes:

- `claude` -> preset tool `claude`, launch provider `claude_code`
- `codex` -> preset tool `codex`, launch provider `codex`
- `gemini` -> preset tool `gemini`, launch provider `gemini_cli`

Note from the discussion:

- Gemini is headless-only currently, so `easy` should reflect that in docs/help and launch behavior

### 3. Credential

The `specialist` flow should let the user provide both a credential name and the credential payload in one place.

Common fields across tools:

- `--credential <name>`
- `--api-key <value>`
- `--base-url <value>`

Tool-specific auth file flags:

- Codex: `--codex-auth-json <path>`
- Claude Code: use a Claude-specific name such as `--claude-state-template-file <path>`
- Gemini: `--gemini-oauth-creds <path>`

This material should compile into the normal auth bundle tree:

```text
.houmao/agents/tools/<tool>/auth/<credential>/
```

The generated preset should then reference that credential by name through `auth: <credential>`.

### 4. Skills

The `specialist` flow should accept repeatable skill imports:

- `--with-skill <path-to-skill-dir>`

Rules proposed in the discussion:

- the source path should point to a skill directory containing `SKILL.md`
- multiple `--with-skill` flags are allowed
- the CLI should copy or sync each selected skill into the project-local `.houmao/agents/skills/` tree
- the generated preset should reference only the skill names, not absolute source paths

This keeps the final runtime contract self-contained inside the project overlay.

## `specialist` Output Model

A created `specialist` should compile into ordinary project-local agent artifacts:

- one role prompt
- one default preset for the chosen tool
- one named auth bundle
- zero or more imported skill directories

Example result for `--name researcher --tool codex --credential work`:

```text
.houmao/agents/
├── roles/
│   └── researcher/
│       ├── system-prompt.md
│       └── presets/
│           └── codex/
│               └── default.yaml
├── tools/
│   └── codex/
│       └── auth/
│           └── work/
└── skills/
    ├── notes/
    └── rg-best-practices/
```

The generated preset remains minimal and standard:

```yaml
skills:
  - notes
  - rg-best-practices
auth: work
```

This is the key design property:

- `project easy` owns the high-level UX
- `.houmao/agents/` remains the only real source contract used by build and launch

## Proposed `project easy` CLI Shape

Recommended public shape:

```text
houmao-mgr project easy
├── specialist
│   ├── create
│   ├── list
│   ├── get
│   ├── update
│   ├── remove
│   └── launch
└── instance
    ├── create
    ├── list
    ├── get
    ├── start
    ├── stop
    └── remove
```

The discussion recommendation was to keep v1 smaller:

```text
houmao-mgr project easy
├── specialist
│   ├── create
│   ├── list
│   ├── get
│   ├── remove
│   └── launch
└── instance
    ├── list
    └── get
```

Rationale:

- the specialist abstraction is the main UX value
- instance creation should not introduce a second persisted contract too early
- the current runtime already has managed-agent manifests and registry state that can back `instance list|get`

## `specialist launch` Semantics

The proposed high-level flow is:

```text
project easy specialist launch
  -> resolve specialist metadata
  -> derive role + tool lane + provider
  -> call the existing native launch path
```

Example:

```bash
houmao-mgr project easy specialist launch \
  --name researcher \
  --instance repo-research-1
```

That should behave like ergonomic sugar for:

```bash
houmao-mgr agents launch \
  --agents researcher \
  --provider codex \
  --agent-name repo-research-1
```

Or, when the tool is Claude:

```bash
houmao-mgr agents launch \
  --agents researcher \
  --provider claude_code \
  --agent-name repo-research-1
```

Important note:

- the provider is derived from the specialist's tool selection rather than typed again by the user at launch time

## `instance` As A UX View, Not Necessarily A New Stored Artifact

The discussion recommendation was to keep `instance` thin in v1.

Meaning:

- `specialist` is a persisted high-level authoring object
- `instance` is initially a user-facing lens over actual launched managed-agent sessions

So:

- `project easy instance list` can show launched agents grouped or annotated by specialist
- `project easy instance get --name <instance>` can show runtime state plus originating specialist

This avoids introducing another configuration layer before it is actually needed.

If later Houmao needs persisted per-instance overrides, that can become a follow-up design.

## Suggested Metadata Layer For `easy`

Because `easy` is a higher-level UX view, it likely needs a small metadata layer that is not runtime-authoritative but is sufficient for reconstruction and updates.

Suggested location:

```text
.houmao/easy/specialists/<name>.toml
```

Suggested purpose:

- remember the user-level specialist object
- map that object to generated `agents/` paths
- support `specialist get` and future `specialist update`

Suggested shape:

```toml
schema_version = 1
name = "researcher"
tool = "codex"
provider = "codex"
role_name = "researcher"
preset_path = "agents/roles/researcher/presets/codex/default.yaml"
auth_name = "work"

[system_prompt]
source_kind = "inline"
managed_path = "agents/roles/researcher/system-prompt.md"

[[skills]]
name = "notes"
managed_path = "agents/skills/notes"

[[skills]]
name = "rg-best-practices"
managed_path = "agents/skills/rg-best-practices"
```

This file should not become a second build input. It exists for the `easy` UX only. The real runtime still consumes the compiled `.houmao/agents/` tree.

## UX Positioning

The resulting model is:

```text
project easy
  simple, opinionated, user-facing workflow

project agents
  direct, filesystem-oriented, power-user workflow
```

That split feels coherent:

- beginners and ordinary operators start with `project easy specialist create`
- advanced users and docs can still refer to the canonical `.houmao/agents/` structure and low-level maintenance commands

## V1 Recommendation For `project easy`

Recommended first slice:

1. `project easy specialist create`
2. `project easy specialist list`
3. `project easy specialist get`
4. `project easy specialist remove`
5. `project easy specialist launch`
6. `project easy instance list`
7. `project easy instance get`

Recommended non-goals for the first slice:

- full inline editing for generated presets
- arbitrary advanced launch/mailbox/extra preset mutation
- persisted instance configuration distinct from managed-agent runtime state
- a second runtime contract outside `.houmao/agents/`

## Open Questions For The `easy` View

1. Should `specialist create` always generate `default.yaml`, or should it optionally allow a named setup from day one?
2. Should `--with-skill` copy skill directories into the overlay, or should it support symlink/project modes as an advanced option later?
3. Should `specialist launch` allow launch-time credential override, or should that stay in the lower-level `agents launch` surface only?
4. Should `easy` metadata live under `.houmao/easy/` or under `.houmao/project-easy/` to make ownership clearer?
5. Should specialist names and role names always be identical in v1, or should role naming remain an internal implementation detail stored in metadata?

## Third Thread: `project mailbox` For Repo-Local Mailbox Roots

Another related design direction is to let `houmao-mgr project` own a repo-local mailbox root explicitly.

The motivation is straightforward:

- today `houmao-mgr mailbox ...` manages an arbitrary or global filesystem mailbox root
- but project workflows increasingly want one mailbox root that belongs to the current repo-local `.houmao/` overlay

That suggests adding:

```text
houmao-mgr project mailbox ...
```

This should be a project-scoped mailbox view, not a replacement for the existing top-level mailbox command family.

## Positioning

Recommended split:

```text
houmao-mgr mailbox ...
  global or arbitrary mailbox-root administration

houmao-mgr project mailbox ...
  mailbox-root administration for the current project overlay
```

This preserves both use cases cleanly:

- one operator may want a shared mailbox root outside any repo
- another operator may want a mailbox root anchored under one repo-local `.houmao/`

The project-aware surface should therefore imply the mailbox root from the discovered project config rather than making the operator repeat `--mailbox-root` everywhere.

## Config Direction

The current project config only records `agent_def_dir`.

The discussion recommendation is to extend `.houmao/houmao-config.toml` with an optional mailbox-root entry:

```toml
schema_version = 1

[paths]
agent_def_dir = "agents"
mailbox_root = "mailbox"
```

Interpretation:

- relative `mailbox_root` values resolve relative to `.houmao/`
- the default project-local mailbox root becomes:

```text
<project-root>/.houmao/mailbox/
```

This keeps mailbox state explicitly relocatable while still letting the project own a local default.

## Proposed `project mailbox` CLI Shape

Recommended public shape:

```text
houmao-mgr project mailbox
├── init
├── status
├── path
├── register
├── unregister
├── repair
└── cleanup
```

Recommended minimal v1 slice:

```text
houmao-mgr project mailbox
├── init
├── status
├── path
├── repair
└── cleanup
```

The narrower v1 rationale:

- bootstrapping and inspecting the repo-local mailbox root is the highest-value project behavior
- direct mailbox-address registration parity can be added later if needed
- managed-agent mailbox binding should remain on `houmao-mgr agents mailbox ...`

## Semantic Split With Existing Mailbox Commands

The discussion recommendation is to keep three distinct ownership layers:

### 1. Root administration

```text
houmao-mgr mailbox ...
```

Use when the operator wants to manage some mailbox root directly, global or otherwise.

### 2. Project-root administration

```text
houmao-mgr project mailbox ...
```

Use when the operator wants to manage the mailbox root associated with the current repo-local `.houmao/` project overlay.

### 3. Managed-agent session binding

```text
houmao-mgr agents mailbox ...
```

Use when the operator wants to bind or unbind one running managed agent to a mailbox root.

This distinction matters because:

- `mailbox` and `project mailbox` operate on mailbox-root state
- `agents mailbox` mutates managed-session mailbox binding state

That session-binding behavior should not be collapsed into the project-root mailbox admin surface.

## Proposed Command Semantics

### `project mailbox init`

Behavior:

1. discover the nearest project overlay
2. resolve the effective project mailbox root from project config
3. if the config has no mailbox-root entry yet, default to `.houmao/mailbox`
4. bootstrap or validate that root using the existing filesystem mailbox bootstrap logic
5. persist the project-local mailbox-root config entry if needed
6. emit structured JSON describing the resolved path and bootstrap status

This command should not require the operator to provide `--mailbox-root` in the common case.

### `project mailbox status`

Behavior:

- report:
  - discovered project root
  - project config path
  - configured project mailbox root
  - mailbox-root health/status summary using the current mailbox status logic

This should be the project-scoped counterpart to `houmao-mgr mailbox status`.

### `project mailbox path`

Behavior:

- print the resolved project mailbox root
- report its authority/source, such as:
  - explicit project config
  - implied project default

This is useful for scripts and for later composition with other commands.

### `project mailbox repair`

Behavior:

- run the existing mailbox-root repair logic against the resolved project mailbox root

### `project mailbox cleanup`

Behavior:

- run the existing mailbox-root cleanup logic against the resolved project mailbox root

### Optional later parity: `register` and `unregister`

If parity is wanted, the project-aware subtree may later expose:

```text
project mailbox register
project mailbox unregister
```

These would behave like the existing root-level mailbox-address registration commands, but with the mailbox root implied by project config.

The discussion recommendation was that this is optional for the first slice.

## Recommended Relationship To `project init`

The recommendation from the discussion is:

- `project init` should continue bootstrapping the project overlay only
- it should not automatically create mailbox state by default
- mailbox state should appear only when the operator opts in through `project mailbox init`

Reasoning:

- mailbox is a distinct subsystem with its own mutable shared state
- many project overlays will not need mailbox at all
- automatic mailbox bootstrap would create extra local state too early and blur subsystem ownership

So the intended workflow becomes:

```bash
houmao-mgr project init
houmao-mgr project mailbox init
```

instead of forcing mailbox creation into the base project bootstrap path.

## Relationship To The Houmao-Owned Directory Model

The current Houmao-owned directory model says mailbox state must remain independently relocatable rather than being implicitly nested under runtime or job roots.

The proposed project-mailbox design is compatible with that rule because:

- the project-local mailbox root is still an explicit configured root
- it is merely defaulted relative to the project overlay
- the mailbox subsystem remains a separate responsibility zone

In other words:

- `project mailbox` does not mean mailbox stops being independent
- it means the current project chooses to own one mailbox root locally

## Future Composition With `project easy`

This project-scoped mailbox root composes naturally with the earlier `project easy` discussion.

Possible future ergonomics:

- `project easy specialist launch --mailbox project`
- `project easy instance get` can show whether the launched instance is bound to the configured project mailbox root

But those should be follow-on conveniences. The base `project mailbox` surface should stand on its own first.

## V1 Recommendation For `project mailbox`

Recommended first slice:

1. add optional `paths.mailbox_root` to project config
2. add `project mailbox init`
3. add `project mailbox status`
4. add `project mailbox path`
5. add `project mailbox repair`
6. add `project mailbox cleanup`

Recommended non-goals for the first slice:

- moving managed-agent mailbox binding off `agents mailbox`
- forcing mailbox creation during `project init`
- changing the default behavior of top-level `houmao-mgr mailbox ...`
- introducing mailbox-specific launch coupling into the project-specialist flow prematurely

## Open Questions For `project mailbox`

1. Should `project mailbox init` persist `mailbox_root = "mailbox"` automatically when the field is absent, or should it allow an implicit runtime default without editing config?
2. Should `project mailbox register|unregister` be included in the first slice, or should project scope stop at mailbox-root administration?
3. Should later project-aware agent mailbox binding use implicit project mailbox-root resolution when `--mailbox-root` is omitted, or should that remain explicit on `agents mailbox`?
4. Should the project mailbox root default to `.houmao/mailbox/` or to another path such as `.houmao/shared-mailbox/` to make the subtree's purpose more obvious?

## Revision: `project mailbox` Should Reuse The Same Mailbox Operations As `houmao-mgr mailbox`

The mailbox discussion was later clarified further.

The intended relationship is:

- `houmao-mgr mailbox ...` and `houmao-mgr project mailbox ...` expose the same mailbox operations
- `project mailbox` is only a different mailbox-root resolution mode
- `project mailbox` is effectively a project-scoped wrapper around:

```text
houmao-mgr mailbox ... --mailbox-root <project-root>/.houmao/mailbox
```

This means the previous framing of `project mailbox` as a distinct mailbox-admin surface was too broad.

The corrected design is:

- one mailbox operations model
- two entry paths with different root resolution

## Recommendation: Keep `houmao-mgr mailbox`

The discussion conclusion was:

- do not remove `houmao-mgr mailbox`

Reasoning:

- `houmao-mgr mailbox` is still the canonical generic mailbox-root command family
- it remains useful for arbitrary mailbox roots outside any project overlay
- removing it would force all mailbox workflows into a project-shaped environment unnecessarily
- existing docs, tests, and operator mental models already have a clear place for generic mailbox administration

So the preferred model becomes:

```text
houmao-mgr mailbox ...
  generic mailbox-root operations

houmao-mgr project mailbox ...
  the same operations, but against the discovered project mailbox root
```

## Updated Positioning

Recommended split:

```text
houmao-mgr mailbox ...
  canonical generic mailbox-root CLI

houmao-mgr project mailbox ...
  project-scoped convenience wrapper over the same mailbox-root CLI

houmao-mgr agents mailbox ...
  managed-agent session mailbox binding
```

This keeps the ownership boundaries clean:

- `mailbox` and `project mailbox` both operate on a mailbox root
- `agents mailbox` operates on a running managed-agent session

## Revised `project mailbox` Semantics

Under the clarified model, `project mailbox` should not define its own separate capability set.

Instead, it should expose the same verbs already available on `houmao-mgr mailbox`, but with mailbox root implied from the current project overlay.

Conceptually:

```text
houmao-mgr project mailbox <verb> [args...]
==>
houmao-mgr mailbox <verb> --mailbox-root <project-root>/.houmao/mailbox [args...]
```

That suggests:

```text
houmao-mgr project mailbox
├── init
├── status
├── register
├── unregister
├── repair
└── cleanup
```

And, if later added to the base mailbox CLI, project-scoped wrappers for mail-reading commands would follow the same rule.

The important point is not the exact current verb inventory. The important point is:

- `project mailbox` should not drift into a different mailbox command family
- it should stay a project-root lens over the canonical mailbox subsystem

## Root Resolution Model

Recommended project behavior:

- discover the nearest project overlay
- resolve the project mailbox root as:

```text
<project-root>/.houmao/mailbox
```

- apply the normal mailbox operation against that resolved root

This can later grow optional config support if needed, but the current clarified use case does not require a separate mailbox-root configuration story.

## Implementation Suggestion

The implementation should avoid duplicating mailbox logic.

Preferred shape:

- keep the existing mailbox command handlers authoritative
- factor the mailbox operations behind reusable internal helpers
- have `project mailbox` call those same helpers with a project-resolved mailbox root

That gives:

- one set of mailbox semantics
- one set of validation and payload shapes
- two root-resolution entrypoints

## Documentation Suggestion

Docs should present:

- `houmao-mgr mailbox ...` as the generic/root-explicit workflow
- `houmao-mgr project mailbox ...` as the preferred repo-local shorthand

In other words:

```text
Use `houmao-mgr mailbox ...` when you want to manage any mailbox root explicitly.
Use `houmao-mgr project mailbox ...` when you want the current repo's `.houmao/mailbox` root automatically.
```

## Updated Recommendation

Final recommendation from this discussion thread:

1. keep `houmao-mgr mailbox`
2. add `houmao-mgr project mailbox`
3. make `project mailbox` a thin wrapper over the same mailbox operations
4. keep `houmao-mgr agents mailbox` separate because it targets session binding rather than mailbox-root administration

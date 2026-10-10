# swe-critic Agent Definition Workspace

This directory is a complete authoring workspace for `swe-critic`, a read-only software design critic that evaluates extensibility, ease of understanding, responsibility division, and coherence versus coupling.

This README is generated orientation for people receiving the workspace. It is not source intent, derived authority, approval evidence, or immutable revision content. Editing it does not change the agent definition.

## Lifecycle State

The source intent has been derived and approved. Revision `1.0.0` is materialized under `agent-definition/` and validates successfully.

- Definition id: `swe-critic`
- Revision id: `1.0.0`
- Revision digest: `sha256:11ee9142bd928ff75769b2c50ec47d9274a5c387a38a0a183d21598d0f9bb5b1`
- Instance-contract digest: `sha256:b3cf3a6f6eac7cce388e1051425b5ee11bedb7098112dac18f27091f894eb30b`

## Directory Tree

```text
.
├── README.md
├── agent-definition/
│   ├── assets/
│   │   ├── memo/houmao-memo.md
│   │   ├── prompts/system.md
│   │   └── skills/swe-critic-review/SKILL.md
│   ├── definition.toml
│   ├── deploy-contract.toml
│   ├── instance-contract.toml
│   └── provenance/materialization.json
├── intent/
│   ├── derived/
│   │   ├── approval.toml
│   │   ├── interpretation.md
│   │   ├── materialization.toml
│   │   ├── materials/
│   │   │   ├── memo/houmao-memo.md
│   │   │   ├── prompts/system.md
│   │   │   └── skills/swe-critic-review/SKILL.md
│   │   └── validation.json
│   └── src/
│       ├── agent-def-overview.md
│       ├── memo/houmao-memo.md
│       ├── prompts/system.md
│       └── skills/swe-critic-review/SKILL.md
└── operator/
    ├── interpretation.md
    └── materialization.toml
```

## File Inventory

| File | Purpose |
| --- | --- |
| [README.md](README.md) | Generated, non-authoritative workspace orientation. |
| [agent-definition/assets/memo/houmao-memo.md](agent-definition/assets/memo/houmao-memo.md) | Immutable memo seed bundled in the revision. |
| [agent-definition/assets/prompts/system.md](agent-definition/assets/prompts/system.md) | Immutable system prompt bundled in the revision. |
| [agent-definition/assets/skills/swe-critic-review/SKILL.md](agent-definition/assets/skills/swe-critic-review/SKILL.md) | Complete review skill bundled in the revision. |
| [agent-definition/definition.toml](agent-definition/definition.toml) | Definition identity, purpose, asset references, and revision digest. |
| [agent-definition/deploy-contract.toml](agent-definition/deploy-contract.toml) | Typed deploy-time input and binding contract. |
| [agent-definition/instance-contract.toml](agent-definition/instance-contract.toml) | Runtime-variable, mindset, and private-workspace contract. |
| [agent-definition/provenance/materialization.json](agent-definition/provenance/materialization.json) | Source and derived digests recorded at materialization. |
| [intent/derived/approval.toml](intent/derived/approval.toml) | Approval bound to the exact source and derived digests. |
| [intent/derived/interpretation.md](intent/derived/interpretation.md) | Current operator interpretation of the source intent. |
| [intent/derived/materialization.toml](intent/derived/materialization.toml) | Normalized machine authority for materialization. |
| [intent/derived/materials/memo/houmao-memo.md](intent/derived/materials/memo/houmao-memo.md) | Confined derived copy of the memo seed. |
| [intent/derived/materials/prompts/system.md](intent/derived/materials/prompts/system.md) | Confined derived copy of the system prompt. |
| [intent/derived/materials/skills/swe-critic-review/SKILL.md](intent/derived/materials/skills/swe-critic-review/SKILL.md) | Confined complete copy of the authored review skill. |
| [intent/derived/validation.json](intent/derived/validation.json) | Derivation findings, source inventory, and freshness digests. |
| [intent/src/agent-def-overview.md](intent/src/agent-def-overview.md) | User-owned entrypoint for all agent requirements and linked source material. |
| [intent/src/memo/houmao-memo.md](intent/src/memo/houmao-memo.md) | User-owned memo seed source. |
| [intent/src/prompts/system.md](intent/src/prompts/system.md) | User-owned system prompt source. |
| [intent/src/skills/swe-critic-review/SKILL.md](intent/src/skills/swe-critic-review/SKILL.md) | User-owned complete review skill source. |
| [operator/interpretation.md](operator/interpretation.md) | Editable operator working draft supplied to the derive command. |
| [operator/materialization.toml](operator/materialization.toml) | Editable operator materialization draft supplied to the derive command. |

## Ownership and Authority

`intent/src/` is the user-owned source of requirements. Change requirements there, starting with `intent/src/agent-def-overview.md`; do not use this README as an intent input.

`operator/` holds editable working drafts. `intent/derived/` holds the current operator interpretation, normalized materialization authority, copied materials, validation evidence, and digest-bound approval. A new derive operation replaces the current derived tree.

`agent-definition/` is the validated immutable revision. Do not edit it in place. Create a new revision through the full derive, approve, preview, materialize, and validate lifecycle.

## Continue, Validate, or Deploy

Run these commands from this workspace root. After changing source intent, update the operator drafts, derive again with the complete skill source, approve the fresh digests, preview, and materialize a new revision id.

Validate the bundled revision:

```bash
houmao-mgr project agent-definitions validate ./agent-definition
```

Start a deployment plan with explicit project-specific names, tool, existing credential, workdir, and `task_objective`:

```bash
houmao-mgr project agent-definitions plan ./agent-definition \
  --deployment-name <deployment-name> \
  --specialist-name <specialist-name> \
  --profile-name <profile-name> \
  --tool <tool> \
  --credential <existing-credential-name> \
  --workdir <project-relative-workdir> \
  --set task_objective="<review objective>"
```

Planning does not launch an agent. Review and apply the plan separately, then use the returned launch handoff.

## Distribution

Share this full workspace when another author needs the original intent, operator interpretation, approval provenance, and guidance for creating another revision. Share only `agent-definition/` when a user needs the portable validated revision for deployment.

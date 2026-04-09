# `.houmao/` Project Layout

Use this reference when the question is how project-local Houmao files are organized.

## Core Layout

```text
.houmao/
├── .gitignore
├── houmao-config.toml
├── catalog.sqlite
├── content/
│   ├── prompts/
│   ├── auth/
│   ├── skills/
│   └── setups/
├── agents/                 # compatibility projection, materialized on demand
├── runtime/
├── jobs/
├── mailbox/
└── easy/
```

## Canonical Store vs Compatibility Projection

- `catalog.sqlite` is the canonical semantic store for project-local specialists, roles, recipes, launch profiles, and managed content references.
- `content/` stores the file-backed payloads those semantic objects refer to.
- `content/auth/<tool>/<opaque-bundle-ref>/` stores auth payloads by opaque bundle ref rather than by the operator-facing auth display name.
- `agents/` is the compatibility projection materialized from the catalog and managed content when file-tree consumers need it.
- `agents/tools/<tool>/auth/<opaque-bundle-ref>/` is likewise a derived projection keyed by opaque refs; user-facing auth names live in the catalog and CLI output instead of these directory basenames.

## Bootstrap Defaults

- `project init` creates `houmao-config.toml`, `.gitignore`, `catalog.sqlite`, and the managed `content/` roots.
- `project init` does not create `.houmao/mailbox/`, `.houmao/easy/`, or the compatibility projection tree unconditionally.
- `project init --with-compatibility-profiles` additionally pre-creates `.houmao/agents/compatibility-profiles/`.

## Interpretation

- Treat `.houmao/agents/` as the file-tree view current builders and runtime consume, not as the only canonical source of truth.
- Treat `runtime/`, `jobs/`, `mailbox/`, and `easy/` as overlay-local maintained state roots that appear when their workflows are enabled.

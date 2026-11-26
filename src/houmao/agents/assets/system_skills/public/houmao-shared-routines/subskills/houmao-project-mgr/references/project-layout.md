# `.houmao/` Project Layout

Use this reference when explaining how project-local Houmao files are organized and maintained.

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

## Canonical Store, Project Skills, and Migration

- **`catalog.sqlite` and `content/`**: `catalog.sqlite` is the canonical semantic store for specialists, project profiles, credentials, `project skills`, deployments, and managed content references; `content/` holds the file-backed payloads.
- **Project-local skills (`content/skills/`)**: `houmao-mgr project skills {add|get|list|remove|set}` registers, inspects, updates, and removes canonical project skills under `.houmao/content/skills/` so specialists (`--skill`, `--with-skill`) and profiles (`--add-registered-skill`) can bind them cleanly. Static Houmao system-skill packs (`admin`, `agent`) are separate and managed via `houmao-mgr system-skills`.
- **Opaque auth refs (`content/auth/<tool>/<opaque-bundle-ref>/`)**: auth payloads use opaque bundle refs; operator-facing credential names live in `catalog.sqlite` and `project credentials` output rather than directory basenames.
- **Compatibility projection (`agents/`)**: materialized on demand from `catalog.sqlite` and `content/` for builders and runtime consumers; never treat `.houmao/agents/` as a hand-edited source of truth.
- **Structure migration (`project migrate`)**: `houmao-mgr project migrate` previews supported `.houmao/` schema/layout upgrades read-only, while `houmao-mgr project migrate --apply` applies the detected migration plan in place.

## Bootstrap Defaults

- `project init` creates `houmao-config.toml`, `.gitignore`, `catalog.sqlite`, and managed `content/` roots.
- `runtime/`, `jobs/`, `mailbox/`, `easy/`, and `agents/` appear only when their corresponding workflows run.

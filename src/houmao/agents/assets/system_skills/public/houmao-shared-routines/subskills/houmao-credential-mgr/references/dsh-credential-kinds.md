---
metadata:
  skill_invocation_notation: >
    Top-level skill entrypoints use SKILL.md. Parent-scoped subskill entrypoints use
    SKILL-MAIN.md and are loaded explicitly through their parent; nested SKILL.md is
    accepted only as legacy input when SKILL-MAIN.md is absent.
    Skill and subskill entrypoints use bare object paths: `X` invokes skill X and
    `X->Y->Z` invokes subskill Z. Subcommands use parenthesized components:
    `X->cmd()` invokes a direct subcommand, `X->Y->cmd()` invokes a subcommand of
    subskill Y, and `X->parent()->child()` invokes child subcommand child exposed
    by parent subcommand parent. Intermediate subcommands act as object generators.
    Forms such as `X()` and `X->Y()` are invalid for skill or subskill entrypoints.
---

# DSH (DeepSeek Harness) Credential Kinds

Use this reference when `--tool dsh` is selected for `project credentials dsh add|set` or `internals native-agent credentials dsh add|set --native-agent-root <path>`.

## Required Adapter and Explicit API Fields

DeepSeek Harness credentials store explicit API endpoint and key configuration without discovering or importing native login state:

| Flag | Applies To | Purpose |
| --- | --- | --- |
| `--name <name>` | `add`, `set` | Operator-facing credential name (required). |
| `--adapter [deepseek\|pi-ai]` | `add`, `set` | Selected DSH protocol adapter (required). |
| `--api-key <secret>` | `add`, `set` | Explicit API key value for the selected adapter (opaque secret; redacted on `get`). |
| `--base-url <url>` | `add`, `set` | Explicit protocol endpoint override for the selected adapter. |
| `--api-key-env <ENV_NAME>` | `add`, `set` | Bundle environment variable name for the API key when binding by env name. |
| `--base-url-env <ENV_NAME>` | `add`, `set` | Bundle environment variable name for the endpoint URL. |
| `--clear-api-key` | `set` | Clear the stored API key on an existing DSH credential. |
| `--clear-base-url` | `set` | Clear the stored endpoint URL on an existing DSH credential. |

## Command Shapes

```bash
<chosen houmao-mgr launcher> project credentials dsh add --name <credential> --adapter <deepseek|pi-ai> [--api-key <key>] [--base-url <url>] [--api-key-env <env>] [--base-url-env <env>]
<chosen houmao-mgr launcher> project credentials dsh set --name <credential> --adapter <deepseek|pi-ai> [--api-key <key> | --clear-api-key] [--base-url <url> | --clear-base-url] [--api-key-env <env>] [--base-url-env <env>]
<chosen houmao-mgr launcher> internals native-agent credentials dsh add --native-agent-root <dir> --name <credential> --adapter <deepseek|pi-ai> [...]
<chosen houmao-mgr launcher> internals native-agent credentials dsh set --native-agent-root <dir> --name <credential> --adapter <deepseek|pi-ai> [...]
```

## Login and Discovery Notes

- DSH has no interactive `credentials dsh login` helper; never invent `houmao-mgr project credentials dsh login` or `houmao-mgr internals native-agent credentials dsh login`.
- `credentials dsh add` and `set` never scan ambient environment variables or home directories automatically. Specialist-creation discovery defaults belong to `houmao-shared-routines->houmao-agent-definition`.

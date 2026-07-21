---
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

# Codex Credential Kinds

Use this reference when `--tool codex` and the agent needs to present credential-kind options to the user during `project credentials codex add` or `internals native-agent credentials codex add --native-agent-root <path>`.

## Kinds

### 1. API Key

- Looks like: a string value representing an OpenAI API key (typically starts with `sk-`)
- Maps to: `--api-key`
- Choose this when: you have an OpenAI API key or a compatible provider key
- Security: opaque secret; treat as non-recoverable once stored

Optional modifiers when using this kind:

- `--base-url` to override the default OpenAI endpoint
- `--org-id` to pin an OpenAI organization ID

### 2. Cached Login State (auth.json)

- Looks like: a file path to an `auth.json` file from a previous `codex` login
- Maps to: `--auth-json`
- Choose this when: you have an existing Codex `auth.json` file (for example from `~/.codex/auth.json`) containing cached login state
- Security: the file is treated as opaque cached login state

Optional modifiers when using this kind:

- `--base-url` to override the default OpenAI endpoint
- `--org-id` to pin an OpenAI organization ID

## Discovery Note

The `project credentials codex add` and `internals native-agent credentials codex add --native-agent-root <path>` commands do not run discovery-mode credential creation (auto credentials, env lookup, or directory scan). If you want discovery-mode credential import during creation, use `project specialist create` through `houmao-shared-routines->houmao-agent-definition` instead.

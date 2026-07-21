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

# Skill Developer Design Notes

These files are developer reference material for maintainers of `<public-entrypoint>->houmao-shared-routines->agent-loop-pro`.

They are not part of skill execution. Do not route user requests through this directory, do not install these files as generated role skills, and do not treat them as operator-facing workflow pages. Runtime behavior belongs in `agents/openai.yaml`, the top-level `SKILL.md` router, the routed operation pages under `subskills/`, and the runtime reference pages under `references/`.

## Runtime Reference Boundary

- `SKILL.md` should stay short: activation, required root, operation list, routing, and global constraints.
- `references/` contains shared runtime guidance that invoking agents read from routed operation pages.
- `dev/design/` contains maintainer rationale and extension advice only.
- If a detail is needed during normal skill execution, put it in `references/` or the relevant operation page, then keep `dev/design/` as the explanation of why that rule exists.

## Clarification Boundary

- `clarify-intent` resolves ambiguity in editable loop intent and writes intent ADRs plus `intention/` Markdown.
- `clarify-execplan` resolves ambiguity in generated loop implementation and writes execplan ADRs plus affected generated artifacts or stale-artifact notes.
- Both clarification flows should use the shared clarification protocol and the mail runtime model before asking questions.
- Do not let execplan clarification silently invent missing user intent; send that gap back to `clarify-intent`.

## Files

- `intent.md`: design intent, boundaries, and source-of-truth rules.
- `execplan-contract.md`: intended shape, execution-stage boundaries, and completeness expectations for generated execplans.
- `reference-execplan-patterns.md`: generic execplan patterns extracted from a mature generated reference package.
- `extension-guide.md`: guidance for revising or extending the packaged skill without blurring authoring, generation, and execution responsibilities.

## Maintenance Rule

When behavior changes, update the execution-facing skill files first, then update these notes to explain why the behavior exists and what future maintainers should preserve.

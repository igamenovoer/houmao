# Remove Memory Pages, Prune Live Memo Entries, or Clear Memo Seeds

## Workflow

1. **Identify the removal target** (live `pages/` file, specific entry inside live `houmao-memo.md`, or stored birth-time memo seed on a profile/launch dossier) and confirm missing required selectors before mutating.
2. **Delete a contained live page** via `houmao-mgr agents self|single ... memory delete --path <rel-path>` (strictly relative to `pages/`).
3. **Remove specific text from live `houmao-memo.md`**: read the current memo with `memory memo show`, delete only the targeted entry while preserving unrelated lines, write the updated text via `memory memo set`, check the compact receipt (`success`, `action`, `memo_file`), and run `memory memo show` if final content verification is needed.
4. **Clear a birth-time memo seed** on a reusable profile via `houmao-mgr project profile set --name <name> --clear-memo-seed` or `houmao-mgr internals native-agent launch-dossiers set --native-agent-root <dir> --name <name> --clear-memo-seed` (use `--memo-seed-text ''` instead if the user wants an explicit empty future `houmao-memo.md`).

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from [../SKILL-MAIN.md](../SKILL-MAIN.md) and the user request, then execute the plan.

## Guardrails

- DO NOT pass `--clear-memo-seed` alongside any `--memo-seed-*` source flag, or hand-edit launch-profile YAML files.
- DO NOT use `..` or absolute paths with `memory delete --path`, or strip unmentioned memo links/sections without reading `memory memo show` first.

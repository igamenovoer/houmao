# Write or Append Live Memory or Profile Memo Seeds

## Workflow

1. **Read the current target before editing** via [read.md](read.md) (`memory memo show`, `memory read --path <rel-path>`, or profile/dossier `get`); if `project profile` vs `launch-dossiers` is ambiguous on a birth-time request, ask before mutating.
2. **Apply live `houmao-memo.md` updates with the smallest meaningful change** (keeping `<memo_cue>` content brief: current facts, standing rules, and `[notes](pages/...)` links):
   - Simple addition: `houmao-mgr agents self|single ... memory memo append --content <text>` (or `--content-file <file>`)
   - Rewrite preserving unrelated entries: `houmao-mgr agents self|single ... memory memo set --content <text>` (or `--content-file <file>`)
3. **Verify the compact write receipt**: confirm `success`, `action`, and `memo_file` from the receipt, and run `memory memo show` in the same scope whenever you need to inspect or quote the resulting contents.
4. **Write or append contained `pages/` notes** via `houmao-mgr agents self|single ... memory write|append --path <rel-path> --content <text>` (using `memory resolve --path <rel-path>` if exact link resolution is needed).
5. **Configure birth-time memo seeds** (for reusable profiles only, never `internals config-drafts generate` and never using prompt overlays as a substitute) via `houmao-mgr project profile create|set` or `houmao-mgr internals native-agent launch-dossiers add|set` with **one** seed source:
   - `--memo-seed-text <text>` (replaces future `houmao-memo.md` only; `''` sets an intentional empty memo seed)
   - `--memo-seed-file <path>` (replaces future `houmao-memo.md` only)
   - `--memo-seed-dir <path>` (memo-shaped directory touching `houmao-memo.md` and/or `pages/` only where present)

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from [../SKILL-MAIN.md](../SKILL-MAIN.md) and the user request, then execute the plan.

## Guardrails

- DO NOT combine `--clear-memo-seed` with `--memo-seed-text`, `--memo-seed-file`, or `--memo-seed-dir`, or pass memo seeds to `internals config-drafts generate`.
- DO NOT write outside `pages/`, auto-maintain page indexes unasked, or bloat `houmao-memo.md` with transient turn logs.

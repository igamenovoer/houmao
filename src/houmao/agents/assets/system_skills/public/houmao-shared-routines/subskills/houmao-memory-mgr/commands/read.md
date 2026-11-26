# Read Live Memory or Profile Memo Seeds

## Workflow

1. **Confirm the target kind and scope**: live managed-agent memory (`agents self` in verified `agent` posture, or `agents single --agent-id|--agent-name` for admin/peer) vs birth-time profile (`project profile` or `internals native-agent launch-dossiers`).
2. **Resolve live paths when needed**: inside a managed session check `HOUMAO_AGENT_MEMO_FILE`, `HOUMAO_AGENT_PAGES_DIR`, and `HOUMAO_AGENT_MEMORY_DIR` first, or run `houmao-mgr agents self memory path` (`status`); for an explicit target run `houmao-mgr agents single --agent-id <id> memory path`.
3. **Read the requested surface**:
   - Fixed live memo: `houmao-mgr agents self|single ... memory memo show`
   - Contained `pages/` tree or path: `houmao-mgr agents self|single ... memory tree`, `memory resolve --path <rel-path>`, or `memory read --path <rel-path>`
   - Birth-time memo seed: `houmao-mgr project profile get --name <name>` or `houmao-mgr internals native-agent launch-dossiers get --native-agent-root <dir> --name <name>`
4. **Apply `<memo_cue>` discipline** in managed turns: follow standing facts and open linked `pages/` notes directly without noisy meta-commentary unless the caller asked to inspect the memo.

If the request does not map cleanly to these steps, use the native planning tool to build a bounded read-only plan from [../SKILL-MAIN.md](../SKILL-MAIN.md) and the user request, then execute the plan.

## Guardrails

- DO NOT pass absolute paths or `..` to `--path`; keep page reads relative to `pages/`.
- DO NOT mutate memo or profile state during a read request.

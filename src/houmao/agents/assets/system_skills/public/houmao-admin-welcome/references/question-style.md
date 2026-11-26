# Question Style

Use this reference when `houmao-admin-welcome` asks the operator for decisions during a guided tour.

## Core Rules

1. Define the Houmao concept in one plain sentence and state why the choice matters before asking.
2. Separate `Required` inputs from `Optional` modifiers, defaults, or skip-for-now paths on Houmao setup/lifecycle questions (do not force `Required`/`Optional` onto open-ended user domain goals).
3. Provide 1 to 3 concrete examples and a safe first-time default or skip option whenever a branch is optional.

## Prompt Patterns by Stage

| Decision | Plain-Language Context | Required vs Optional | Safe Default / Boundary Note |
| --- | --- | --- | --- |
| Specialist & tool | Reusable template pairing role prompt, adapter (`claude`, `codex`, `dsh`, `kimi`), and credential. | `Required`: specialist name, tool, credential name. `Optional`: run mode (`headless`, `service`, `tui`, `web`), project profile (`skip` on first run). | Suggest a clear role slug such as `researcher` or `reviewer`; skip optional profile wrapper until defaults repeat. |
| Project mailbox | Shared `offline` root under `.houmao/mailbox` or late Stalwart `online` JMAP binding on an existing agent. | `Required` (if enabled): root-only vs manual account (`<name>@houmao.localhost`) vs Stalwart online attach. `Optional`: skip for now. | Initialize offline root only; `HOUMAO-*` local parts under `houmao.localhost` are reserved for system principals, and easy launch can own `<agent-name>@houmao.localhost` automatically. |
| Live follow-up | Next action on a running agent (`headless`, `service`, `tui`, or `web`). | `Required`: next operation. `Optional`: target ID/name when unambiguous, skip follow-up. | Offer `agent-inspect` (state/usage), attributed `request` or direct `prompt`, `open-browser` (Kimi Web), mail/`mail-notifier`, `houmao-cccc`, or `memory-mgr`. |
| Lifecycle action | `stop` ends live run; `relaunch` restarts preserving identity/mode; `cleanup` deletes stopped artifacts. | `Required`: action (`stop`, `relaunch`, `cleanup`) + explicit agent ID/name. `Optional`: list agents first, cleanup scope (`session`, `logs`). | Never run `cleanup` on a live session; offer `agent-inspect` / `list` first if target IDs are unknown. |

## Compact Template

```text
<Question>

<One-sentence concept explanation and why it matters.>

Required:
- <field>

Optional:
- <modifier or "skip this branch for now" or "none for this step">

Examples: `<example-1>`, `<example-2>`
Recommended default: <default>
```

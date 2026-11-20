# Design

## Context

The manager registers its top-level Click groups in [`commands/main.py`](../../../src/houmao/srv_ctrl/commands/main.py) and resolves print styles through [`commands/output.py`](../../../src/houmao/srv_ctrl/commands/output.py). The distribution includes `src/houmao` and excludes the repository docs tree. The gateway login page already uses `importlib.resources` to read files shipped with the Python package. [Build configuration](../../../pyproject.toml) · [Packaged resource loader](../../../src/houmao/gateway/_web_login.py)

## Goals / Non-Goals

The manual should give a CLI-only agent enough context to choose an operation, confirm its target, and recognize success or uncertainty. It introduces workflows through a read-only command. The existing operations own execution and authorization. Generated loop plans and skill orchestration keep their own documentation.

## Decisions

### Register Real Commands and Load Packaged Documents

Register `manual` as a root group in `commands/main.py` and keep its implementation in `commands/manual.py`. Use Click groups for the five catalogs and leaf commands for their pages. Bare manual and catalog groups print their indexes. Click supplies normal help, command discovery, and usage errors at each level. Add a short `houmao-mgr manual` pointer to root help alongside the detailed docs link.

Keep the catalog and page registrations in Python. Store all manual prose under `src/houmao/srv_ctrl/assets/manual/`. Use one root `index.md`, one `<catalog>/index.md` per catalog, and one `<catalog>/<page>.md` per leaf. Read only the selected UTF-8 resource through `importlib.resources`. A resource path comes from registered command components. Report missing or unreadable files as CLI errors that identify the affected manual command.

Use the shared output context. Plain mode prints the Markdown with its paragraphs and command examples intact. Fancy mode can render the same content through the existing Rich console. JSON uses `path` for the command components and `content` for the Markdown. An editor should be able to revise a title, description, example, or explanation by changing a Markdown file alone.

### Organize Pages Around User Requests

The root index maps common requests to entry pages. Each catalog index lists its pages with a short description of when to read each one. Use the supported manager command families in examples and point readers to leaf `--help` for syntax. A page should fit roughly one terminal screen and give a decision, a short workflow, and a check for the result. Compose longer journeys through neighboring pages.

| Catalog | Page | Guidance |
| --- | --- | --- |
| `start` | `first-agent` | Inspect the requested project. Select a named credential and reuse or create a specialist. Save a profile for repeat launches. Distinguish preparing the worker from launching it. Keep the returned ID and check its state. |
| | `existing-project` | Discover the overlay, specialists, profiles, and known workers. Resume from the nearest useful stage. |
| | `targets` | Use an explicit stable agent ID for operator work. Verify `agents self identity` for managed-self work. Identify external communication references and saved owner routes. |
| `prepare` | `credentials` | Find a named project credential, then use supported import or login when needed. Keep credential values out of reports. |
| | `definitions` | Choose a specialist, launch profile, or reusable immutable definition. Explain role and skill ownership and the deployment-to-launch handoff. |
| | `launch` | Select the workdir, native mode, prompt policy, and execution owner. Explain birth-time precedence, unattended defaults for omitted supported permission settings, and reserved native inputs. |
| `operate` | `inspect` | Start with scoped state and choose mode-appropriate evidence. Distinguish a known agent, live process, readiness, and progress. |
| | `turns` | Choose scoped prompting, explicit ready-only gateway admission, or tracked headless turns. Distinguish acceptance, handoff, and completion. Inspect uncertain work before retrying. |
| | `lifecycle` | Choose adoption, interruption, refresh, stop, relaunch, or fresh launch by intended effect. Explain the saved mode, provider conversation selection, and targeted cleanup. |
| | `memory` | Choose live memo or pages for an agent, a profile memo seed for future launches, or a workdir for deliverables. |
| `communicate` | `mail` | Choose direct prompting or durable mail. Explain operator post, managed send and reply, channel selection, message references, and delivery evidence. |
| | `mailboxes` | Distinguish store initialization, launch-owned registration, and late binding. Verify the selected channel's binding before sending. |
| | `gateway` | Check live attachment and select gateway operations. Explain owner-local Web entry and keep entry links private. |
| | `wakeups` | Distinguish mail, notifier wakeups, and scheduled reminders. Retain the supplied gateway and mailbox binding for a bounded notifier round. Reply before archiving processed mail when a reply is required. |
| `coordinate` | `team` | Give each worker a role, workdir, expected artifact, and acceptance rule. Verify a builder's artifact before a reviewer receives the exact revision or patch. |
| | `workspaces` | Choose shared or isolated Git workdirs. Resolve definition-owned private workspace locations through the supported instance-state commands. |
| | `loops` | Identify recurring work that needs durable state, an explicit start, and recovery. Explain Lite and Pro at a decision level and point to generated loop controls and the Loop Authoring Guide. |

Use the [welcome guided paths](../../../src/houmao/agents/assets/system_skills/public/houmao-admin-welcome/references/guided-paths.md) and the [admin](../../../src/houmao/agents/assets/system_skills/public/houmao-admin-entrypoint/SKILL.md) and [managed-agent](../../../src/houmao/agents/assets/system_skills/public/houmao-agent-entrypoint/SKILL.md) entrypoints as the intent inventory. Verify command paths against the current CLI tree and maintained references when authoring examples.

## Risks / Trade-Offs

- Index or example drift. Check that every registered page has a document, every index lists the exact children for that level, and representative example paths resolve in the CLI.
- Editable-checkout success can conceal omitted release files. Inspect wheel and sdist inventories and run the installed wheel outside the repository with an isolated home.
- Workflow prose can age as runtime behavior changes. Refer to command help for invocation details and keep examples focused on decisions and verification.

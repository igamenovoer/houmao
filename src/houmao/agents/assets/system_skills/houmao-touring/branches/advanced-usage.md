# Advanced Usage Branch

Use this branch when a guided-tour user wants a flat enumeration of the broader advanced Houmao feature surface. The branch lists the advanced entry points as brief entries; each entry names the owning skill the user can invoke or select to go deeper.

## Listing Style

- Present the entries as a flat list of brief entries (roughly one to two sentences each).
- Do not mark any entry as recommended, preferred, primary, or default.
- Do not order the entries to imply a priority ranking. The ordering below is a reading order for the tour, not a ranking.
- Do not restate composed topology, rendered control graphs, run charters, routing packets, mailbox result protocol, reminder protocol, memory file layouts, or credential lifecycle details inline; keep those on the selected owning skill.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill only for state inspection the tour already needs; do not invent a new command surface here.
2. Present the advanced entries as a flat brief list using the entries below.
3. When the user picks one entry, tell the agent to invoke or select the owning skill named in that entry, and stop touring-level elaboration on that topic so the selected skill can own the detailed workflow.
4. When the user is still browsing, keep the entries concise and do not collapse them into a single "advanced" surface.

## Advanced Entries

- **Stable pairwise loop** — use `houmao-agent-loop-pairwise` to author a pairwise loop plan and operate an accepted master-owned run through `plan`, `start`, `status`, and `stop`.
- **Enriched pairwise loop** — use `houmao-agent-loop-pairwise-v2` to author an enriched pairwise loop plan and operate a run through `plan`, `initialize`, `start`, `peek`, `ping`, `pause`, `resume`, `recover_and_continue`, `stop`, and `hard-kill` for extended runtime control and routing-packet prestart.
- **Workspace-aware pairwise loop** — use `houmao-agent-loop-pairwise-v3` to extend the enriched pairwise workflow with an authored `standard` or `custom` workspace contract, including task-scoped standard in-repo posture when needed.
- **Generic loop graph** — use `houmao-agent-loop-generic` for mixed pairwise and relay component graphs where a user-controlled agent needs to decompose a multi-agent communication graph and operate the accepted root-owned run through `start`, `status`, and `stop`.
- **Advanced usage patterns** — use `houmao-adv-usage-pattern` for multi-step workflow compositions built from existing Houmao skills, including self-notification, pairwise edge loops, and forward relay loops, plus the elemental immediate driver-worker edge protocol that underlies loop components.
- **Managed-agent memory** — use `houmao-memory-mgr` to read or write a managed agent's `houmao-memo.md` free-form memo file and the managed-agent pages memory.
- **Gateway extras** — use `houmao-agent-gateway` for gateway mail-notifier polling, reminders, and other gateway-only control surfaces that live alongside an attached live gateway.
- **Credential management** — use `houmao-credential-mgr` for project-local credential lifecycle, including list, inspect, add, update, log in, rename, and remove for credentials backing specialist launches.
- **Low-level agent definition** — use `houmao-agent-definition` for low-level project-local role and preset authoring, including creating, listing, inspecting, updating, or removing roles and recipes when the higher-level specialist and profile surfaces are not sufficient.

## Pairwise Ownership Boundaries

Pairwise agent loops are advanced composed workflows:

- the user agent stays outside the execution loop,
- the designated master owns supervision after accepting the run,
- downstream work moves through pairwise immediate driver-worker edges,
- each edge closes locally before the immediate driver integrates the result.

Keep ownership boundaries explicit:

- composed topology, rendered control graphs, run charters, lifecycle vocabulary, and run-control actions belong to the selected pairwise loop skill,
- elemental immediate driver-worker edge protocol guidance belongs to `houmao-adv-usage-pattern`, specifically the pairwise edge-loop pattern,
- ordinary project setup, specialist authoring, launch, messaging, mailbox, gateway, and lifecycle work still routes to the existing direct-operation skills.

When the user only wants the simplest maintained pairwise planner, point them at the stable pairwise loop entry and ask the user to select or explicitly invoke the desired pairwise skill. When the user needs routing-packet preflight, read-only peeking, ping, pause-only resume, restart recovery with `recover_and_continue`, or emergency hard-kill controls, point them at the enriched pairwise loop entry. When the user also needs the loop plan to own workspace posture, point them at the workspace-aware pairwise loop entry. In all cases, ask the user to select or explicitly invoke the desired pairwise skill.

## Guardrails

- Do not silently auto-route generic pairwise loop planning or pairwise run-control requests into `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, or `houmao-agent-loop-pairwise-v3`; ask the user to select or explicitly invoke the desired pairwise skill.
- Do not make the user agent the upstream driver of the execution loop.
- Do not restate pairwise loop plan templates, run charters, stop modes, routing packets, mailbox result protocol, or reminder protocol inline.
- Do not push composed pairwise topology, recursive child-control planning, rendered graph semantics, or run-control actions down into `houmao-adv-usage-pattern`.
- Do not treat the stable, v2, and v3 pairwise loop skills as aliases; they are separate choices with different lifecycle and workspace surfaces.
- Do not mark any advanced entry as recommended, preferred, primary, or default; the entries are peers.
- Do not collapse the advanced entries into a single generic "advanced" surface; each entry has its own owning skill.

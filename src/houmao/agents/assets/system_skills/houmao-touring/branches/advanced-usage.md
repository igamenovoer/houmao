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

- **Pro loop authoring** — use `houmao-agent-loop-pro` to scaffold intention files, clarify loop intent, generate execplan artifacts, validate readiness, launch agents, and operate the generated loop.
- **Tree-loop mode** — choose `tree-loop` inside `houmao-agent-loop-pro` when downstream work is a local-close tree: each node replies to its immediate upstream, and non-tree cycles are handled through explicit relay choices in the generated execplan.
- **Generic-loop mode** — choose `generic-loop` inside `houmao-agent-loop-pro` when the communication graph may contain cycles, relay lanes, or task-specific predecessor-context forwarding choices.
- **Advanced usage patterns** — use `houmao-adv-usage-pattern` for multi-step workflow compositions built from existing Houmao skills, including self-notification, local-close edge loops, and forward relay loops, plus the elemental immediate driver-worker edge protocol that underlies loop components.
- **Managed-agent memory** — use `houmao-memory-mgr` to read or write a managed agent's `houmao-memo.md` free-form memo file and the managed-agent pages memory.
- **Gateway extras** — use `houmao-agent-gateway` for gateway mail-notifier polling, reminders, and other gateway-only control surfaces that live alongside an attached live gateway.
- **Credential management** — use `houmao-credential-mgr` for project-local credential lifecycle, including list, inspect, add, update, log in, rename, and remove for credentials backing specialist launches.
- **Agent definition** — use `houmao-agent-definition` for project-local `roles`, `recipes`, `raw-profiles`, `specialists`, `profiles`, and `create-agent-fast-forward`.

## Loop Ownership Boundaries

Generated loops are advanced composed workflows:

- the user agent stays outside the execution loop,
- generated execplan artifacts define the topology, mail schemas, harness, skills, workspace contracts, and run-control behavior,
- tree-loop mode uses local-close immediate upstream/downstream result routing,
- generic-loop mode records task-specific predecessor-context and relay choices when downstream nodes need context from earlier predecessors.

Keep ownership boundaries explicit:

- composed topology, rendered control graphs, generated artifacts, lifecycle vocabulary, and run-control actions belong to `houmao-agent-loop-pro`,
- elemental immediate driver-worker edge protocol guidance belongs to `houmao-adv-usage-pattern`, specifically the local-close edge-loop pattern,
- ordinary project setup, specialist authoring, launch, messaging, mailbox, gateway, and lifecycle work still routes to the existing direct-operation skills.

When the user asks for current loop authoring, route to `houmao-agent-loop-pro` and help them choose `tree-loop` or `generic-loop` mode. Do not ask them to choose among retired loop packages.

## Guardrails

- Do not route current loop planning or generated loop run-control requests to retired loop packages.
- Do not make the user agent the upstream driver of the execution loop.
- Do not restate tree-loop plan templates, run charters, stop modes, routing packets, mailbox result protocol, or reminder protocol inline.
- Do not push composed tree loop topology, recursive child-control planning, rendered graph semantics, or run-control actions down into `houmao-adv-usage-pattern`.
- Do not mark any advanced entry as recommended, preferred, primary, or default; the entries are peers.
- Do not collapse the advanced entries into a single generic "advanced" surface; each entry has its own owning skill.

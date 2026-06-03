# Advanced Orchestration Branch

Use this advanced branch when a guided-tour user is ready for composed multi-agent systems: generated loops, topology choices, or isolated multi-agent workspaces. This branch is not a catalog of every packaged Houmao skill.

## Listing Style

- Present the entries as advanced orchestration choices, not as a broad function list.
- Do not mark any entry as recommended, preferred, primary, or default unless the user's stated goal clearly selects it.
- Do not order the entries to imply a priority ranking. The ordering below is a teaching order for the tour, not a ranking.
- Do not restate generated loop templates, topology contracts, run charters, workspace creation or validation rules, routing packets, mailbox result protocol, reminder protocol, memory file layouts, or credential lifecycle details inline; keep those on the selected owning skill.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill only for state inspection the tour already needs; do not invent a new command surface here.
2. Confirm the user's advanced intent:
   - lightweight Markdown/direct-SQL loop package,
   - schema-rich generated loop,
   - tree-loop or generic-loop topology choice,
   - isolated multi-agent workspace planning, creation, validation, or summaries,
   - elemental mailbox/gateway coordination pattern before generated loops.
3. Present only the advanced entries relevant to that intent, or the concise list below when the user is browsing advanced options.
4. When the user picks one entry, tell the agent to invoke or select the owning skill named in that entry, and stop touring-level elaboration on that topic so the selected skill can own the detailed workflow.
5. After advanced setup or operation completes, offer stage-aware next actions:
   - validate a workspace or loop plan
   - choose lite or pro loop authoring
   - choose `tree-loop` or `generic-loop` mode inside pro
   - generate or validate loop artifacts
   - prepare or inspect isolated workspaces
   - launch participants
   - operate the generated loop
   - return to intermediate live inspection, mailbox, gateway, memo, or lifecycle follow-up

## Advanced Entries

- **Lite loop authoring** - use `houmao-agent-loop-lite` to scaffold a small loop package with Markdown contracts, typed Markdown templates, required generated skills, direct SQLite state, and no generated harness or docs layer.
- **Pro loop authoring** - use `houmao-agent-loop-pro` to scaffold intention files, clarify loop intent, generate schema-rich execplan artifacts, validate readiness, prepare workspaces, launch agents, and operate the generated loop.
- **Tree-loop mode in pro** - choose `tree-loop` inside `houmao-agent-loop-pro` when downstream work is a local-close tree: each node replies to its immediate upstream, and non-tree cycles are handled through explicit relay choices in the generated execplan.
- **Generic-loop mode in pro** - choose `generic-loop` inside `houmao-agent-loop-pro` when the communication graph may contain cycles, relay lanes, or task-specific predecessor-context forwarding choices.
- **Isolated multi-agent workspace management** - use `houmao-utils-workspace-mgr` to plan, create, validate, or summarize workspaces. This covers in-repo or out-of-repo layouts, per-agent worktrees, local-only shared repos, safe local-state symlinks, launch-profile cwd updates, project-command readiness, and optional memo-seed workspace rules.
- **Elemental coordination patterns** - use `houmao-adv-usage-pattern` when the user wants a supported mailbox/gateway coordination pattern before generating a full loop package.

## Loop and Workspace Ownership Boundaries

Generated loops and isolated workspaces are advanced composed workflows:

- the user agent stays outside the execution loop,
- lite execplans define Markdown contracts, typed templates, generated skills, direct SQLite state, participant bindings, and bounded run behavior,
- pro execplans define topology, mail schemas, harness, skills, workspace contracts, and run-control behavior,
- tree-loop mode uses local-close immediate upstream/downstream result routing,
- generic-loop mode records task-specific predecessor-context and relay choices when downstream nodes need context from earlier predecessors,
- isolated workspace plans define where agents work, how Git worktrees or local shared repos are prepared, how launch-profile cwd values are adjusted, and what workspace rules are seeded into memo context.

Keep ownership boundaries explicit:

- lightweight Markdown/direct-SQL generated loops belong to `houmao-agent-loop-lite`,
- composed topology, rendered control graphs, schema-rich generated artifacts, lifecycle vocabulary, and run-control actions belong to `houmao-agent-loop-pro`,
- isolated workspace planning, creation, validation, and summaries belong to `houmao-utils-workspace-mgr`,
- elemental immediate driver-worker edge protocol guidance belongs to `houmao-adv-usage-pattern`, specifically the local-close edge-loop pattern,
- ordinary project setup, specialist authoring, launch, messaging, mailbox, gateway, memo, inspection, and lifecycle work still routes to the existing direct-operation skills.

When the user asks for current loop authoring, route to `houmao-agent-loop-lite` if they explicitly want Markdown/direct-SQL or no-harness loop packages; otherwise route topology-rich generated execplans to `houmao-agent-loop-pro` and help them choose `tree-loop` or `generic-loop` mode. Do not ask them to choose among retired loop packages.

## Guardrails

- Route current loop planning and generated loop run-control requests only to the maintained loop packages.
- Keep the user agent outside the execution loop rather than making it the upstream driver.
- Do not restate tree-loop or generic-loop plan templates, run charters, stop modes, routing packets, mailbox result protocol, workspace creation or validation details, or reminder protocol inline.
- Do not push composed tree/generic loop topology, recursive child-control planning, rendered graph semantics, or run-control actions down into `houmao-adv-usage-pattern`.
- Skip unrelated utility skills in the normal advanced tour, even when they are packaged system skills.
- Do not mark any advanced orchestration entry as recommended, preferred, primary, or default unless the user's stated goal clearly selects it.
- Keep each advanced entry on its own owning skill rather than collapsing them into a single generic "advanced" surface.

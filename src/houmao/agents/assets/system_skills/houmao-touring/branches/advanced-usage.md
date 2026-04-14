# Advanced Usage Branch

Use this branch when a guided-tour user wants to understand or create an advanced pairwise agent loop.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill only for state inspection that the tour already needs; do not invent a new loop CLI surface here.
2. Explain that pairwise agent loops are advanced composed workflows:
   - the user agent stays outside the execution loop
   - the designated master owns supervision after accepting the run
   - downstream work moves through pairwise immediate driver-worker edges
   - each edge closes locally before the immediate driver integrates the result
3. Present the stable and enriched pairwise loop choices explicitly:
   - stable pairwise loop -> ask the caller to invoke or select `houmao-agent-loop-pairwise` for `plan`, `start`, `status`, and `stop`
   - enriched pairwise loop -> ask the caller to invoke or select `houmao-agent-loop-pairwise-v2` for `plan`, `initialize`, `start`, `peek`, `ping`, `pause`, `resume`, `stop`, and `hard-kill`
4. When the user only wants the simplest maintained pairwise planner, recommend the stable pairwise loop skill.
5. When the user needs initialization mail, routing-packet preflight, read-only peeking, ping, pause/resume, or emergency hard-kill controls, recommend the v2 pairwise loop skill.
6. Keep ownership boundaries explicit:
   - composed topology, rendered control graphs, run charters, lifecycle vocabulary, and run-control actions belong to the selected pairwise loop skill
   - elemental immediate driver-worker edge protocol guidance belongs to `houmao-adv-usage-pattern`, specifically the pairwise edge-loop pattern
   - ordinary project setup, specialist authoring, launch, messaging, mailbox, gateway, and lifecycle work still routes to the existing direct-operation skills
7. After the user selects a pairwise loop skill, stop touring-level elaboration and let that skill own the detailed loop workflow.

## Guardrails

- Do not silently auto-route generic pairwise loop planning or pairwise run-control requests into `houmao-agent-loop-pairwise` or `houmao-agent-loop-pairwise-v2`; ask the user to select or explicitly invoke the desired pairwise skill.
- Do not make the user agent the upstream driver of the execution loop.
- Do not restate pairwise loop plan templates, run charters, stop modes, routing packets, mailbox result protocol, or reminder protocol inline.
- Do not push composed pairwise topology, recursive child-control planning, rendered graph semantics, or run-control actions down into `houmao-adv-usage-pattern`.
- Do not treat stable and v2 pairwise loop skills as aliases; they are separate choices with different lifecycle surfaces.

## 1. Plan Authoring Contract

- [x] 1.1 Update the top-level `houmao-agent-loop-pairwise-v2` skill overview so the default prestart strategy is `precomputed_routing_packets` and `operator_preparation_wave` is explicit opt-in.
- [x] 1.2 Update `authoring/formulate-loop-plan.md` to generate one root routing packet for the master and one child routing packet for each parent-to-child pairwise edge.
- [x] 1.3 Update `authoring/revise-loop-plan.md` to revalidate packet coverage, packet freshness markers, intended recipients, immediate drivers, and child dispatch tables after plan revisions.
- [x] 1.4 Update `references/plan-structure.md` so v2 plans record `prestart_strategy`, routing packet inventory, root packet location, and child dispatch table rules.
- [x] 1.5 Update `templates/single-file-plan.md` and `templates/bundle-plan.md` to show precomputed routing packet sections or packet file references, including child packet forwarding guardrails.
- [x] 1.6 Update `authoring/render-loop-graph.md` if needed so the rendered control graph labels the default prestart path as routing-packet validation rather than a targeted preparation mail wave.

## 2. Initialize And Start Guidance

- [x] 2.1 Update `prestart/prepare-run.md` so default `initialize` validates routing packet coverage and moves to `ready` without sending operator-origin preparation mail.
- [x] 2.2 Preserve the existing targeted preparation-mail behavior in `prestart/prepare-run.md` under the explicit `operator_preparation_wave` strategy, including `require_ack` and leaf-target override rules.
- [x] 2.3 Update `references/run-charter.md` so the start charter includes the root routing packet or exact root packet reference and summarizes the selected prestart strategy.
- [x] 2.4 Update `operating/start.md` so start readiness checks the selected strategy and directs the master to forward child packets through ordinary pairwise edge requests.
- [x] 2.5 Add runtime handoff guardrails to the v2 guidance: append prepared child packets verbatim, do not edit/merge/summarize them by default, and fail closed on missing, mismatched, or stale packets.
- [x] 2.6 Update cross-references and terminology so `ready`, `initializing`, and `awaiting_ack` describe both precomputed routing-packet validation and explicit operator preparation waves accurately.

## 3. Specs And Validation

- [x] 3.1 Review the delta spec against the updated v2 skill content and adjust it if implementation discovers a necessary contract correction.
- [x] 3.2 Run `pixi run openspec validate add-pairwise-v2-routing-packets --strict`.
- [x] 3.3 Run targeted text checks for stale default-preparation wording that still says v2 sends preparation mail to delegating/non-leaf participants by default.
- [x] 3.4 Run relevant system-skill content tests or catalog/docs checks if they cover packaged skill assets, or document why no narrower automated check exists.

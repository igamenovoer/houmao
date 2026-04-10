## 1. Packaged Skill Assets

- [x] 1.1 Add a new packaged system skill directory at `src/houmao/agents/assets/system_skills/houmao-agent-loop-relay/` with a top-level `SKILL.md` that presents the skill as a relay loop planner and run controller with separate authoring and operating lanes.
- [x] 1.2 Add authoring-lane guidance pages that cover formulating a relay loop plan from user intent, revising a plan, supporting both single-file and bundle plan forms, and normalizing route policy explicitly.
- [x] 1.3 Add operating-lane guidance pages for `start`, `status`, and `stop` that define the user-agent-to-origin control plane, root `run_id` ownership, origin-owned liveness, final-result return expectations, and default interrupt-first stop behavior.

## 2. References And Templates

- [x] 2.1 Add local reference pages or templates for the authored run charter, route-policy forms, result-return contract, stop modes, reporting contract, and plan structure so the master receives one normalized relay plan contract instead of ad hoc prompt text.
- [x] 2.2 Add authoring guidance that requires a Mermaid graph in the finalized plan and shows how to render the user agent, designated master or origin, relay handoff edges, receipt flow, final-result return path, supervision loop, completion condition, and stop condition without using ASCII art.
- [x] 2.3 Add example plan templates for both the single-file Markdown form and the bundle-directory form, including relay-lane guidance, script inventory guidance, and canonical `plan.md` entrypoint rules.

## 3. Validation

- [x] 3.1 Update system-skill packaging and projection tests under `tests/unit/agents/` to assert that `houmao-agent-loop-relay` is packaged and that its top-level skill routes to both authoring and operating guidance.
- [x] 3.2 Add or update content tests to assert the required guidance strings for explicit route policy, origin-owned liveness, final-result return to the origin, default interrupt-first stop behavior, and required Mermaid relay-graph rendering.
- [x] 3.3 Run the relevant unit-test slice for packaged system skills and record the passing command output in the implementation results.

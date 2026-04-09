## 1. Packaged Skill Assets

- [ ] 1.1 Add a new packaged system skill directory at `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise/` with a top-level `SKILL.md` that presents the skill as a pairwise loop planner and run controller with separate authoring and operating lanes.
- [ ] 1.2 Add authoring-lane guidance pages that cover formulating a loop plan from user intent, revising a plan, supporting both single-file and bundle plan forms, and normalizing delegation policy explicitly.
- [ ] 1.3 Add operating-lane guidance pages for `start`, `status`, and `stop` that define the user-agent-to-master control plane, root `run_id` ownership, master-owned liveness, and default interrupt-first stop behavior.

## 2. References And Templates

- [ ] 2.1 Add local reference pages or templates for the authored run charter, delegation policy forms, stop modes, reporting contract, and plan structure so the master receives one normalized plan contract instead of ad hoc prompt text.
- [ ] 2.2 Add authoring guidance that requires a Mermaid graph in the finalized plan and shows how to render the user agent, designated master, pairwise control edges, supervision loop, completion condition, and stop condition without using ASCII art.
- [ ] 2.3 Add example plan templates for both the single-file Markdown form and the bundle-directory form, including script inventory guidance and canonical `plan.md` entrypoint rules.

## 3. Validation

- [ ] 3.1 Update system-skill packaging and projection tests under `tests/unit/agents/` to assert that `houmao-agent-loop-pairwise` is packaged and that its top-level skill routes to both authoring and operating guidance.
- [ ] 3.2 Add or update content tests to assert the required guidance strings for explicit delegation policy, master-owned liveness, default interrupt-first stop behavior, and required Mermaid loop-graph rendering.
- [ ] 3.3 Run the relevant unit-test slice for packaged system skills and record the passing command output in the implementation results.

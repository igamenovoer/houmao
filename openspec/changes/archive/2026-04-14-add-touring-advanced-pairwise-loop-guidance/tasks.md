## 1. Touring Skill Guidance

- [x] 1.1 Add `branches/advanced-usage.md` to `houmao-touring` with stable versus v2 pairwise loop selection guidance.
- [x] 1.2 Update `houmao-touring/SKILL.md` scope, workflow branch list, branch index, routing guidance, and guardrails to reference the advanced-usage branch.
- [x] 1.3 Ensure the touring guidance tells callers to explicitly select or invoke `houmao-agent-loop-pairwise` or `houmao-agent-loop-pairwise-v2` rather than silently auto-routing generic loop requests.
- [x] 1.4 Ensure the touring guidance states that composed pairwise topology belongs to the pairwise loop skills and elemental immediate driver-worker edge protocol belongs to `houmao-adv-usage-pattern`.

## 2. Verification

- [x] 2.1 Update system-skill installation/projection tests to assert the new touring branch file is installed.
- [x] 2.2 Add test assertions for key touring routing text, including stable pairwise, v2 pairwise, explicit selection, and `houmao-adv-usage-pattern` boundary guidance.
- [x] 2.3 Run focused system-skill tests covering the packaged touring skill projection.
- [x] 2.4 Run `openspec status --change add-touring-advanced-pairwise-loop-guidance` and strict OpenSpec validation for the change.

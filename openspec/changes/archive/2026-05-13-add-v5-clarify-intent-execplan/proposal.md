## Why

The current v5 `clarify-intent` guidance asks one question at a time, but it does not force a structured scan of the loop's core logic before asking. This can lead agents to ask local wording or field questions while missing high-impact ambiguities in objective authority, mail-driven process flow, state transitions, scheduling, completion, recovery, and generated execplan implementation choices.

## What Changes

- Replace the ambiguous `clarify intent` operation name with an explicit `clarify-intent` subcommand.
- Add a new `clarify-execplan` subcommand focused on generated execplan implementation choices.
- Add a shared clarification protocol reference page based on the strong parts of the spec-kit clarify flow:
  - structured coverage scan before questioning;
  - internal ambiguity map;
  - impact × uncertainty prioritization;
  - at most five questions;
  - exactly one question at a time;
  - recommended answer with concise rationale;
  - immediate recording and source update after each accepted answer;
  - validation that the clarification removed ambiguity and did not create contradictions;
  - final coverage summary.
- Rewrite `clarify-intent` so it gathers richer context from intention files, project context, prior ADRs, and the mail-based loop model before asking questions.
- Add `clarify-execplan` so generated execplan artifacts can be reviewed for unclear implementation decisions after generation or update.
- Preserve the existing principle that intention clarification updates editable intention source, while execplan clarification updates generated execplan artifacts and execplan ADRs.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `houmao-agent-loop-pairwise-v5-skill`: Clarification behavior changes to support explicit `clarify-intent` and `clarify-execplan` subcommands, a shared structured clarification protocol, stronger context gathering, and separate intent-level versus execplan-level decision recording.

## Impact

- Affected skill assets: `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v5/`.
- Affected top-level routing: operation list and route names for clarification.
- Affected authoring pages: rewrite `clarify-intent.md`; add `clarify-execplan.md`; update execplan/update guidance where clarification affects generated artifacts.
- Affected runtime references: add a clarification protocol page and reference the mail-based agent loop model as required context.
- Affected generated loop artifacts: `clarify-execplan` may update `execplan/adrs/`, specs, harness, skills, agents, docs, and manifest/validation notes as needed by accepted clarification decisions.
- No dependency or runtime CLI change outside the packaged skill guidance.

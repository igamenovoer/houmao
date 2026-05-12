## Context

The v5 skill currently has one clarification route for intent. It reads intention files, asks one focused question at a time, records accepted decisions as ADRs, and updates intention Markdown. That shape is useful, but the question discovery step is too shallow: it lists decision areas without forcing the invoking agent to build a coverage map of the loop's core logic before asking.

The spec-kit `clarify.md` command provides a stronger pattern: load the current artifact, scan it against a taxonomy, prioritize ambiguity by impact and uncertainty, ask at most five targeted questions, recommend an answer, record each accepted answer immediately, and report coverage. For v5 this pattern needs two scopes:

- intent clarification: what loop the user wants;
- execplan clarification: whether the generated implementation of that loop is coherent and accepted.

The mail-notification runtime model is central to both. Many high-impact ambiguities in Houmao loops are not generic product-spec ambiguities; they are failures to define who sends mail, who processes mail, what state transition follows, what tick runs after mail, and how agents avoid in-chat waiting.

## Goals / Non-Goals

**Goals:**

- Add canonical `clarify-intent` and `clarify-execplan` authoring subcommands.
- Rewrite `clarify-intent` to use structured coverage scanning and prioritized questions.
- Add `clarify-execplan` for generated execplan artifact review and implementation-decision confirmation.
- Add a shared clarification protocol reference page for coverage scan, prioritization, question style, answer integration, validation, and coverage summary.
- Require the mail-based agent loop model as mandatory context for both clarification flows.
- Keep intent decisions in intention source and intent ADRs.
- Keep execplan implementation decisions in generated execplan artifacts and execplan ADRs.

**Non-Goals:**

- Build an automated semantic analyzer for arbitrary Markdown.
- Change generated execplan layout outside clarification guidance.
- Change how agents execute loops at runtime.
- Add new dependencies.
- Make every clarification question mandatory; the workflow must still ask only high-impact questions.

## Decisions

### Use canonical hyphenated subcommand names

Use `clarify-intent` and `clarify-execplan` as the canonical operation names in `SKILL.md`, routing, and authoring page names. The old natural phrase `clarify intent` may be treated as an unambiguous alias for `clarify-intent`, but generated docs and routed pages should teach the hyphenated names.

Alternative considered: keep `clarify intent` and add `clarify execplan`. Rejected because the user explicitly wants subcommands, and hyphenated names match the rest of the v5 command style.

### Add `subskills/reference/clarification-protocol.md`

The shared protocol should capture the reusable spec-kit pattern without copying feature-spec assumptions that do not fit agent loops. It should define:

- read sources first;
- build an internal coverage map;
- mark each category clear, partial, missing, deferred, or not applicable;
- generate candidate questions internally;
- ask at most five questions per session;
- ask exactly one question at a time;
- require each question to be multiple-choice or a constrained short answer;
- provide a recommended answer and concise reasoning;
- accept `yes`, `recommended`, or `suggested`;
- record each accepted answer immediately;
- update the most appropriate source artifacts immediately;
- validate no contradiction remains;
- finish with a coverage summary.

Alternative considered: duplicate the full protocol in both clarification pages. Rejected because drift would be likely and the protocol is shared.

### Split clarification by authority boundary

`clarify-intent` reads and updates user-editable source:

```text
<loop-dir>/intention/
<loop-dir>/adrs/
```

It asks questions whose answers define the intended loop behavior. It must not directly edit generated `execplan/`.

`clarify-execplan` reads and updates generated execution material:

```text
<loop-dir>/execplan/
<loop-dir>/execplan/adrs/
```

It asks questions whose answers confirm or correct generated implementation choices. It may update specs, harness guidance, generated skill text, agent bindings, docs, manifest metadata, or validation notes when the accepted answer affects them.

Alternative considered: one clarify command with a mode flag. Rejected because the distinction is conceptual and should be visible in routing.

### Use loop-specific coverage taxonomies

`clarify-intent` should scan for missing intent-level decisions:

- objective, non-goals, and completion signals;
- participant roles, authorities, and handoff rights;
- collaboration topology and work-item lifecycle;
- mail/message families at intent level;
- on-event and on-tick responsibilities;
- state/bookkeeping needs;
- operator controls and recovery posture;
- workspace, artifact, and evidence expectations;
- project integration context;
- terminology and explicit omissions.

`clarify-execplan` should scan generated implementation decisions:

- process model phases, events, handoffs, ticks, terminal posture, and recovery posture;
- mail schemas, renderers, reply links, ack/result/error families, and payload lifecycle;
- state schema, transitions, invariants, ownership, backend choice, and repair posture;
- harness commands for init, query, validate, apply, render, and explain;
- generated skill triggers, bounded procedures, stop points, and tick placement;
- agent bindings, notifier prompts, support skills, workspace policy, and memo posture;
- run artifacts, evidence refs, validation coverage, manifest coherence, and generated docs;
- platform boundary compliance and no in-chat waiting.

### Prioritize core loop logic over local file questions

The clarification pages should explicitly discourage low-impact local questions when higher-impact loop logic is missing. Questions should be selected by impact on architecture, generated contracts, runtime safety, scheduling, recovery, validation, or user acceptance.

Good questions confirm things like completion authority, handoff reply expectations, timeout handling, state transition ownership, and recovery policy. Weak questions ask about local wording, file placement, or minor template preferences that do not change generated behavior.

## Risks / Trade-offs

- Too many categories make agents over-question → Cap each session at five accepted questions and require impact × uncertainty prioritization.
- Execplan clarification might be mistaken for hand-editing generated output casually → Require accepted decisions, execplan ADRs, and coherent downstream artifact updates.
- Intent clarification might drift into implementation detail → Define the authority boundary and defer implementation-only decisions to `clarify-execplan`.
- Agents might skip the mail runtime model → Mark `runtime-mail-model.md` as MUST READ in both clarification pages and the shared protocol when mail behavior is involved.
- Coverage summaries could become verbose → Require concise status tables focused on clear, resolved, deferred, and outstanding categories.

## Migration Plan

1. Add `subskills/reference/clarification-protocol.md`.
2. Rename or rewrite the current route documentation so `clarify-intent` is canonical.
3. Add `subskills/authoring/clarify-execplan.md`.
4. Update `SKILL.md` operations and routing.
5. Update design docs and validation/update guidance where clarification decisions affect execplan artifacts.
6. Validate Markdown links and run `git diff --check`.

## Open Questions

- None.

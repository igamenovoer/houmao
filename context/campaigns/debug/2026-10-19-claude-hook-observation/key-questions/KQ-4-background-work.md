# KQ-4: Background Work Observability

Status: resolved (iteration 1, 2026-10-19). Owner: iteration 1. Campaign: [debug-intent.md](../debug-intent.md).

## Question

Can the session-scoped `work` axis (`context/features/2026-10-19-session-work-axis/`) ever be cleared by live provider evidence, or is the terminal-payload mirror the only v1 source?

## Propositions

### P4.1 Stop payload reports outstanding background work

An agent that backgrounds a task and returns control produces `Stop` with a non-empty `background_tasks` (or documented equivalent). Test: S5 capture.

### P4.2 Completion evidence exists at the floor

When the background task later finishes, some observable event fires: a task-lifecycle hook (`TaskCreated`/`TaskCompleted` or as found), a notification, or a provider-initiated turn. The exact mechanism is named, with payload. Test: S5 capture; record everything that fires between background start and idle.

### P4.3 Ghost-turn behavior is characterized

If background completion wakes the agent into a new turn, the wake's hook signature is recorded (does `UserPromptSubmit` fire? does activity appear without it?), so turn arming rules can account for provider-initiated turns. Test: S5 capture.

### P4.4 idle_prompt semantics

`Notification` `idle_prompt` either respects outstanding background work or fires while work runs; either result is recorded as the semantics. Test: S5 capture with an idle wait (short, bounded; cost-lane compliant).

### P4.5 TUI corroboration check

Whether the 2.1.303 TUI renders a running-background indicator reliable enough to serve as secondary evidence is recorded from the paired pane recording. Test: S5 pane recording inspection.

## Answer

Iteration 1, 2026-10-19. Verdicts per proposition:

- **P4.1 confirmed.** The turn that backgrounds work ends with non-empty `Stop.background_tasks: [{command: "sleep 90", description, id, status: "running", type: "shell"}]`; after completion the list drains to `[]`. Evidence: [S5](../evidences/2026-10-19-s5-background-work.md).
- **P4.2 confirmed, mechanism named.** Completion fires a provider-initiated turn: a `UserPromptSubmit` whose `prompt` is a `<task-notification>` XML document (task-id, tool-use-id, output-file, status `completed`, exit-code summary) followed by its `Stop` about 2 s later. No task-lifecycle hook event and no `Notification` exist in the v1 subscribed set; the ghost turn is the completion evidence. Evidence: [S5](../evidences/2026-10-19-s5-background-work.md).
- **P4.3 confirmed.** The wake signature is fully characterized: `UserPromptSubmit` DOES fire (with a fresh `prompt_id` and the machine-authored notification text, no human origin), then `Stop`. Turn-arming rules must treat a `<task-notification>`-shaped `UserPromptSubmit` as a provider wake, not a human submission. Evidence: [S5](../evidences/2026-10-19-s5-background-work.md).
- **P4.4 unresolved (named gap).** `Notification` is not in the v1 subscribed set, so `idle_prompt` semantics were never exercisable; the completion wake arrived as a ghost turn instead. To test P4.4 a later iteration must subscribe `Notification` and repeat the bounded idle wait. Evidence gap named, not ignored.
- **P4.5 confirmed.** The 2.1.303 TUI renders a reliable running-background indicator: dock suffix `1 shell still running` and footer `1 shell · ↓ to manage`, present from task start (s000010) through completion and cleared at the completion frame. Suitable as secondary evidence. Evidence: [S5](../evidences/2026-10-19-s5-background-work.md).

Summary: the `work` axis can be cleared by live provider evidence (the ghost turn), not only by terminal-payload mirroring; the payload mirror remains a valid fallback for un-watched completions.

## Scope

Background-work evidence only. The axis's state-transition rules are validated in KQ-5; this question only decides which events exist to drive them. Evidence: `evidences/` links added as produced.

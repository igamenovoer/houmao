## Context

Issue 19 originally looked like a hard context-corruption failure: Codex could return to a visible prompt after a remote compact/server error, but later turns often failed again. The previous change modeled that as `reset_required`, causing the next accepted semantic prompt to start from clean context. New provider behavior weakens that assumption. The same prompt-adjacent compact error can still appear, but continuing in the same chat sometimes succeeds.

The system still needs two protections:

- state tracking must report the prompt surface correctly when the composer is ready, even if the current latest turn contains an error cell, and
- safeguards must prevent stale active evidence from keeping a stable promptable surface active forever.

The changed behavior is therefore not "ignore the error". It is "classify the error as recoverable degraded context, keep the surface promptable, block success, and let ordinary prompt control continue current context unless the caller explicitly asks for a new chat".

## Goals / Non-Goals

**Goals:**

- Preserve prompt readiness when Codex shows a current prompt-adjacent compact/server error and the composer is stable, accepting input, not editing input, and not blocked by an overlay.
- Keep current prompt-adjacent error evidence as a success blocker.
- Replace mandatory `reset_required` semantics with a softer degraded-context state or diagnostic that does not force reset.
- Ensure compact/server error detection only considers the prompt-adjacent live prompt region, not arbitrary historical scrollback.
- Make ordinary gateway prompt control continue in the current chat when degraded context is present.
- Preserve explicit clean-context requests through `chat_session.mode = new`.
- Ensure stable false-active recovery can turn a long-stable promptable error surface from active to ready without setting `last_turn.result=success`.
- Update notifier behavior so degraded prompt-ready sessions are eligible for normal current-context notifier prompts when other gates pass.

**Non-Goals:**

- Guaranteeing that continuing after a compact/server error will always work.
- Automatically choosing between "continue current chat" and "new chat" based on provider-specific recovery guesses.
- Treating a current compact/server error as a successful turn.
- Scanning full scrollback for old compact/server errors.
- Removing explicit context-reset support for callers that want a new chat.

## Decisions

### Use degraded-context semantics, not reset-required semantics

The public state should not say `reset_required` for this condition. That name implies mandatory behavior and pushes gateway/notifier code toward automatic reset. The replacement should be either a `chat_context = "degraded"` value or an equivalent stable diagnostic such as a note plus `chat_context = "current"`. Prefer `chat_context = "degraded"` because it gives consumers a structured signal without changing prompt admission.

`degraded` means:

- the prompt surface may still be ready;
- the current latest turn has prompt-adjacent recoverable error evidence;
- success settlement is blocked for that turn; and
- the next ordinary prompt is allowed to continue current chat context.

Alternative considered: keep the field value `reset_required` but stop resetting. That preserves fewer code changes, but the name would keep encoding the wrong contract and make future regressions likely.

### Keep compact/server matching prompt-adjacent

Codex error matching should continue to use the bounded prompt-area region, not latest-turn history or full screen text. Old compact errors can remain visible above the current prompt after later conversation progress. Those historical cells must not mark the current state as degraded, must not block current success settlement, and must not affect prompt admission.

Alternative considered: scan the current latest-turn window. That is still too wide for this failure mode because the requirement is specifically "near the prompt area" and the user called out long-history confusion as a risk.

### Error blocks success but does not imply active

A current prompt-adjacent compact/server error should set current-error evidence and clear success candidacy. It should not create active evidence, should not force `surface.ready_posture=unknown`, and should not make `turn.phase=active` when the prompt/composer facts indicate ready.

When an old active signal remains sticky despite a stable submit-ready error surface, the existing final stable-active recovery path should apply. Recovery should publish non-active readiness but leave `last_turn.result=none`, because the error surface is neither success nor a recognized known-failure terminal result.

Alternative considered: introduce a separate terminal result for recoverable error. That would enlarge the public lifecycle vocabulary and is unnecessary for the immediate gateway/notifier behavior.

### Gateway prompt control treats degraded as current-context eligible

Gateway prompt readiness should keep using the existing prompt-ready contract. If the target is prompt-ready and `chat_context=degraded`, ordinary prompt requests that omit `chat_session` should be delivered exactly like current-context prompt work.

For native headless targets, degraded context must not force the resolved selector to `mode=new`. For TUI-backed targets, degraded context must not trigger the reset-then-send workflow. The reset-then-send workflow remains available only when the caller explicitly sends the supported TUI clean-context selector, currently `chat_session.mode = new`.

Alternative considered: reject ordinary prompt control while degraded and require explicit caller choice. That avoids choosing wrong recovery behavior but would reintroduce stuck unattended workflows even though the TUI is promptable.

### Mail notifier uses ordinary current-context prompt work

When the notifier finds open inbox work and the target is otherwise prompt-ready, degraded context should not cause a busy skip and should not trigger a reset. The notifier should enqueue or deliver the normal wake-up prompt through the current-context path.

Audit records may include degraded-context detail for diagnosis, but the outcome should not be `clean_context_enqueued` unless the notifier is explicitly extended later with a caller-configured clean-context policy.

Alternative considered: keep notifier reset-only while direct prompts continue current context. That would make unattended behavior diverge from manual/operator behavior and would still lose recoverable chat continuity.

## Risks / Trade-offs

- Continuing current chat may fail again -> Preserve explicit `chat_session.mode = new` so callers can reset when they decide continuity is not worth preserving.
- Degraded classification may hide a real hard-corruption case -> Keep the degraded diagnostic visible in tracked state and audit details so operators can detect repeated failures.
- Error matching may become too narrow for future Codex wording -> Keep the compact/server phrase matcher isolated and covered by fixtures so new observed wording can be added deliberately.
- Stable-active recovery could mask real long-running work -> Require independent prompt-ready evidence, no blocking overlay, accepting input, not editing input, stable unchanged surface, and do not settle success.
- Existing reset-required code paths may partially remain -> Remove automatic consumption paths and rename tests/fixtures so no public behavior still treats recoverable compact errors as mandatory reset.

## Migration Plan

No persisted user-data migration is required. Implementation should change the in-memory/public tracked-state vocabulary before this change is archived so the stable contract does not expose `reset_required` for recoverable compact/server errors.

Rollback is direct: restore the previous automatic reset behavior if provider behavior regresses and continuation becomes consistently unsafe again. That rollback should be a deliberate spec change because it changes prompt-control semantics.

## Open Questions

None for implementation. The recommended field shape is `chat_context = "degraded"`; if implementation finds that changing the enum is too invasive, it may use `chat_context = "current"` plus a stable degraded diagnostic note, but it must still avoid any automatic reset behavior.

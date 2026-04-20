## 1. Queue Model And Classification

- [x] 1.1 Add `coalesced` as a terminal gateway stored request state in gateway models and any strict validation helpers.
- [x] 1.2 Add helper logic to classify coalescible control intents from accepted queue rows, limited to `interrupt` and exact whole-prompt `/compact`, `/clear`, or `/new`.
- [x] 1.3 Ensure `mail_notifier_prompt`, ordinary prompts, unsupported stored kinds, non-accepted rows, and different managed-agent epochs remain coalescing boundaries.

## 2. Runtime Coalescing Behavior

- [x] 2.1 Update `_take_next_request()` to inspect the oldest accepted queue run before promoting work to `running`.
- [x] 2.2 Collapse duplicate interrupts to one effective interrupt.
- [x] 2.3 Collapse duplicate and superseded context-control prompts so `/new` supersedes `/clear` and `/compact`, and `/clear` supersedes `/compact`.
- [x] 2.4 Preserve one effective interrupt followed by one final effective context-control prompt when a run contains both intent classes.
- [x] 2.5 Mark skipped accepted rows as `coalesced` with `finished_at_utc`, `result_json`, and gateway event data that identify the effective superseding action.
- [x] 2.6 Refresh gateway status and reminder wakeups after coalescing so queue depth reflects only accepted and running work.

## 3. Tests

- [x] 3.1 Add unit coverage for duplicate interrupt coalescing.
- [x] 3.2 Add unit coverage for duplicate `/compact` prompt coalescing.
- [x] 3.3 Add unit coverage for `/compact`, `/clear`, and `/new` supersession.
- [x] 3.4 Add unit coverage for mixed interrupt plus context-control runs executing one interrupt before one final context prompt.
- [x] 3.5 Add unit coverage proving ordinary prompts, `mail_notifier_prompt`, and epoch changes break coalescing.
- [x] 3.6 Add unit coverage for durable audit state, result metadata, gateway events, and queue-depth exclusion for `coalesced` records.

## 4. Documentation And Verification

- [x] 4.1 Update gateway protocol and queue-recovery documentation to describe control-intent coalescing, recognized commands, guardrails, and audit state.
- [x] 4.2 Run focused gateway tests for the new queue coalescing behavior.
- [x] 4.3 Run the standard unit test suite or document any test command that cannot complete.

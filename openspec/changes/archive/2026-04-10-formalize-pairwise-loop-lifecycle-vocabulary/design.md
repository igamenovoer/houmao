## Context

`houmao-agent-loop-pairwise` is a documentation-first system skill that already separates broad lanes into authoring, prestart, and operating guidance. The current material is sufficient for `start`, `status`, and `stop`, but it does not define one explicit lifecycle vocabulary for operator actions and observed run states. That leaves room for drift between prompts, docs, tests, and future implementations, especially around `peek`, `ping`, `pause`, `resume`, and the difference between an action and an observed condition.

This change is intentionally narrow. It does not introduce a new runtime loop engine or a new transport protocol. It formalizes the names and semantics that the pairwise skill uses when describing control of an already-authored pairwise loop.

## Goals / Non-Goals

**Goals:**

- Define one canonical operator action vocabulary for pairwise loop lifecycle control.
- Define one canonical observed state vocabulary that is distinct from operator actions.
- Clarify which actions are read-only inspection versus active messaging.
- Clarify that `stop` remains master-directed and that any participant-wide advisory stop messaging is separate.
- Clarify that `pause` and `resume` describe suspension and restoration of loop wakeup mechanisms rather than only mail-notifier toggling.

**Non-Goals:**

- Creating a new runtime loop scheduler, queue, or transport.
- Adding a new global loop-state persistence subsystem.
- Changing relay-loop lifecycle vocabulary in the same change.
- Replacing the lower-level skills that already own messaging, gateway, mailbox, reminder, or inspection behavior.

## Decisions

### Decision: Separate operator actions from observed states

The lifecycle vocabulary will be split into two lists:

- operator actions: `plan`, `initialize`, `start`, `peek`, `ping`, `pause`, `resume`, `stop`
- observed states: `authoring`, `initializing`, `awaiting_ack`, `ready`, `running`, `paused`, `stopping`, `stopped`, `dead`

Rationale:

- An action is something the operator asks the system to do.
- A state is something the operator or skill observes about the run.
- Mixing them causes ambiguity such as treating `dead` like a command or treating `status` like both an action and a state.

Alternative considered:

- Keep one mixed vocabulary list for both commands and statuses.
  Rejected because it preserves the ambiguity the change is trying to remove.

### Decision: Keep `plan` and `initialize` as lifecycle actions even though the filesystem layout stays lane-based

The skill may keep its current directory layout of `authoring/`, `prestart/`, and `operating/`, but the operator-facing lifecycle vocabulary will be action-based:

- `plan` maps to authoring guidance
- `initialize` maps to prestart guidance
- `start`, `peek`, `ping`, `pause`, `resume`, and `stop` map to runtime control guidance

Rationale:

- The user asked for well-defined lifecycle names.
- Renaming the on-disk folders is not required to expose a clearer operator contract.
- This reduces churn in the existing skill structure while still making the lifecycle vocabulary explicit.

Alternative considered:

- Rename the whole skill directory structure to action names.
  Rejected because the current lane-based layout already matches existing documentation and tests, and the user request is about vocabulary, not repo layout.

### Decision: Define `peek` as read-only and selector-based

`peek` will be the canonical read-only inspection action with selectors:

- `peek master`
- `peek all`
- `peek <agent-name>`

Rationale:

- This makes `peek` a family of one inspection verb rather than a mix of `status`, `inspect`, and ad hoc peeking language.
- It aligns cleanly with `houmao-agent-inspect` for read-only participant inspection and with master status review for run-level inspection.

Alternative considered:

- Keep `status` for master-only observation and `peek` for everything else.
  Rejected because it keeps two overlapping read-only verbs for closely related tasks.

### Decision: Define `ping` as active messaging, not inspection

`ping <agent-name>` will mean sending an active message to a selected participant to ask what is happening.

Rationale:

- The operator needs a term that clearly differs from read-only inspection.
- This aligns with the existing lower-level boundary between `houmao-agent-inspect` and `houmao-agent-messaging`.

Alternative considered:

- Treat `ping` as a lightweight synonym for `peek`.
  Rejected because it erases the important difference between reading state and causing new traffic.

### Decision: Keep `stop` master-directed and treat any participant-wide advisory mail separately

`stop` will remain the canonical termination action directed at the master. If the skill later exposes participant-wide advisory termination mail, that action will be documented separately, for example as `broadcast-stop`, and will not be treated as equivalent to `stop`.

Rationale:

- The pairwise model already places liveness and supervision on the master after acceptance.
- Making `stop` fan out to all participants by default would weaken that ownership model.

Alternative considered:

- Redefine `stop` to broadcast directly to every participant.
  Rejected because it conflicts with the current master-owned control model and would blur responsibility for reconciliation.

### Decision: Define `pause` and `resume` in terms of wakeup control, not notifier-only toggles

`pause` will mean suspending the loop's wakeup mechanisms for the run, not merely turning off mail notifications in isolation. `resume` will mean restoring those mechanisms.

Rationale:

- A loop can still wake through reminders even if mail notifier is off.
- The operator-facing term `pause` should mean the run is intentionally stalled, not just partially muted.

Alternative considered:

- Define `pause` as mail-notifier disable only.
  Rejected because it is too weak for the name and would mislead operators.

## Risks / Trade-offs

- [Vocabulary-first without a new runtime enum] → Mitigation: state names are defined as a documented contract first; future implementation may persist them more formally without changing the names.
- [Old `status` wording may linger in docs or tests] → Mitigation: update the pairwise skill, overview docs, and related tests together.
- [Pause semantics may outpace current low-level control surfaces] → Mitigation: describe `pause` and `resume` as control intent over wakeup mechanisms while reusing the existing gateway/reminder primitives rather than inventing a new scheduler in this change.
- [Operators may still want a participant-wide stop broadcast] → Mitigation: explicitly separate any optional advisory broadcast action from canonical `stop`.

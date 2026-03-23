## Context

The repository already has three adjacent teaching artifacts, but none of them shows the target workflow end to end:

- `mailbox-roundtrip-tutorial-pack` demonstrates a two-agent mailbox exchange without gateway-driven later turns.
- `gateway-mail-wakeup-demo-pack` demonstrates gateway notifier wake-up for one mailbox-enabled session.
- `houmao-server-dual-shadow-watch` demonstrates demo-owned `houmao-server` lifecycle and paired Claude/Codex provisioning, but not asynchronous mailbox ping-pong.

The repository also already has the key headless platform primitives:

- managed headless launch through `POST /houmao/agents/headless/launches`
- transport-neutral prompt and interrupt submission through `POST /houmao/agents/{agent_ref}/requests`
- managed-agent detail inspection through `/state/detail`
- post-launch gateway attach and notifier control through `/gateway/*`
- durable headless turn inspection through `/turns/*`
- runtime-owned mailbox system skills that tell launched agents how to inspect, send, reply, and mark processed mail read without duplicating transport instructions in every role
- tracked lightweight dummy-project and mailbox-demo fixture families under `tests/fixtures/`

This change therefore does not need new runtime primitives first. It needs a new standalone demo pack that composes the existing server, gateway, mailbox, and fixture surfaces into one reproducible workflow and keeps all Houmao-generated state under one pack-owned `outputs/` root.

## Goals / Non-Goals

**Goals:**

- Add a standalone demo pack at `scripts/demo/mail-ping-pong-gateway-demo-pack/`.
- Demonstrate one two-agent asynchronous conversation between managed headless Claude Code and Codex participants.
- Reuse the tracked dummy-project fixture family and tracked `mailbox-demo-default` brain recipes instead of inventing a new launch-fixture family.
- Add thin demo-specific initiator and responder role packages that rely on runtime-owned mailbox system skills and add only the ping-pong thread and round-limit policy.
- Use one explicit kickoff action, then let later turns progress through mailbox state plus gateway wake-up.
- Keep all Houmao-generated state for the run under `<demo-home>/outputs/`.
- Provide both an automatic end-to-end flow and a stepwise operator flow with bounded polling, visible progress, and explicit timeout diagnostics.
- Produce stable demo-owned evidence that explains message flow, turn boundaries, wake-up behavior, and final outcome.
- Keep artifact names and the operator-facing command vocabulary transport-neutral enough to extend to TUI or mixed modes later without replacing the pack.

**Non-Goals:**

- Implement TUI/TUI or mixed-mode parity in this change.
- Extend or rewrite the existing mailbox-roundtrip, gateway-wakeup, or dual-shadow-watch packs in place.
- Prove exact gateway notifier poll-by-poll sequencing.
- Add a pack-local live-agent `autotest/` harness in v1.
- Build a general-purpose multi-agent orchestration framework beyond this demo.

## Decisions

### Decision: Build a new standalone demo pack using the newer thin-wrapper module pattern

The new workflow needs one coherent operator story: two managed agents, one mailbox thread, later gateway-driven turns, stable inspection artifacts, and one output-root ownership model. Extending an existing pack would inherit the wrong default teaching contract:

- `mailbox-roundtrip-tutorial-pack` is intentionally gateway-optional.
- `gateway-mail-wakeup-demo-pack` is intentionally single-agent.
- `houmao-server-dual-shadow-watch` is intentionally interactive observation rather than asynchronous conversation.

The new pack will therefore own its own `README.md`, `run_demo.sh`, tracked inputs, expected report, and backing Python module under `src/houmao/demo/mail_ping_pong_gateway_demo_pack/`.

It will follow the newer pack structure:

- thin `run_demo.sh`
- `scripts/demo_driver.py`
- backing module files rooted at `src/houmao/demo/mail_ping_pong_gateway_demo_pack/`

At minimum, the backing module will expose:

- `driver.py` for orchestration and CLI command routing
- `models.py` for persistent demo state and report models
- `server.py` for demo-owned `houmao-server` lifecycle
- `agents.py` for build, launch, request, gateway, and stop helpers
- `events.py` for normalized event extraction
- `reporting.py` for inspect and report generation

**Alternatives considered**

- Extend `mailbox-roundtrip-tutorial-pack`: rejected because it would blur the existing direct mailbox roundtrip contract.
- Extend `gateway-mail-wakeup-demo-pack`: rejected because it would overload a single-agent tutorial with two-agent thread semantics.
- Extend `houmao-server-dual-shadow-watch`: rejected because it would mix interactive TUI monitoring goals with a deterministic asynchronous mailbox workflow.

### Decision: Reuse the tracked mailbox-demo fixture family, but with demo-specific role packages

The default tracked fixture root for this demo will be `tests/fixtures/agents`, overridable via `AGENT_DEF_DIR` the same way other demo packs do. The demo will reuse the existing lightweight dummy-project and mailbox-demo fixture family rather than inventing new launch fixtures:

- dummy project source: `tests/fixtures/dummy-projects/mailbox-demo-python`
- Claude recipe: `tests/fixtures/agents/brains/brain-recipes/claude/mailbox-demo-default.yaml`
- Codex recipe: `tests/fixtures/agents/brains/brain-recipes/codex/mailbox-demo-default.yaml`

The current tracked `mailbox-demo` role is too generic for this conversation contract. The demo will therefore add two thin tracked role packages in the same agent-definition root:

- `mail-ping-pong-initiator`
- `mail-ping-pong-responder`

Those roles are intentionally small. They will preserve the narrow-scope posture of `mailbox-demo`, but they will not restate filesystem mailbox mechanics. Instead they will rely on the runtime-owned mailbox system skill and add only:

- the ping-pong conversation goal
- the thread-key contract
- the round-limit stop rule
- the per-role behavior split between initiator and responder

This choice aligns with the existing mailbox system-skill contract: the gateway reminder prompt already instructs the agent to use the runtime-owned mailbox skill, and the runtime already projects that skill for mailbox-enabled sessions.

**Alternatives considered**

- Reuse the bare `mailbox-demo` role: rejected because it narrows scope but does not define this conversation behavior.
- Put mailbox behavior directly into new recipe-owned skills: rejected because the runtime-owned mailbox skill is already the platform contract for mailbox operations.
- Create a pack-local dummy project template: rejected because the repository already has a standardized dummy-project fixture family for narrow runtime flows.

### Decision: Bootstrap headless participants through explicit build-brain plus headless launch

The headless launch API requires `agent_def_dir`, `brain_manifest_path`, `role_name`, `tool`, and `working_directory`, so the demo must define an explicit bootstrap chain.

Startup will:

1. resolve the effective `agent_def_dir`
2. provision copied dummy-project workdirs under `<output-root>/projects/initiator/` and `<output-root>/projects/responder/`
3. build one Claude brain home from the tracked `mailbox-demo-default` Claude recipe into `<output-root>/runtime/`
4. build one Codex brain home from the tracked `mailbox-demo-default` Codex recipe into `<output-root>/runtime/`
5. capture the resulting manifest paths
6. call `POST /houmao/agents/headless/launches` twice with:
   - the built manifest path for the selected tool
   - the copied workdir for that participant
   - the effective `agent_def_dir`
   - the explicit role name for initiator or responder

This separates reusable tool/bootstrap fixtures from demo-specific behavior policy and avoids an implicit or prebuilt-manifest dependency.

**Alternatives considered**

- Reference prebuilt manifest paths directly: rejected because the pack should remain self-contained and rebuildable from tracked recipes.
- Launch via CAO-backed TUI sessions first: rejected because v1 is intentionally headless-first.

### Decision: Use demo-owned `houmao-server` managed headless authority end to end

The pack will treat `houmao-server` as the control and inspection authority for the live run.

The server flow will follow the established dual-shadow-watch pattern, narrowed for headless use:

- choose one free loopback port for the run and persist the selected `api_base_url`
- start `houmao-server serve` under the demo-owned server area
- pass a server-private runtime root under `<output-root>/server/`
- use bounded health polling before any agent launch begins
- do not use `--startup-child`, because this demo does not depend on CAO child startup

Startup will then:

- launch one headless Claude Code managed agent and one headless Codex managed agent
- attach gateways for both agents after launch
- enable mailbox notifier polling for both gateways
- persist the resulting identities into `outputs/control/demo_state.json`

Operator and helper flows will use the managed-agent routes rather than bypassing them:

- launch via `POST /houmao/agents/headless/launches`
- kickoff via `POST /houmao/agents/{agent_ref}/requests`
- inspection via `GET /houmao/agents/{agent_ref}/state`, `/state/detail`, `/history`, and `/gateway`
- notifier pause and continue via `GET|PUT|DELETE /houmao/agents/{agent_ref}/gateway/mail-notifier`
- stop via `POST /houmao/agents/{agent_ref}/stop`

Headless turn linkage from `/requests` responses and `/turns/*` inspection will be used to build deterministic demo evidence without scraping terminal text.

Defaults such as server health-poll cadence, server health timeout, and free-port selection policy will live in the pack backing models and tracked input parameters, not as ad hoc constants hidden in shell code.

**Alternatives considered**

- Drive the demo through lower-level direct CLI or tmux control: rejected because the demo should teach the managed-agent surface rather than bypass it.
- Assume an ambient operator-owned `houmao-server`: rejected because the pack should own its lifecycle and artifacts.

### Decision: Make `<demo-home>/outputs/` the only generated-state root

The pack root will remain source-only. All generated state for a run will live under the selected output root. The default output root will be `scripts/demo/mail-ping-pong-gateway-demo-pack/outputs/`.

At minimum, the selected output root will contain:

- `control/`
- `server/`
- `runtime/`
- `registry/`
- `mailbox/`
- `jobs/`
- `projects/initiator/`
- `projects/responder/`

The pack will enforce this containment by exporting these overrides for every Houmao-owned subprocess:

- `AGENTSYS_GLOBAL_RUNTIME_DIR=<output-root>/runtime`
- `AGENTSYS_GLOBAL_REGISTRY_DIR=<output-root>/registry`
- `AGENTSYS_GLOBAL_MAILBOX_DIR=<output-root>/mailbox`
- `AGENTSYS_LOCAL_JOBS_DIR=<output-root>/jobs`

The demo-owned server directory will hold server logs, ownership metadata, and the server-private runtime root used by `houmao-server serve`. The operational rule is simple: if a file was generated by the demo run, it must be discoverable somewhere under `<output-root>/`.

**Alternatives considered**

- Keep only reports under `outputs/` and let Houmao write runtime state to the operator defaults: rejected because it breaks inspectability and cleanup ownership.
- Reuse `<project>/.houmao/jobs/` default derivation: rejected because the user explicitly wants one output-root ownership model for the demo.

### Decision: Define one explicit thread-key and kickoff contract

The default walkthrough will use two logical roles:

- `initiator`
- `responder`

Before kickoff, the pack will generate one run-specific thread key and persist it in `demo_state.json`. The thread key will be human-readable and stable for the run, for example `mail-ping-pong-<utc-stamp>-<short-hex>`.

The kickoff prompt submitted to the initiator will include, at minimum:

- the thread key
- the configured round limit
- the responder mailbox identity to target
- the subject template for outgoing messages
- the rule that every outgoing message must carry the thread key and current round number in visible message content
- the rule that the responder replies through the mailbox reply primitive in the same thread
- the rule that the initiator stops after reading reply `N`, where `N` is the round limit

The default message convention will be:

- subject prefix contains the thread key and round number
- body contains the thread key, round number, and the bounded request text

The real mailbox `thread_id` remains the transport truth for reply ancestry, but the explicit thread key makes run-owned inspection and verification unambiguous even before every message is reopened from disk.

Conversation semantics:

1. The operator or automatic flow sends one kickoff prompt to the initiator.
2. The initiator sends round 1 mail to the responder and ends its turn.
3. The responder later wakes because unread mail is actionable, reads the thread, replies in the same thread, and ends its turn.
4. The initiator later wakes because the reply is actionable, reads the reply, and either sends the next round or stops if the configured limit has been reached.

For round limit `N`, success is defined by:

- `2 * N` total sent messages
- `2 * N + 1` completed turns
- one stable thread identity across the whole exchange

For the default `N = 5`, the pack must observe `10` messages and `11` turns. The extra final initiator turn is required because the initiator must wake one last time to read reply 5 and decide not to send round 6.

The pack will submit only the kickoff prompt directly. Any later prompt or turn creation must come from gateway wake-up behavior rather than from the operator issuing direct prompts after each message.

**Alternatives considered**

- Hard-chain both sides by direct prompt submission after every message: rejected because it teaches the wrong turn model.
- Declare success after 10 messages only: rejected because it misses the final initiator stop decision turn.

### Decision: Persist one minimal field contract for demo-owned artifacts, with concrete models in code

The design will define the minimum required fields for the stable demo-owned artifacts, while the concrete Pydantic models will still live in `models.py`.

`control/demo_state.json` must persist enough to let `inspect`, `pause`, `continue`, `wait`, `verify`, and `stop` target the same live run. At minimum it will contain:

- `output_root`
- `agent_def_dir`
- `api_base_url`
- `mailbox_root`
- `thread_key`
- `round_limit`
- `wait_defaults` with bounded poll and timeout settings
- `server` ownership and artifact references needed for teardown and diagnostics
- `initiator` and `responder` records with at least:
  - `tracked_agent_id`
  - `tool`
  - `role_name`
  - `working_directory`
  - `brain_recipe_path`
  - `brain_manifest_path`

`conversation_events.jsonl` will use one normalized event shape. Every record must contain:

- `event_type`
- `observed_at_utc`
- `agent_role`
- `tracked_agent_id`
- `thread_key`
- `round_index`

and may additionally carry any available `request_id`, `headless_turn_id`, `message_id`, `thread_id`, `gateway_request_id`, or `detail`.

`inspect.json` will contain:

- `snapshot_at_utc`
- demo-state summary
- per-participant managed state and gateway status snapshots
- progress summary
- recent normalized events

`report.json` and `report.sanitized.json` will contain the same logical sections:

- configuration summary
- outcome summary
- message, turn, and round counts
- thread identity summary
- per-role outcome summary
- gateway evidence summary
- mailbox evidence summary
- artifact references

The sanitized form will mask paths, timestamps, runtime ids, request ids, turn ids, and message ids while preserving the stable outcome structure.

This field contract is intentionally minimal. The code models may contain more fields, but they may not omit these required resumability and verification fields.

**Alternatives considered**

- Leave schemas entirely to implementation: rejected because the spec already treats these files as stable interfaces.
- Put full JSON-schema or full Pydantic dumps into the design: rejected because that would over-prescribe the implementation and diverge from existing demo-pack practice.

### Decision: Expose both automatic and stepwise control with bounded wait semantics

The runner will expose these commands:

- `auto`
- `start`
- `kickoff`
- `wait`
- `inspect`
- `pause`
- `continue`
- `verify`
- `stop`

`start` will provision the output tree, copied projects, server, brains, agents, gateways, and notifier settings. `kickoff` will submit the one direct request. `pause` will disable notifier progression without stopping the agents. `continue` will restore notifier operation. `inspect`, `verify`, and `stop` will all reuse the persisted state in `outputs/control/demo_state.json`.

`wait` is an operator-facing command, so it cannot be open-ended. It will:

- poll on a bounded cadence using tracked defaults from the backing models and input parameters
- emit visible progress about completed rounds and current participant posture
- exit successfully when the configured success contract is satisfied
- exit non-zero with an explicit incomplete reason when the timeout expires
- preserve artifacts so the operator can still run `inspect` and `verify` on the incomplete run

This split keeps the automatic path simple while still giving maintainers an inspectable live state machine.

**Alternatives considered**

- Expose only a one-shot `auto` flow: rejected because the issue explicitly asks for stepwise inspection and control.
- Expose manual “send arbitrary mail” commands in v1: rejected because the first pack contract is about one reproducible canonical conversation, not a mailbox playground.

### Decision: Verify normalized conversation facts rather than exact notifier poll traces

Gateway notifier behavior is unread-set based and may deduplicate or summarize work across poll cycles. The pack will therefore build its golden report from normalized facts rather than exact per-poll row counts.

The evidence model will combine:

- kickoff request results
- headless turn ids and durable turn state
- managed-agent summary and detail state
- gateway status and notifier status
- gateway audit evidence from the live gateway root
- mailbox thread and message metadata under the shared mailbox root
- the normalized `conversation_events.jsonl` stream owned by the pack

The normalized event stream will include records such as:

- `kickoff_accepted`
- `mail_sent`
- `mail_reply_sent`
- `gateway_enqueued`
- `gateway_skipped`
- `turn_completed`
- `conversation_completed`
- `conversation_incomplete`

`verify` will assert stable outcomes such as thread continuity, total message count, total turn count, later-turn wake-up evidence, and final unread posture. It will explicitly avoid requiring an exact number or ordering of empty notifier polls.

**Alternatives considered**

- Compare raw queue and audit rows exactly: rejected because valid runs may differ in poll cadence and deduplication details.
- Rely on terminal text or transcript scraping: rejected because the managed headless turn and gateway artifacts are the stronger authority.

### Decision: Keep operator-facing artifact names transport-neutral, but make v1 collectors explicitly headless-only

The report schema, role names, command names, and conversation event vocabulary will avoid headless-specific labels where transport-neutral language is sufficient. That keeps room for future TUI or mixed-mode extension of the same pack.

However, the collectors used in v1 are intentionally headless-specific:

- `/turns/*` is the durable turn authority
- `headless_turn_id` is part of the normalized linkage when available
- managed headless request responses are the source of created-turn linkage

The design will therefore treat transport-neutral artifact names and headless-only evidence collectors as two separate concerns. Unsupported transport selections will fail fast with a clear message rather than silently degrading.

**Alternatives considered**

- Implement the full headless/TUI/mixed matrix now: rejected because the current repository support is not equally mature across those pairings.
- Make every artifact headless-specific: rejected because it would make a future transport expansion more expensive than necessary.

### Decision: Keep v1 regression coverage pytest-based and explicitly defer pack-local live-agent autotest

This change will add pytest-based regression coverage for the demo pack contract, including:

- startup defaults
- output-root containment
- persisted-state resumability
- pause and continue behavior
- successful completion and report sanitization
- timeout and incomplete-run diagnostics

This change will not add a pack-local live-agent `autotest/` harness. If the operator contract stabilizes and there is later demand for a maintained HTT path, that can be proposed in a follow-on change.

**Alternatives considered**

- Add a live-agent autotest harness immediately: rejected because it increases scope before the core pack contract has been exercised through normal pytest coverage.

## Risks / Trade-offs

- [Gateway notifier deduplicates unread-set activity] → Mitigation: verify causal outcome summaries and thread progression instead of exact poll counts.
- [The final initiator stop turn is easy to omit] → Mitigation: define success as `2N + 1` completed turns and require an explicit completion event for the stop decision.
- [State from previous runs could contaminate mailbox or registry evidence] → Mitigation: use one unique output root per live run and stamp a run-specific thread key into the conversation.
- [Cleanup may leave live server or agent processes behind after failure] → Mitigation: persist ownership state in `demo_state.json` and make `stop` idempotent across partial runs.
- [Role packages could drift away from the runtime-owned mailbox skill contract] → Mitigation: keep role text focused on thread and round policy and rely on the runtime-owned mailbox skill for the actual mailbox procedure guidance.
- [Future mixed/TUI support may need different wake-up evidence or control paths] → Mitigation: keep operator-facing artifact names transport-neutral while treating v1 collectors as headless-only.

## Migration Plan

This change adds a new standalone demo pack and does not replace an existing public workflow.

Implementation order:

1. Add the new pack directory, thin wrapper, backing module, and tracked fixture wiring.
2. Add demo-owned server startup, brain build, managed headless launch, gateway attach, and notifier control.
3. Add kickoff, bounded wait, event capture, inspect, and report generation.
4. Add pytest-based coverage and documentation.

Rollback is low risk because the change is additive. Reverting the pack removes the new workflow without requiring data migration or compatibility shims for existing packs.

## Open Questions

- None for v1. A pack-local live-agent `autotest/` harness is explicitly deferred to a follow-on change.

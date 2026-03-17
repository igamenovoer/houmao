## Context

The mailbox tutorial pack currently builds a reusable `DemoLayout` rooted at a caller-selected `--demo-output-dir`, with a default under `tmp/demo/mailbox-roundtrip-tutorial-pack`. That layout puts:

- the shared mailbox root at `<demo-output-dir>/shared-mailbox`,
- copied tracked inputs at `<demo-output-dir>/inputs`,
- runtime and CAO state under `<demo-output-dir>/runtime` and `<demo-output-dir>/cao`, and
- control artifacts such as `mail_send.json`, `mail_reply.json`, `demo_state.json`, and `report.json` directly under `<demo-output-dir>/`.

The current roundtrip flow also still treats the reply as deterministic tracked content: `roundtrip_demo()` passes `inputs/reply_message.md` directly to `mail reply --body-file`, and verification compares the canonical reply body against that tracked Markdown. That leaves no clean place for a human-readable conversation log and makes the "agent reply" look more like a replay of canned content than an authored tutorial exchange.

The new requirement set changes both filesystem shape and conversational ownership:

- the canonical output root should be the pack-local `outputs/` directory,
- that directory is disposable and should be cleared on each full run,
- the mailbox root should move under `<output-root>/mailbox`,
- a semantic `chats.jsonl` should become a first-class generated output, and
- the receiver should author the final reply content while appending it directly through a structured pack-owned path instead of relying on transcript extraction.

## Goals / Non-Goals

**Goals**

- Make `scripts/demo/mailbox-roundtrip-tutorial-pack/outputs/` the canonical pack-local default output root.
- Treat that output root as disposable generated state and ignore it through a demo-local `.gitignore`.
- Keep stepwise automation viable while ensuring full-run automation always starts from a fresh output tree.
- Promote `outputs/mailbox/` and `outputs/chats.jsonl` to first-class maintainer inspection surfaces.
- Replace the canned tracked reply body with tracked reply-authoring instructions and a direct structured append path for the final reply event.

**Non-Goals**

- Preserving backward compatibility for the old `shared-mailbox/` and `reply_message.md` layout.
- Turning `chats.jsonl` into a raw CAO transcript archive.
- Solving every generic runtime mailbox logging use case in this proposal; this is specifically about the tutorial-pack contract.

## Decisions

### 1. The tutorial pack will use one disposable pack-local output root

The canonical output root becomes:

```text
scripts/demo/mailbox-roundtrip-tutorial-pack/outputs/
```

This directory is not a durable artifact store. Full-run automation (`run_demo.sh auto` and the default no-command invocation) will clear and reconstruct it from scratch before runtime work begins. That preserves the current "known clean run" property while moving the default output location into the pack itself.

Stepwise automation still needs reuse, so `start -> roundtrip -> verify -> stop` should continue operating on one prepared output root for the same run. The clearing rule therefore applies to full-run entrypoints, not to every stepwise command.

The pack directory should own a local `.gitignore` entry for `outputs/` so generated runs never look like tracked content.

Alternatives considered:

- Keep `tmp/demo/...` as the default output location and only add a convenience copy into the pack directory.
  Rejected because it duplicates artifacts and weakens the idea that the tutorial pack has one canonical human-inspection root.
- Clear `outputs/` before every `start`, `roundtrip`, `verify`, and `stop`.
  Rejected because it breaks the existing stepwise workflow contract.

### 2. The output-root layout should separate human-readable outputs from control artifacts

The output root should be documented around these first-class surfaces:

```text
<output-root>/
├── mailbox/
├── chats.jsonl
├── inputs/
├── control/
├── runtime/
├── project/
└── cao/
```

`mailbox/` and `chats.jsonl` are the maintainer-facing inspection surfaces. `control/`, `runtime/`, `project/`, and `cao/` remain generated orchestration state. Using a dedicated `control/` directory keeps the root from becoming a flat pile of JSON files.

Alternatives considered:

- Keep every JSON artifact at the top level and only rename `shared-mailbox/` to `mailbox/`.
  Rejected because the root is already crowded, and the new `chats.jsonl` deserves a clearer surrounding contract.

### 3. `chats.jsonl` will be a semantic event log, not a TUI transcript dump

Each line in `chats.jsonl` should be one JSON object with at least:

- `ts_utc`
- `from`
- `to`
- `content`

The implementation may also include `kind`, `message_id`, `thread_id`, or other stable fields that help correlate chat events with canonical mailbox state.

This log should record tutorial-relevant semantic events, not raw CAO screen output. In practice:

- controller/helper code can append controller-owned prompt or instruction events directly, and
- the receiver's final reply should be appended directly as structured content through a pack-owned append surface, instead of being scraped back out of the TUI transcript.

That keeps the log trustworthy and avoids fragile parser logic whose only purpose is to reconstruct a human-readable reply that the runtime already has in structured form.

Alternatives considered:

- Store the raw TUI transcript and derive the human-readable chat later.
  Rejected because the user requirement explicitly wants to avoid transcript extraction for the final reply.
- Ask the model itself to hand-write JSONL with no helper surface.
  Rejected because escaping, locking, and schema consistency should remain code-owned.

### 4. The tracked input contract should shift from canned reply text to reply-authoring instructions

The current tracked `reply_message.md` locks the tutorial into exact canned reply content. That is incompatible with the new requirement that the agent append the final reply as authored output.

The tracked input contract should instead distinguish:

- seed content for the initial send body, and
- tracked reply-authoring instructions that tell the receiver what kind of reply to produce and log.

This preserves tutorial determinism at the instruction level without pretending the final reply is a prewritten static artifact.

The natural consequence is that verification should stop requiring the final canonical reply body to equal a tracked reply-body file byte-for-byte. It should instead verify:

- mailbox threading correctness,
- presence and structure of the final canonical reply,
- presence and structure of the corresponding `chats.jsonl` event, and
- any tutorial-level response constraints that can be checked structurally rather than by exact text equality.

### 5. Verification and scenario automation should treat mailbox plus chat log as the primary outputs

The sanitized report contract can remain, but it should no longer be the only human inspection surface. Successful runs should leave two primary artifacts:

- canonical mailbox content under `<output-root>/mailbox/`, and
- semantic conversation events in `<output-root>/chats.jsonl`.

Scenario automation and live tests should validate both. The sanitized expected report should continue to avoid embedding raw message bodies or raw chat content.

## Risks / Trade-offs

- [Changing the default output root to a tracked-pack-local path could make accidental deletion feel riskier] -> Counter by making `outputs/` explicitly disposable in docs, tests, and `.gitignore`.
- [Moving from canned reply text to agent-authored replies reduces exact-text determinism] -> Keep determinism in the instruction contract and verify structure/threading instead of exact prose.
- [Direct append for the final reply needs a trusted write surface] -> Use a pack-owned helper or mailbox-adjacent append path rather than TUI scraping or model-owned JSONL formatting.
- [A `control/` subdirectory is a larger layout change than a simple rename] -> Accept the broader cleanup because the new output root is already a breaking layout revision.

## Migration Plan

1. Add the new output-root and chat-log capability contract.
2. Update the tutorial pack's default output-root layout and demo-local ignore rules.
3. Replace tracked canned reply content with tracked reply-authoring instructions.
4. Update live/unit/scenario verification to validate `mailbox/` plus `chats.jsonl`.
5. Refresh the tutorial README and expected-report assumptions around the new layout.

No data migration is needed because `outputs/` is explicitly disposable and full-run automation will recreate it from scratch.

## Open Questions

- Whether the CLI should keep the old `--demo-output-dir` flag as an override/alias or rename it to `--output-root`. The requirements in this change avoid forcing that naming decision yet.

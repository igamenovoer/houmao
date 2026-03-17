# mailbox-roundtrip-output-root-and-chat-log Specification

## Purpose
TBD - created by archiving change restructure-mailbox-tutorial-pack-output-root-and-chat-log. Update Purpose after archive.

## Requirements

### Requirement: Mailbox tutorial pack SHALL use a disposable pack-local output root

The mailbox roundtrip tutorial pack SHALL treat `scripts/demo/mailbox-roundtrip-tutorial-pack/outputs/` as its canonical default `<output-root>` for full tutorial-pack runs.

Full-run automation (`run_demo.sh auto` and the default no-command invocation) SHALL clear any existing `outputs/` directory and reconstruct it from scratch before runtime work starts. The tutorial pack SHALL not treat any existing content under `outputs/` as valuable state that must be preserved across full runs.

Stepwise automation MAY continue to reuse one already prepared `<output-root>` across `start`, `roundtrip`, `verify`, and `stop` for the same run.

The tutorial-pack directory SHALL include a demo-local `.gitignore` rule that ignores `outputs/`.

#### Scenario: Full run recreates the pack-local output root

- **WHEN** a maintainer runs the mailbox tutorial pack through `run_demo.sh auto` or the default no-command invocation
- **THEN** the pack clears any preexisting `scripts/demo/mailbox-roundtrip-tutorial-pack/outputs/` directory before runtime work begins
- **AND THEN** it reconstructs the output-root layout from scratch for the new run
- **AND THEN** the run does not depend on preserving older generated files under `outputs/`

#### Scenario: Stepwise commands reuse one prepared output root

- **WHEN** a maintainer runs `run_demo.sh start`, `roundtrip`, `verify`, and `stop` stepwise for the same tutorial-pack run
- **THEN** those commands reuse the same prepared `<output-root>` for that run
- **AND THEN** the pack does not clear that output root between those stepwise phases

### Requirement: Output root SHALL expose mailbox, chat log, copied inputs, and generated control state as distinct surfaces

The tutorial pack SHALL place the canonical filesystem mailbox root under `<output-root>/mailbox` and SHALL place the append-only semantic conversation log at `<output-root>/chats.jsonl`.

The pack SHALL also copy its tracked tutorial inputs under `<output-root>/inputs` and SHALL keep the remaining generated runtime, project, CAO, and control artifacts in documented locations under the same `<output-root>`.

#### Scenario: Maintainer can find the mailbox and chat log from the output root alone

- **WHEN** a maintainer inspects a successful tutorial-pack output root
- **THEN** the canonical mailbox content is available under `<output-root>/mailbox/`
- **AND THEN** the semantic chat log is available at `<output-root>/chats.jsonl`
- **AND THEN** copied tutorial inputs are available under `<output-root>/inputs/`

### Requirement: Tutorial pack SHALL record a semantic append-only chat log instead of reconstructing replies from TUI output

Each line in `<output-root>/chats.jsonl` SHALL be one JSON object containing at least:

- time,
- who sent the event,
- who received the event, and
- content.

The implementation SHALL expose those fields in a stable structured form such as `ts_utc`, `from`, `to`, and `content`.

The tutorial-pack automation SHALL record controller-owned prompt events directly. The receiver's final tutorial reply SHALL be appended directly as structured output through a pack-owned append surface instead of being recovered later by parsing CAO TUI transcript content.

#### Scenario: Chat log records prompt and reply events with stable metadata

- **WHEN** a successful tutorial-pack roundtrip finishes
- **THEN** `<output-root>/chats.jsonl` contains append-only structured events for the tutorial conversation
- **AND THEN** each event records at least time, sender, recipient, and content
- **AND THEN** the receiver's final reply event was appended directly rather than reconstructed from TUI transcript scraping

### Requirement: Tracked tutorial inputs SHALL distinguish seed message content from reply-authoring instructions

The tracked `inputs/` contract for the mailbox tutorial pack SHALL provide:

- seed content for the initial send body, and
- tracked instructions that tell the receiver how to author the reply.

The tutorial pack SHALL no longer depend on a canned tracked final-reply body file whose exact text must equal the final canonical reply content after a successful run.

#### Scenario: Inputs describe the conversation contract without hard-coding the final reply body

- **WHEN** a maintainer inspects the tracked tutorial-pack `inputs/` directory
- **THEN** it contains tracked content for the initial message body
- **AND THEN** it contains tracked instructions for authoring the receiver reply
- **AND THEN** the successful run contract does not require the final reply body to match a prewritten canned reply file exactly

### Requirement: Successful verification SHALL treat mailbox artifacts plus chat log as the primary human-readable outputs

The tutorial pack's live and scenario verification SHALL continue to validate canonical mailbox artifacts while also validating that `<output-root>/chats.jsonl` exists and records the expected semantic conversation events for a successful roundtrip.

Tracked sanitized verification snapshots SHALL continue to avoid embedding raw mailbox bodies or raw chat content.

#### Scenario: Verification preserves sanitized snapshots while checking mailbox and chat outputs

- **WHEN** a maintainer runs tutorial-pack verification after a successful roundtrip
- **THEN** verification checks canonical mailbox artifacts under `<output-root>/mailbox/`
- **AND THEN** verification checks the presence and structure of `<output-root>/chats.jsonl`
- **AND THEN** tracked sanitized report snapshots still exclude raw mailbox and chat body content

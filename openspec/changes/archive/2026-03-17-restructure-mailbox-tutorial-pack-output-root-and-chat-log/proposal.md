## Why

The mailbox roundtrip tutorial pack still thinks in terms of a generic demo-owned output directory, and it mixes mailbox content, copied inputs, runtime state, and control artifacts in one layout whose default home is outside the pack directory. That made sense when the pack was mostly about reproducible step outputs, but it is awkward for the next requirement set:

- maintainers want one canonical pack-local disposable output root under `scripts/demo/mailbox-roundtrip-tutorial-pack/outputs/`,
- the mailbox root should live at `<output-root>/mailbox`,
- the run should leave behind a human-readable `chats.jsonl`,
- the receiver's final reply should be logged directly rather than reconstructed from CAO TUI output, and
- the pack's tracked inputs should describe the conversation shape instead of hard-coding a canned final reply body.

There is also an ownership question: if `outputs/` becomes the canonical pack-local output root, it should be treated as disposable automation state, not as something maintainers curate by hand or accidentally commit.

## What Changes

- Define `scripts/demo/mailbox-roundtrip-tutorial-pack/outputs/` as the canonical default `<output-root>` for full tutorial-pack runs.
- Require full-run automation (`auto` and the default no-command invocation) to clear and reconstruct `outputs/` from scratch before work starts, while leaving stepwise command reuse available for the same prepared output root.
- Move the canonical mailbox root to `<output-root>/mailbox` and document the rest of the output-root layout around mailbox, copied inputs, runtime/control artifacts, and the new chat log.
- Add a semantic append-only `chats.jsonl` contract whose lines record at least time, sender, recipient, and content.
- Require the receiver's final tutorial reply to be appended directly as structured output through a pack-owned append surface instead of being parsed back out of the CAO TUI transcript.
- Update the tracked `inputs/` contract so the tutorial owns seed message content plus reply-authoring instructions, rather than a canned final reply body that must match exactly.
- Require a demo-local `.gitignore` in the tutorial-pack directory to ignore `outputs/`.

## Capabilities

### New Capabilities

- `mailbox-roundtrip-output-root-and-chat-log`: Defines the pack-local disposable output-root layout, the semantic chat-log contract, and the shift from canned reply bodies to agent-authored reply logging for the mailbox tutorial pack.

### Modified Capabilities

<!-- None. -->

## Impact

- Affected code: `scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh`, `scripts/demo/mailbox-roundtrip-tutorial-pack/scripts/tutorial_pack_helpers.py`, `scripts/demo/mailbox-roundtrip-tutorial-pack/README.md`, `scripts/demo/mailbox-roundtrip-tutorial-pack/inputs/*`, scenario automation, and the live/unit tutorial-pack tests.
- Affected systems: tutorial-pack output-root layout, mailbox content inspection, report verification, pack-local ignored files, and the runtime-owned mail prompt/reply path used by the tutorial pack.
- Affected workflow: maintainers will treat `scripts/demo/mailbox-roundtrip-tutorial-pack/outputs/` as disposable generated state, inspect canonical mailbox content under `outputs/mailbox/`, and inspect semantic conversation events under `outputs/chats.jsonl`.

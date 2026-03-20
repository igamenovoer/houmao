# Claude Code Activity State Signals

## Context

- Observed on 2026-03-20 in tmux session `gig-3`
- Tool: Claude Code
- Command-reported version: `claude --version` -> `2.1.80 (Claude Code)`
- Visible UI banner version during observation: `v2.1.80`
- Primary recording artifacts:
  - `/data1/huangzhe/code/houmao/tmp/terminal_record/gig-3-20260320T041035Z/pane_snapshots.ndjson`
  - `/data1/huangzhe/code/houmao/tmp/terminal_record/gig-3-20260320T041035Z/parser_observed.ndjson`
  - `/data1/huangzhe/code/houmao/tmp/terminal_record/gig-3-20260320T041035Z/state_observed.ndjson`
- Intent: define Claude-specific activity patterns for `turn_active` and successful return to `turn_ready`, independent of the current buggy implementation

## Observed Sequence

The recorded turn behaved like this:

1. Older interrupted history remained visible in scrollback from a previous attempt
2. Claude started a new turn and displayed a live thinking line: `Cerebrating…`
3. Claude then displayed both tool activity and thinking:
   - `Fetch(https://huggingface.co/papers)`
   - `⎿  Fetching…`
   - `Cerebrating…`
4. During that active turn, the operator typed `/`, which opened the slash-command menu overlay
5. Claude began rendering the answer while the slash menu was still briefly visible
6. Claude later showed `Worked for 35s`
7. The pane returned to a fresh `❯` prompt

This means the real Claude process sequence was:

```text
stale historical interruption in scrollback
-> active thinking
-> active tool + thinking
-> active answer generation
-> success
-> ready
```

The stale interruption line was not the current state of the new turn.

## State: `turn_active`

### Classification

When the active-turn signal matches, the tracked current turn state is:

- current posture: `turn_active`

### Sufficient Evidence

Any one of the signal groups below is sufficient to classify the current turn as `turn_active`.

#### A. Thinking line plus interruptable footer

All of the following are true in the same current surface:

1. A visible Claude activity line contains a live thinking verb such as `Cerebrating…`
2. That activity line is visually current, not stale scrollback
3. The bottom status/footer shows `esc to interrupt`

Observed examples from the recording:

- `s000114` at `24.964555s`
- `s000192` at `41.287237s`

Representative surface:

```text
❯ find me the top 10 paper of trending paper of hf tody, tell me what they are about

✢ Cerebrating…

────────────────────────────────────────────────────────────────────────────────
❯
────────────────────────────────────────────────────────────────────────────────
  ⏵⏵ bypass permissions on (shift+tab to cycle) · esc to interrupt
```

#### B. Tool activity plus interruptable footer

All of the following are true in the same current surface:

1. A visible tool block is present, such as `Fetch(...)`
2. The tool continuation/status line shows an in-flight activity text such as `Fetching…`
3. The bottom status/footer shows `esc to interrupt`

Observed example from the recording:

- `s000138` at `29.994988s`

Representative surface:

```text
❯ find me the top 10 paper of trending paper of hf tody, tell me what they are about

● Fetch(https://huggingface.co/papers)
  ⎿  Fetching…

✻ Cerebrating… (thought for 1s)

────────────────────────────────────────────────────────────────────────────────
❯
────────────────────────────────────────────────────────────────────────────────
  ⏵⏵ bypass permissions on (shift+tab to cycle) · esc to interrupt
```

#### C. Answer growth while the turn is still interruptable

All of the following are true in the same current surface:

1. The latest Claude answer content is visibly appearing in the transcript
2. The bottom status/footer still shows `esc to interrupt`
3. The surface has not yet transitioned to a completed marker such as `Worked for <duration>`

Observed example from the recording:

- `s000228` at `48.880903s`

Representative surface:

```text
● Here are today's top 10 trending papers on Hugging Face (March 20, 2026):

  ---

  1. Generation Models Know Space (45 upvotes) — H-EmbodVis

────────────────────────────────────────────────────────────────────────────────
❯
────────────────────────────────────────────────────────────────────────────────
  ⏵⏵ bypass permissions on (shift+tab to cycle) · esc to interrupt
```

### Overlay Rule

A slash-command suggestion menu opened by typing `/` during an already-active Claude turn does NOT negate `turn_active` by itself.

If current active-turn evidence remains visible at the same time as the slash menu, the classification remains:

- current posture: `turn_active`

Observed examples:

- `s000211` at `45.283971s`
- `s000212` at `45.494482s`
- `s000227` at `48.670062s`

Representative surface:

```text
✻ Cerebrating… (thought for 1s)

────────────────────────────────────────────────────────────────────────────────
❯ /
────────────────────────────────────────────────────────────────────────────────
  /openspec-apply-change
  /openspec-explore
  /openspec-propose
```

Interpretation:

- the `/...` menu is an overlay caused by local prompt editing
- it does not prove a slash command is actually being executed
- it does not cancel the already-visible active Claude turn

## State: `turn_ready` with `last_turn=success`

### Classification

When the successful-return signal matches, the tracked states are:

- current posture: `turn_ready`
- last turn outcome: `success`

### Required Conditions

All conditions below MUST be true in the same current surface:

1. The latest Claude answer content is present in the transcript
2. A completion marker of the form `Worked for <duration>` is visible
3. A fresh `❯` input prompt is visible
4. No current known error signal is present for the latest turn
5. The current visible TUI has remained stable for a short settle window such as `1s`
6. That stability check applies to the whole relevant visible state, not only the answer area; it also includes volatile activity markers such as the spinning/thinking symbol line and other current-state indicators

Interpretation:

- `turn_success` is not emitted the instant answer text first appears
- `turn_success` is emitted only after the answer-bearing surface has settled, no current known error pattern is present for the latest turn, and the current visible TUI stops changing for the settle window
- the settle window must be based on the current visible surface, not just the answer body, so a still-changing spinner/thinking line keeps the turn out of success
- stale error or interruption lines from previous chats that remain in scrollback do not block success for the latest turn by themselves

Observed example from the recording:

- `s000363` at `77.477368s`

Representative surface:

```text
● Here are today's top 10 trending papers on Hugging Face (March 20, 2026):
  ...

✻ Worked for 35s

────────────────────────────────────────────────────────────────────────────────
❯
────────────────────────────────────────────────────────────────────────────────
  ⏵⏵ bypass permissions on (shift+tab to cycle)
```

## Non-Match Guidance

- Do not classify `turn_active` from stale historical lines alone
- Do not classify `turn_active` from a slash-menu overlay alone
- Do not classify `turn_active` from `/...` text at the prompt alone
- Do not classify `turn_ready` with `last_turn=success` if a current known error signal for the latest turn is present
- Do not block `turn_ready` with `last_turn=success` merely because an older error from a previous chat remains visible in scrollback
- Do not classify `turn_ready` with `last_turn=success` until the whole relevant visible TUI has stayed stable for the settle window
- Do not classify current interruption or failure from older interrupted/error transcript lines that remain visible in scrollback after a later turn has begun
- Do not let a slash-menu overlay override stronger current active-turn evidence that is still visible on screen
- Do not require any one single spinner glyph shape; the observed activity line varied across glyphs such as `✢`, `✻`, `✽`, and `*`

## Current Design Implications

- Claude activity detection must be based on the current visible region, not naive substring matching over the full scrollback
- Stale transcript content can remain on screen for a long time and MUST NOT dominate current-state classification
- Slash-like prompt text is not a reliable semantic discriminator
- Tool activity lines, thinking lines, answer growth, and completion markers are stronger state signals than slash-menu overlays

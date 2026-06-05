## 1. Claude Prompt Classification

- [x] 1.1 Extend Claude prompt payload style extraction to retain the prompt payload's meaningful foreground/style facts needed to recognize darker ghost-suggestion rendering.
- [x] 1.2 Update the Claude Code `2.1.x` prompt behavior variant so a wholly ghost-styled payload classifies as placeholder or suggestion content without checking exact payload text.
- [x] 1.3 Preserve conservative draft behavior for ordinary typed payloads, mixed typed-prefix plus suggestion-suffix payloads, and unrecognized non-empty prompt styling.

## 2. Tracked State and Notifier Behavior

- [x] 2.1 Add Claude prompt-behavior unit fixtures for arbitrary darker suggestion text, changed suggestion wording, mixed typed/suggestion styling, and unrecognized styling.
- [x] 2.2 Add shared tracked-state coverage showing style-classified Claude suggestions produce `editing_input=no`, ready posture, and a ready turn when no active evidence is present.
- [x] 2.3 Add gateway mail notifier coverage showing notifier work can enqueue over a style-classified Claude suggestion but still defers over real draft editing.

## 3. Verification

- [x] 3.1 Run the focused shared TUI tracking and gateway notifier tests that cover the new behavior.
- [ ] 3.2 Run `pixi run test` or the broadest practical unit-test target before marking the change complete.

## Why

The managed prompt header gained a five-section architecture with per-section policy control (`identity`, `houmao-runtime-guidance`, `automation-notice`, `task-reminder`, `mail-ack`). The six docs pages that cover the feature in detail have already been updated in the working tree, but the two highest-visibility entry points — README.md (line 349) and docs/index.md (line 46) — still describe the header as a monolithic block. The README also omits the default-on `automation-notice` behavior (prohibits `AskUserQuestion`, routes mailbox-driven clarification), which is the most operationally impactful section. Fixing these two callouts completes the docs surface for the section-level feature.

## What Changes

- **README.md line 349**: Rewrite the `> **Managed prompt header.**` callout to describe the five sections, their defaults (three on, two off), the `--managed-header-section` per-launch override, and the `--no-managed-header` whole-header opt-out.
- **docs/index.md line 46**: Update the Managed Launch Prompt Header index entry to mention per-section control alongside the existing composition/opt-out description.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `readme-structure`: The README managed-header callout block within step 5 / `agents join` section now describes the five-section architecture and per-section CLI surface instead of treating the header as monolithic.
- `docs-managed-launch-prompt-header-reference`: The docs index entry for this reference page now mentions per-section control in its one-line description.

## Impact

- **README.md** — one blockquote paragraph rewritten (~3 sentences).
- **docs/index.md** — one bullet description reworded (~10 words changed).
- No code, no tests, no API changes.

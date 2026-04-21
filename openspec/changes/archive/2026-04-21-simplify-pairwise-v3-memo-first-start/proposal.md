## Why

`houmao-agent-loop-pairwise-v3` currently inherits the heavier pairwise-v2 prestart and start contract: `initialize` writes durable initialize pages plus memo pointers, and `start` writes a durable start charter and waits for explicit `accepted` or `rejected` from the master. For workspace-aware pairwise runs, that ceremony is more complex than needed and duplicates control material across pages, memo blocks, and live triggers.

The v3 surface should instead make memo materialization the canonical prestart handoff. That keeps the per-agent working contract in the place agents already consult during work, and lets `start` become a small fire-and-go trigger instead of a second acceptance gate.

## What Changes

- **BREAKING** Change pairwise-v3 `initialize` from page-backed preparation to memo-first preparation that writes organization rules, workspace posture, goals, and local obligations directly into the related agents' memo surfaces.
- Change pairwise-v3 `initialize` so it may launch missing participants from provided launch profiles before mail-capability checks and memo materialization.
- **BREAKING** Change pairwise-v3 `start` from an acceptance-gated charter handoff to a compact trigger that tells the designated master to read its memo and begin work.
- Change pairwise-v3 ordinary `start` so the kickoff is sent via mail by default rather than direct prompt, unless the user explicitly requests direct prompt delivery.
- **BREAKING** Require pairwise-v3 to fail closed when any required participant lacks email/mailbox support, instead of trying to proceed without the default in-loop communication channel.
- Remove the pairwise-v3 requirement to create or refresh a durable `start-charter` page before `start`.
- Remove the pairwise-v3 requirement for explicit `accepted` or `rejected` replies during ordinary `start`.
- Narrow the meaning of `initialize` so it owns durable participant guidance materialization and preflight validation, while `start` only kicks off execution after `initialize` is complete.
- Update the authored plan, templates, and docs so pairwise-v3 records memo-slot expectations and memo-first lifecycle vocabulary instead of start-charter-first language.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-agent-loop-pairwise-v3-skill`: change v3 initialize/start requirements to use memo-first participant guidance, drop the durable start-charter requirement for ordinary start, and remove explicit start-time `accepted` or `rejected` replies.

## Impact

- Affected skill assets under `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v3/`, especially `SKILL.md`, authoring templates, prestart guidance, start guidance, and charter references.
- Affected documentation under `docs/getting-started/` and any reference pages that describe pairwise-v3 as inheriting the pairwise-v2 start handshake.
- Affected OpenSpec main spec `openspec/specs/houmao-agent-loop-pairwise-v3-skill/spec.md`.
- Operators using the current v3 `start` contract will need to adopt the new memo-first initialize flow and no longer expect `accepted` or `rejected` responses from ordinary `start`.

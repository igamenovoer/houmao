## Context

The archived `fix-shadow-mailbox-sentinel-completion-gating` change already added mailbox-specific provisional completion for `shadow_only` turns, but the current implementation still uses a loose presence check when deciding whether a shadow surface has reached the mailbox result contract. In practice, a runtime-owned mailbox prompt can echo the sentinel names inside ordinary prose and again inside the appended `response_contract` JSON fields before any real mailbox result block is emitted.

That creates a mismatch between the provisional gate and the final parser. The provisional gate can treat an echoed surface as "contract reached" because it only sees `BEGIN` followed later by `END`, while the exact parser then rejects the same surface because it contains multiple sentinel-name occurrences rather than one actual sentinel-delimited result block.

Constraints:

- Keep the generic shadow turn monitor unchanged for non-mail turns.
- Preserve the existing mailbox prompt contract and sentinel names.
- Preserve explicit mailbox parse failures for real malformed mailbox result blocks.
- Avoid fragile TUI-specific cleanup rules that depend on exact projection fidelity.

## Goals / Non-Goals

**Goals:**

- Prevent prompt-echo sentinel mentions from satisfying mailbox-specific shadow completion gating.
- Make mailbox provisional completion and final mailbox parsing rely on the same exact active-request contract.
- Preserve explicit parse failures for real malformed or duplicated mailbox result blocks.
- Add regression coverage for the prompt-echo false positive.

**Non-Goals:**

- Redesign the mailbox prompt format or rename the sentinels.
- Add automatic retry prompts for malformed mailbox output.
- Change generic `shadow_only` completion behavior for non-mail turns.
- Introduce a new mailbox timeout separate from the existing turn timeout/stall policy.

## Decisions

### 1. Use standalone sentinel-block extraction instead of raw substring presence

Mailbox result detection will stop treating arbitrary `AGENTSYS_MAIL_RESULT_BEGIN` and `AGENTSYS_MAIL_RESULT_END` substrings as sufficient evidence. Instead, mailbox extraction will identify candidate result blocks only when the sentinels appear as standalone delimiter lines around a payload block, matching the documented mailbox result contract and the existing unit-test fixtures.

Rationale:

- Prompt echo currently repeats sentinel names in prose and in JSON string values, but those mentions are not actual delimiter lines.
- The real mailbox contract already models result emission as:
  - one `BEGIN` line
  - one JSON object payload
  - one `END` line
- A standalone-block extractor lets the runtime ignore prompt echo while still recognizing true result blocks in noisy shadow output.

Alternatives considered:

- Tighten the existing whole-surface count check. Rejected because a full shadow surface can still legitimately contain echoed prompt text plus a valid later result block.
- Remove sentinel names from the mailbox request prompt. Rejected because the prompt needs to state the response contract explicitly, and changing that contract would widen scope unnecessarily.
- Depend on more aggressive baseline trimming only. Rejected because shadow projection fidelity is intentionally best-effort and should not be the correctness boundary.

### 2. Share one mailbox result selection path between provisional gating and final parsing

The mailbox completion observer and the final `parse_mail_result()` path will use the same extracted-block selection logic. The shared selector will:

- scan ordered candidate surfaces,
- extract standalone sentinel-delimited blocks,
- ignore surfaces that contain only prompt-echo sentinel mentions and no actual blocks,
- require exactly one valid active-request mailbox result block before treating completion as satisfied, and
- preserve explicit parse failures when one or more real standalone result blocks are malformed, duplicated, or mismatch the active request/binding contract.

Rationale:

- The current bug exists because the observer and the parser answer different questions with different rules.
- A shared selector keeps "not yet present", "valid result present", and "malformed result present" aligned across both phases.

Alternatives considered:

- Let the observer stay loose and only harden the final parser. Rejected because that recreates the current mismatch and still allows premature completion.
- Let the observer fully parse the result and bypass `parse_mail_result()` entirely. Rejected because that would duplicate responsibility and make event-surface parsing less consistent for callers.

### 3. Keep bounded failure behavior unchanged

Mailbox-specific completion will continue using the existing generic timeout, blocked-surface, unsupported-surface, disconnect, and stall policies. The fix only changes what counts as mailbox-result evidence during provisional shadow completion and mailbox parsing.

Rationale:

- The bug is false-positive contract detection, not inadequate timeout policy.
- Reusing the existing bounded failure policy keeps risk localized and preserves current operator expectations.

Alternatives considered:

- Add a mailbox-only timeout or retry layer. Rejected because it would mask the real contract-detection problem and complicate diagnosis.

### 4. Add regression coverage at both the parser and runtime-completion layers

Coverage will include:

- unit tests for prompt-echo text that mentions sentinel names without emitting a real standalone result block,
- unit/integration tests showing that a real standalone result block still completes and parses correctly after prompt echo, and
- regression coverage for malformed standalone blocks so the runtime still fails explicitly instead of timing out silently.

Rationale:

- The failure spans both mailbox extraction and shadow completion behavior.
- We need to lock in the difference between "echo noise" and "actual malformed result".

## Risks / Trade-offs

- [Standalone delimiter detection assumes the mailbox contract keeps sentinels on their own logical lines] -> This matches the documented protocol and existing tests; if the contract changes later, the extractor can evolve intentionally instead of relying on accidental substring matches.
- [A projection may split or normalize line boundaries differently across providers] -> Prefer the existing ordered shadow surfaces and keep the extractor tolerant of surrounding TUI noise while still requiring delimiter-line structure.
- [Sharing one selector across provisional gating and final parsing couples those two paths more tightly] -> This is intentional; the current bug comes from those paths diverging.
- [A real malformed standalone result might now fail earlier and more consistently] -> Keep the error surface explicit and covered by regression tests so operators see a deterministic mailbox parse failure instead of a misleading provisional success.

## Migration Plan

No data migration is required.

Implementation rollout:

1. Introduce shared standalone sentinel-block extraction and active-request result selection for mailbox surfaces.
2. Switch mailbox-specific shadow completion gating to that shared selector.
3. Update final mailbox parsing to consume the same selector so prompt echo outside standalone blocks is ignored.
4. Add regression coverage for prompt echo, valid delayed result, and malformed standalone result cases.

Rollback strategy:

- Revert the shared selector and mailbox observer/parser wiring changes together.
- Leave the rest of the shadow turn monitor untouched.

## Open Questions

- None that block the proposal. The main implementation choice is whether the shared selector returns a parsed payload directly or returns a validated source block plus metadata for `parse_mail_result()` to consume, but either shape satisfies this design as long as observer and parser use the same contract.

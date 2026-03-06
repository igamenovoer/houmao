## Context

This repo already includes runtime-owned shadow parsing for CAO-backed sessions:

- `backend=cao_rest` supports two parsing modes:
  - `cao_only`: gate completion via CAO terminal status and extract via `output?mode=last`.
  - `shadow_only`: gate completion via runtime shadow parsing over `output?mode=full` and extract via a runtime shadow parser.
- Shadow parsers exist today for:
  - Codex: `CodexShadowParser` (strict `codex_shadow_v1` format detection).
  - Claude Code: `ClaudeCodeShadowParser` (version presets via banner/env override, but no explicit output-format contract).

These parsers are useful, but they are not yet a robust, versioned superset of upstream CAO provider parser behavior:

- Codex: current shadow parser expects a banner + marker/prompt shape and does not cover several known variants (label-style fixtures, approval prompts, footer chrome).
- Claude Code: preset “floor” behavior can silently accept unknown versions, and totally drifted output can degrade into “processing until timeout” rather than an explicit unknown-format result.
- Gemini: runtime primarily uses headless JSON output, not TUI scraping. Gemini parser architecture (including any future TUI/CAO transport design) is deferred to a separate feature request; this change keeps existing Gemini headless behavior unchanged.

The feature goal is to build a first-class, version-aware shadow parser stack for `codex` and `claude` that:

1. Is a functional superset of upstream CAO parser capabilities for supported variants.
2. Separates generic parsing logic from version-specific rules.
3. Detects unknown/unsupported variants explicitly with actionable diagnostics.
4. Becomes the preferred/default runtime parsing path after rollout (keeping CAO-native parsing as an explicit fallback configuration).

## Goals / Non-Goals

**Goals:**

- Define a single runtime-owned shadow parsing contract that can be implemented by CAO/TUI providers and multiple preset versions.
- Implement version-aware dispatch:
  - Use explicit version detection when available (banner/env override).
  - Fall back to a floor preset only with explicit “unknown version” anomaly reporting.
- Ensure “unknown format” is explicit:
  - No more “treat unrecognized output as processing forever”.
  - Failure messages must include an ANSI-stripped excerpt and reason codes suitable for debugging.
- Expand Codex and Claude shadow parsing so it is parity-or-better vs upstream CAO provider parsers for supported variants.
- Add a fixture-driven unit test matrix for known-good variants and intentionally drifted variants.
- Update runtime defaults and docs so shadow parsing is the preferred path after parity is achieved (especially for Codex CAO-backed sessions).

**Non-Goals:**

- Modifying or depending on upstream CAO internal parser code at runtime (it remains reference material only).
- Mixing parser families within a single turn (no in-turn fallback from shadow to CAO-native parsing).
- Building a Gemini TUI scraping flow in this change.
- Refactoring or extending Gemini headless parser behavior in this change (it remains as-is).

## Decisions

- Introduce a provider-agnostic shadow parsing core with explicit contracts.
  - Rationale: keeps baseline handling, normalization, diagnostics, and status semantics consistent across tools.
  - Alternative: keep per-provider ad hoc parser classes and evolve them independently. Rejected because it increases drift risk and makes it hard to enforce explicit unknown-format behavior consistently.

- Use versioned parsing profiles as the unit of provider/version-specific behavior.
  - TUI profiles (Codex/Claude) define:
    - output-format probing/detection,
    - status classification (including waiting-user-answer),
    - baseline capture semantics, and
    - extraction stop boundaries.
  - Rationale: adding or changing an upstream variant becomes additive (new profile + registration) rather than editing monolithic logic.

- Defer Gemini parser architecture to a separate feature request.
  - This change does not modify Gemini parser behavior and does not add Gemini shadow parser entrypoints.
  - Rationale: CAO upstream currently does not provide a Gemini provider, and Gemini likely needs a different parser architecture/design track than CAO/TUI parser supersets.

- Make “unknown/unsupported” explicit and diagnostic-rich.
  - For each provider, shadow parsing must either:
    - match a known preset/variant with `match=true`, or
    - return/raise an explicit `unknown_format` / `unsupported_output_format` result that includes:
      - output excerpt,
      - detected version (if any),
      - failed probe reasons (if feasible).
  - Rationale: timeouts are expensive to debug and can appear as “hangs”.
  - Alternative: treat unknown output as `processing` and rely on global timeouts. Rejected (violates feature request).

- Keep `parsing_mode` surface area stable (`cao_only` vs `shadow_only`), but change defaults after parity.
  - Implementation uses the existing mode split in `cao_rest` to preserve the “no mixing in one turn” invariant.
  - Default mapping is updated so Codex CAO-backed sessions prefer shadow parsing once parity and drift detection are in place.

- Keep CAO provider parsers as reference fixtures, not as a runtime dependency.
  - We may copy representative fixture outputs into repo-owned test fixtures (under `tests/fixtures/...`) to keep unit tests independent of `extern/` and to curate coverage intentionally.

## Risks / Trade-offs

- [Risk] Shadow parser rules will require ongoing updates as upstream TUIs change.
  - Mitigation: make it easy to add presets (registry + fixture-first workflow) and ensure drift is surfaced explicitly with diagnostics.

- [Risk] Over-strict probing could classify real output as unknown, causing turn failures.
  - Mitigation: start with permissive-but-safe probes, cover more real fixtures, and provide an operator override to pin presets or switch to `cao_only` during incidents.

- [Risk] Changing Codex default parsing mode may regress environments that relied on CAO-native parsing quirks.
  - Mitigation: ship in phases, keep explicit configuration to force `cao_only`, and document how to revert quickly.

- [Risk] Deferring Gemini parser design leaves Gemini-specific parser hardening out of this change.
  - Mitigation: track as a separate feature request and keep current Gemini headless path unchanged for now.

## Migration Plan

1. Implement the new parser core + registry and refactor existing Claude/Codex parsers into presets behind the same runtime interface.
2. Add fixture-driven tests (including drift fixtures) and ensure parity-or-better behavior vs upstream CAO provider fixtures for supported variants.
3. Wire `cao_rest` shadow-only paths to the new stack and enrich error reporting with anomaly metadata and excerpts.
4. Roll out the new default preference:
   - Keep Codex default `cao_only` while parity is incomplete.
   - Flip Codex default to `shadow_only` once fixtures and real-world validation show parity and reliable drift detection.
5. Update documentation to describe:
   - the new default behavior,
   - how to force `cao_only`,
   - how to interpret drift diagnostics.

Rollback strategy:

- Revert default parsing-mode mapping to `codex -> cao_only` and/or disable shadow-only mode in config for affected environments while presets are updated.

## Open Questions

- Should “unknown format” be represented as a distinct status (`unknown_format`) or always as a structured parse error? (Both satisfy “explicit”, but status can be useful for reporting/telemetry.)
- What is the minimal, stable set of Codex “real TUI” markers we should treat as part of each variant probe (banner, footer chrome, prompt glyphs, assistant marker)?
- Follow-up tracked separately: `context/issues/features/feat-gemini-headless-parser-architecture.md`.

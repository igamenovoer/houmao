# TUI Parsing Architecture

The TUI parsing stack exists because CAO gives the runtime a transport surface, not a structured turn protocol. For `shadow_only`, the runtime reads `mode=full` tmux snapshots and turns them into stable state/projection artifacts that it can reason about over time.

## Core Design Boundary

The stack is intentionally split so each layer owns one kind of responsibility:

| Layer | Owns | Must not own |
|------|------|--------------|
| CAO transport | fetching terminal snapshots and sending input | deciding whether visible text is the answer for the prompt |
| Provider parser | classifying one snapshot and selecting the projector that will produce visible-dialog output | submit-aware lifecycle across multiple snapshots |
| Runtime `TurnMonitor` | pre-submit readiness and post-submit lifecycle | provider-specific regexes or prompt chrome rules |
| Optional associator | caller-owned extraction heuristics over projected dialog | provider-owned state detection |

This separation is the key outcome of `decouple-shadow-state-from-answer-association`: provider parsing remains centralized and version-aware, while prompt-to-answer association becomes explicit and optional.

The projection stage is also modular. Shared core code owns normalization and final assembly, while each provider parser owns version-aware projector selection and may swap projector instances without changing the rest of the runtime lifecycle stack.

## End-To-End Flow

```mermaid
flowchart TD
    U[User prompt] --> RT[CAO runtime<br/>send-prompt loop]
    RT --> CAO[CAO REST API]
    CAO --> TMUX[tmux snapshot<br/>mode=full]
    TMUX --> N[Normalize and strip ANSI]
    N --> PP[Provider parser<br/>Claude or Codex]
    PP --> SA[SurfaceAssessment]
    PP --> DP[DialogProjection]
    SA --> TM[TurnMonitor]
    DP --> TM
    DP --> AA[Optional AnswerAssociator]
    TM --> RES[Structured shadow_only result]
    AA --> CALLER[Caller-specific extraction]
    RES --> CALLER
```

## Major Modules

| File | Role |
|------|------|
| `backends/shadow_parser_core.py` | shared dataclasses, anomaly types, projector protocol, projection metadata, preset registry helpers, shared projection assembly |
| `backends/claude_code_shadow.py` | Claude-specific parser, preset families, state detection, projector selection, dialog projection heuristics |
| `backends/codex_shadow.py` | Codex-specific parser, output-family detection, state detection, projector selection, dialog projection heuristics |
| `backends/cao_rest.py` | CAO polling loops, `_TurnMonitor`, payload shaping, runtime terminality rules |
| `backends/shadow_answer_association.py` | optional caller-side association helpers such as `TailRegexExtractAssociator` |

## Why The Parser Returns Two Artifacts

One normalized snapshot becomes two first-class artifacts:

- `SurfaceAssessment`: what the tool appears to be doing right now
- `DialogProjection`: the visible dialog-oriented transcript with TUI chrome removed

This split matters because the runtime needs both answers independently:

- “Is it safe to submit input or declare completion?” comes from `SurfaceAssessment`.
- “What visible dialog content changed?” comes from `DialogProjection`.

Treating those concerns as separate artifacts prevents the parser from making unstable claims such as “this exact text is definitely the final answer for the latest prompt.”

## Parser Versus Runtime Ownership

The provider parser is responsible for one-snapshot interpretation:

- version-aware preset selection
- version-aware projector selection
- supported versus unsupported output-family detection
- disconnected/error-like surface detection
- provider-specific `ui_context` classification
- dialog projection boundaries and projection metadata

The runtime is responsible for ordered-snapshot interpretation:

- waiting for safe pre-submit readiness
- recording the pre-submit projection baseline
- noticing post-submit `working` and projection changes
- promoting continuous `unknown` into `stalled`
- deciding whether the turn is blocked, failed, or complete

`ShadowParserStack` sits at the boundary: it resolves the provider parser and can pass through a projector override, but it does not own provider-specific projection logic itself.

## Result Surface

A successful `shadow_only` completion exposes structured runtime/parser output instead of a shadow-mode `output_text` alias. The caller-facing payload is built around:

- `surface_assessment`
- `dialog_projection`
- `projection_slices`
- `parser_metadata`
- `mode_diagnostics`

That result surface is deliberately neutral: it exposes what the runtime observed, while leaving prompt-specific answer extraction to higher layers. Downstream code that needs reliable machine parsing should prefer explicit schema/sentinel contracts over assuming exact `dialog_text` recovery.

# Collect Behavior Test Evidence

## Workflow

1. **Stop the declared observation window.** Record its terminal event, timeout, failure, or required clarification boundary.
2. **Export provider-native skill events when available.** Preserve original timestamps and event identifiers.
3. **Freeze transcript and terminal evidence.** Keep raw provider output separate from any rendered summary.
4. **Freeze command and access evidence.** Record observable command invocations, selected skill-file access when available, and instrumentation limitations.
5. **Capture bounded after-state.** Compare only the allowed filesystem and runtime resources declared in context.
6. **Write `evidence-index.json`.** Record path, kind, authority tier, digest, byte size, capture status, and missing-source reason for each evidence item.

If a provider exposes no reliable event export, use the native planning tool to collect the strongest remaining observable sources and mark activation evidence unavailable; do not synthesize an event from the response.

## Immutability Contract

Raw files become immutable when indexed. Rendering, excerpting, and adjudication outputs go to derived paths and retain source digests.

## Guardrails

- DO NOT record hidden chain-of-thought or ask the provider to reveal it.
- DO NOT alter transcript text to normalize provider wording.
- DO NOT treat TUI tracker output as system-skill behavior ground truth.

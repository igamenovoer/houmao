# Design

## Context

The brain builder already validates the selected model and layered tool parameters before allocating a Hermes home. It then renders the custom Chat Completions route with `prepare_hermes_home`. Hermes service, TUI, and headless startup read `agent.reasoning_effort` through the native configuration resolver. [Proposal and motivation](proposal.md)

## Goals / Non-Goals

Resolve one launch effort from validated Houmao input, apply it through the shared private-home writer, and report which input selected it. Use the same effort rules for the manager fixture and the standalone raw fixture.

The projection happens when Houmao constructs the home. Request-scoped controls belong to the existing Hermes runtime contract. Endpoint support for a specific effort is established by provider qualification.

## Decisions

### Share the Chat Completions Effort Vocabulary

Define the exact Hermes effort type and ordered presets in the Hermes tool-parameter contract. Reuse that vocabulary in the shared reasoning mapping and in fixture validation. The vocabulary describes the wire values supported by Hermes's custom Chat Completions adapter. Hermes can accept a wider internal vocabulary, including `ultra`, which the adapter clamps to `max`. Each Houmao preset selects a distinct value on this route.

### Resolve the Winner Before Creating the Home

Carry the numeric mapping from native-input validation into the Hermes build, using the established source, profile, and direct launch precedence. Validate the exact tool parameter independently, then use it as the default when the resolved launch model config has no level. Retain the distinction between explicit `none` and an omitted effort.

Pass the resolved effort into `prepare_hermes_home` so the existing atomic private write emits the route and effort together. The Hermes build uses the same selection to populate `model_selection.native_projection.reasoning` with the source, native value, and YAML target `agent.reasoning_effort`. For a numeric selection, include the requested and effective levels and the saturation flag.

### Keep Fixture Inputs on Their Existing Routes

Validate the resolved fixture options before allocating run state. Exact efforts reach the raw fixture's home writer and the manager fixture's generated `tool-params.yaml`. Manager numeric levels already flow through the generated `fixture-agent` profile. This exercises the same builder as an ordinary managed launch and preserves fixture preflight's exact-index check. Raw fixtures use an exact label such as `--reasoning-effort xhigh`.

The model-pool resolver already carries both fields. A CLI level overrides a pooled level, and pool selection supplies native model metadata such as an exact effort. A pool entry with `reasoning_effort = "xhigh"` can drive both lanes. Run-mode verification covers the raw and manager surfaces. [Issue #103](https://github.com/igamenovoer/houmao/issues/103)

## Risks / Trade-offs

- A custom endpoint can translate or reject a native effort, and Hermes can retry a rejected request with a different payload. Capture the top-level effort on the first matching main-model request at the synthetic peer. Record live Qwen behavior separately when qualifying that endpoint.
- Manager preparation can create a fixture-local preview home. Check the home recorded by the actual managed launch as well as the generated profile and setup to catch projection gaps.

## Migration Plan

The new inputs are optional. Newly built managed homes and newly prepared fixtures pick up the selection. Existing profiles and model-pool entries can add a level or native default using their existing configuration surfaces.

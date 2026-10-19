# CLI Hook Observation Channel

Status: Design draft

## Purpose

Add a provider-hook observation channel to Houmao's managed-agent state tracking. The channel collects CLI-specific lifecycle events emitted by the provider, normalizes them into a provider-neutral observation stream, and merges that stream with TUI parsing so the tracker can determine turn activity, terminal outcome, permission waits, maintenance windows, and background work without relying only on terminal text.

The first adapter targets Claude Code. The observation model, merge contract, diagnostics, fallback behavior, and qualification model are provider-neutral so Codex and Kimi Code can add adapters later without reopening the core design.

## Artifacts

- [Feature Requirement](feature-requirement.md)
- [Use Cases](usecases/README.md)
- [Design](design/README.md)
- [ADR 0001: Rx Stream Merge](adrs/0001-rx-stream-merge-for-hook-observations.md)
- [Agent Task](agent-task.md)

## Current Stage

Feature requirement and interface design are drafted. The use cases cover the core launch, merge, blocked/failure, and fallback workflows. ADR 0001 records the decision to resolve hook and TUI observations in one Rx stream. Implementation handoff, milestones, and verification gates remain to be written after design review.

## Related Context

- [TUI Tracking State Model](../../../docs/reference/tui-tracking/state-model.md): current `TrackedStateSnapshot`, readiness, completion, and last-turn vocabulary.
- [Prompt Admission and TUI Observation](../../../docs/reference/gateway/internals/prompt-admission-and-tui-observation.md): why readiness, stability, and pending input are separate facts.
- [Runtime Lifecycle and State Transitions](../../../docs/developer/tui-parsing/runtime-lifecycle.md): readiness and anchored-completion pipelines.
- [Claude Parsing Repair Campaign](../../campaigns/debug/2026-10-12-claude-code-tui-parsing/reports/2026-10-12-claude-2-1-296-parsing-repair.md): the failure classes that motivate a second channel.
- [`src/houmao/shared_tui_tracking/`](../../../src/houmao/shared_tui_tracking/): provider detectors, tracker session, and single-session tracking runtime.
- [`src/houmao/server/tui/tracking.py`](../../../src/houmao/server/tui/tracking.py): live tracker, turn anchors, readiness and completion reductions.
- [`src/houmao/agents/realm_controller/gateway_service.py`](../../../src/houmao/agents/realm_controller/gateway_service.py): prompt admission and gateway-owned tracking.
- [Claude Code hooks reference](https://code.claude.com/docs/en/hooks): provider event catalog, payload fields, handler types, and exit semantics.

## Open Questions

- Which hook events are guaranteed at the Claude Code 2.1.296 support floor, and which need version-gated activation?
- Should the hook ingress be a standalone collector, a gateway-hosted endpoint, or a Unix-socket service, given that all paths must publish into the same Rx stream?
- Should the merged Rx stream live inside `LiveSessionTracker` or a separate `HookMergeSession` composed beside it?
- Should the hook channel be opt-in per launch, default-on for managed Claude launches, or controlled by launch profile?
- Should `Stop.last_assistant_message` be published on the managed-agent state surface or retained only as local turn evidence?
- Should `claude_headless` use hooks in v1, or remain on its existing structured `stream-json` path?
- How should joined sessions and externally launched providers be handled when no hooks were injected?
- How long should raw hook payloads be retained, and which fields must be redacted before any inspection surface exposes them?

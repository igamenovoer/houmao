# Issue: Hook Observation Channel Records Two Generation-Boundary Rows Per Generation

Date: 2026-10-20. Found by the `add-codex-hook-observation` live qualification (task 6.2), `tmp/codex-hook-smoke/QUALIFICATION.md` finding 3.

## Symptom

Each fresh hook observation channel contains two generation-boundary records for the same generation, so `channel.json` `counts.generation_boundaries` is 2 where 1 is expected:

1. `HookObservationStore.__init__` appends a boundary envelope when opened with a generation newer than every existing record (`src/houmao/hook_observation/store.py`).
2. The collector process then appends its own bare `{"record": "generation_boundary", ...}` row at startup via `CollectorState.write_generation_boundary()` (`src/houmao/hook_observation/collector.py`, called from `main()`).

## Scope

Pre-existing: introduced with the original hook observation core in `ffeeb8a4` and present in the Claude lane since then; the Codex live smoke surfaced it. Both rows parse as boundaries and the reducer ignores them, so turn state and posture are unaffected. The impact is limited to misleading boundary counts in channel diagnostics and to any future consumer that assumes one boundary row per generation.

## Candidate Fix

Pick one writer: either have the collector skip its own boundary when the store open already wrote one for the same generation, or move boundary writing entirely into the collector and make store opens passive. Update the store/collector tests that pin the current double-write behavior.

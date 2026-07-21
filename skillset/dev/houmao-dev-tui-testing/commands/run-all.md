# Run the Full TUI Evidence Workflow

## Workflow

1. **Plan, delegate launch, and record** with `record`, using `houmao-dev-launch-agents` and producing a stopped and digested 20 Hz source capture.
2. **Label blindly** with `label`, producing complete, independently frozen public-state ground truth.
3. **Replay** the source and declared cadence matrix with `replay` only after label freeze.
4. **Compare** canonical exact results and cadence-aware semantic results with `compare`.
5. **Render and verify videos** with `render-video`, including a detector-comparison video when visual diagnosis is requested.
6. **Finalize one report** that links every artifact, digest, verdict, limitation, and cleanup obligation.

If the task requires a different ordering, use the native planning tool to preserve the immutable recording and blind-label dependency gates while adapting the remaining stages, then execute the plan.

## Execution Rules

`run-all` is a shortcut, not permission to weaken stage gates. It must stop before replay if labels are incomplete or contaminated, and it must stop before a pass verdict if comparison or video verification is incomplete.

Do not pause to ask the operator to approve routine unattended steps. A provider confirmation prompt fails or suspends that capture unless it is hard-coded upstream and cannot be disabled; document that exception before any intervention.

Use a new numbered attempt after live capture failure. Reuse the frozen recording for replay, comparison, or video retries when its digest remains unchanged.

## Final Report

Write `<run-root>/report.md` for a developer reader. Include:

- task, provider, CLI and detector versions, test project revision, and unattended launch posture
- exact user-operation sequence and completion status
- source capture cadence, sample count, duration, authority/taint posture, and hashes
- blind-label provenance, settle assumption, coverage, and hash
- replay matrix with interval, mode, phase, seed, row count, and status
- canonical exact verdict
- cadence-aware semantic verdicts
- false-ready, false-busy, transition, terminal-result, and timing-drift findings
- video paths, representative frame paths, media metadata, and hashes
- failed or incomplete attempts and why they do not count as passes
- cleanup status for credentials, temporary provider homes, tmux sessions, and test projects

Lead with the outcome and distinguish `pass`, `fail`, and `incomplete`. A partial matrix is an incomplete qualification even when completed variants pass.

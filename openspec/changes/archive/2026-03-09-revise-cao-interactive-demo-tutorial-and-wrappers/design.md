## Context

The existing interactive CAO demo pack already implements the core lifecycle correctly: it can start a persistent `cao_rest` session, reuse the same `agent_identity` across turns, expose inspection metadata, and stop cleanly. What is missing is the operator-facing experience around that engine. The current README emphasizes subcommands and verification, while the requested workflow is tutorial-driven: launch a known agent named `alice`, interact through simple shell helpers, and stop when the user is done.

This revision therefore focuses on surfaces rather than architecture. The pack should remain local-only, continue using the fixed CAO loopback target, and preserve the current stateful Python implementation as the source of truth.

## Goals / Non-Goals

**Goals:**
- Make the interactive demo understandable as a step-by-step tutorial instead of a terse lifecycle reference.
- Provide three obvious wrapper scripts for the main manual workflow: launch, send prompt, and stop, while keeping shell-level defaults centralized through `run_demo.sh` or a shared helper sourced from it.
- Make `alice` the tutorial's stable agent identity without removing the underlying CLI's ability to accept other names.
- Keep verification available for maintainers while removing it from the tutorial's primary happy path.
- Keep implementation review manual and tutorial-oriented instead of introducing new Pixi gating for this demo pack.

**Non-Goals:**
- Replacing the existing Python lifecycle module with shell-only logic.
- Changing the persisted state model or CAO runtime targeting rules.
- Removing the existing `run_demo.sh` multiplexer or the `inspect`/`verify` commands from the lower-level interface.
- Redesigning the current verification contract beyond documenting its existing minimum two-turn scope.
- Adding new Pixi tasks or treating this demo pack as release-certification automation.
- Expanding the tutorial to cover credential setup, CAO installation, or unrelated runtime internals.

## Decisions

1. Keep `src/gig_agents/demo/cao_interactive_full_pipeline_demo.py` as the workflow engine.
Rationale: The Python module already owns the state file, turn artifacts, validation, and launcher guardrails. Rewriting those behaviors into multiple shell scripts would duplicate logic and increase drift risk.
Alternatives considered:
- Replace the Python module with standalone shell scripts: simpler on the surface, but harder to test and more fragile around JSON/state handling.
- Make the tutorial call `brain_launch_runtime` directly: exposes too much low-level complexity and bypasses current guardrails.

2. Add thin wrapper scripts in the demo pack for the main human workflow, backed by `run_demo.sh` or a shared helper factored from it.
Rationale: Wrapper scripts give the tutorial memorable, copy-pasteable commands while `run_demo.sh` already centralizes workspace root, agent-definition defaults, launcher-home alignment, role defaults, and verification post-processing. Reusing that shell layer keeps the tutorial flow and advanced commands on one consistent session state without duplicating shell plumbing.
Alternatives considered:
- Have each wrapper call the Python module directly: explicit, but duplicates the shell-level defaults now owned by `run_demo.sh`.
- Document only `run_demo.sh start|send-turn|stop`: lower file count, but less friendly for first-time operators.
- Add wrappers for every subcommand including `inspect` and `verify`: more symmetrical, but unnecessary for the primary workflow.

3. Hardcode `alice` at the wrapper layer, not the Python module default.
Rationale: The tutorial needs one deterministic identity, but the engine should remain reusable for other names in tests or future demos.
Alternatives considered:
- Change the Python module default agent name to `alice`: simple, but couples the general CLI to one tutorial persona.
- Require the user to pass `--agent-name alice` manually each time: accurate, but adds avoidable friction.

4. Rewrite the README to follow the repository's API usage tutorial format.
Rationale: The requested style is explicitly more explanatory, with code shown inline at each critical step. Matching the house tutorial pattern makes the demo easier to audit and more consistent with other documentation.
Alternatives considered:
- Keep the existing README and add a short note about wrappers: too small a change to solve the usability problem.
- Move the tutorial into `docs/` and keep a terse pack README: splits the operator flow across two locations.

5. Reposition verification as optional maintainer tooling.
Rationale: The tutorial is intentionally open-ended and should not imply that success only means "run two prompts and stop immediately." Keeping verification as an appendix preserves regression support without confusing the main usage path, and the documentation should explicitly describe `verify` as the existing minimum two-turn maintainer check rather than a full transcript assertion.
Alternatives considered:
- Remove verification entirely: simpler pack, but loses useful automated contract checks.
- Redesign verification to cover every recorded turn: stronger claim, but outside the scope of a surface-level tutorial reshaping.
- Keep verification in the main workflow: preserves current structure, but conflicts with the requested manual-interaction tutorial.

6. Keep wrapper-flow validation manual and non-gating.
Rationale: These demo packs are learning surfaces and live documentation, not release-certification suites. Manual developer review of the tutorial flow is enough for this change, and any `bash -n` checks should remain optional author sanity aids rather than new Pixi tasks.
Alternatives considered:
- Add new Pixi tasks or automation for wrapper validation: more standardized, but mispositions the demo as a gated certification surface.
- Leave the validation story implicit: lower upfront effort, but reviewers may assume new automation is required.

## Risks / Trade-offs

- [Risk] Wrapper scripts drift from the Python CLI flags over time. -> Mitigation: keep wrappers thin and delegate all real behavior through `run_demo.sh` or a shared helper that preserves the existing shell defaults.
- [Risk] Users may launch `alice` and forget to stop the session. -> Mitigation: keep the stop script prominent in the tutorial and retain replacement behavior on repeated launch.
- [Risk] Tutorial text may become stale as the workspace layout evolves. -> Mitigation: document generated files from the current state/report structure and use the manual walkthrough as part of author review when the demo pack changes.
- [Trade-off] The pack will expose both a low-level wrapper (`run_demo.sh`) and higher-level helper scripts. -> Mitigation: present the helper scripts as the default path and describe `run_demo.sh` as the advanced interface.
- [Trade-off] Manual review is less standardized than automated gating. -> Mitigation: state clearly in the tasks and README-facing artifacts that this demo is reviewed as learning material, not as release certification.

## Migration Plan

1. Add the new wrapper scripts under `scripts/demo/cao-interactive-full-pipeline-demo/`.
2. Ensure those wrapper scripts delegate through `run_demo.sh` or a shared helper so they reuse the existing shell defaults and workspace state.
3. Rewrite the README into tutorial format and move verification to an appendix or maintainer section that explains the minimum two-turn regression scope.
4. Review the wrapper flow manually as part of implementation review, using any shell syntax checks only as optional author aids.
5. Leave existing workspace/state artifacts compatible so no user data migration is required.

## Open Questions

- No major open questions remain after review. The chosen direction is to keep `src/gig_agents/demo/cao_interactive_full_pipeline_demo.py` as the engine, route the new wrapper scripts through `run_demo.sh` or a shared helper, document `verify` as an optional minimum two-turn maintainer check, and keep implementation review manual rather than adding new Pixi automation.

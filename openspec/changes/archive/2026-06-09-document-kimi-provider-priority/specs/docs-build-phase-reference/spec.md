## ADDED Requirements

### Requirement: Build-phase Kimi references document current system-prompt caveat

Build-phase reference pages that describe Kimi launch policy SHALL name Kimi Code 0.11.0 when discussing current Kimi launch behavior.

The build-phase launch-policy reference SHALL warn that Kimi Code 0.11.0 does not expose a native system-prompt flag. The warning SHALL distinguish this from Kimi skill support: Houmao may project `houmao-auto-system-prompt`, but Kimi users may need to invoke that skill manually before substantive chat begins when automatic skill startup does not run first.

The warning SHALL NOT claim that Kimi Code is unsupported, and SHALL NOT remove accurate Kimi `--skills-dir`, `extra_skill_dirs`, prompt-mode, or TUI unattended launch-policy details.

#### Scenario: Reader sees current Kimi launch-policy version

- **WHEN** a reader opens `docs/reference/build-phase/launch-policy.md`
- **THEN** Kimi launch-policy guidance names Kimi Code 0.11.0 for current behavior
- **AND THEN** older 0.10-family wording is not used for current Kimi launch behavior unless it is explicitly historical

#### Scenario: Reader sees Kimi system-prompt caveat without losing skill guidance

- **WHEN** a reader reviews Kimi launch-policy caveats
- **THEN** the docs state that Kimi Code 0.11.0 lacks a native system-prompt flag
- **AND THEN** the docs state that `houmao-auto-system-prompt` may need manual invocation before substantive Kimi chat begins
- **AND THEN** the docs continue to document supported Kimi skill projection and launch-policy behavior

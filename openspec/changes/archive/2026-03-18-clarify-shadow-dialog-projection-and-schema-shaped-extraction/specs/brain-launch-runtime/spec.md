## MODIFIED Requirements

### Requirement: Runtime mail commands use skill-directed prompts with appended mailbox metadata and validate a sentinel-delimited result contract
The runtime SHALL translate each `mail` command invocation into a runtime-owned mailbox prompt delivered through the existing prompt-turn control path rather than directly manipulating mailbox files or mailbox SQLite state itself.

That mailbox prompt SHALL explicitly tell the agent which projected mailbox system skill to use for the mailbox operation and SHALL append structured mailbox metadata needed for the mailbox operation and result parsing.

The `mail` command handler SHALL validate exactly one structured mailbox result payload returned between `AGENTSYS_MAIL_RESULT_BEGIN` and `AGENTSYS_MAIL_RESULT_END` sentinels in the agent output and SHALL surface that result to the operator in a parseable form.

That sentinel-delimited structured result contract SHALL be the correctness boundary for mailbox result parsing. The runtime SHALL NOT rely on generic shadow dialog projection fidelity as the guarantee that mailbox result text was recovered exactly.

#### Scenario: Mail command uses skill-directed prompt with appended mailbox metadata
- **WHEN** a developer invokes a runtime `mail` command for a mailbox-enabled session
- **THEN** the runtime delivers a runtime-owned mailbox prompt through the existing prompt-turn control surface for that session
- **AND THEN** that prompt explicitly names the projected mailbox system skill the agent should use
- **AND THEN** that prompt tells the agent to inspect the shared mailbox `rules/` directory before interacting with shared mailbox state
- **AND THEN** that prompt tells the agent to use shared scripts from `rules/scripts/` for any mailbox step that touches `index.sqlite` or `locks/`
- **AND THEN** that prompt appends structured mailbox metadata for the mailbox operation and result contract

#### Scenario: Mail command returns structured mailbox result
- **WHEN** a mailbox-enabled agent completes a runtime `mail` request
- **THEN** the agent returns one structured mailbox result payload describing the mailbox operation outcome between the required sentinels
- **AND THEN** the runtime validates and prints that result in a parseable form for the operator

#### Scenario: Shadow-mode mailbox parsing relies on the schema contract rather than exact projection cleanup
- **WHEN** a mailbox-enabled shadow-mode session returns one sentinel-delimited JSON result together with surrounding TUI noise or imperfect projection cleanup
- **THEN** the runtime still treats the sentinel-delimited structured payload as the reliability boundary
- **AND THEN** mailbox correctness does not depend on `dialog_projection.dialog_text` being an exact recovered reply transcript

#### Scenario: Mail command fails on malformed sentinel payload
- **WHEN** a mailbox-enabled agent omits the required sentinels, emits malformed JSON, or returns more than one sentinel-delimited mailbox result payload
- **THEN** the runtime returns an explicit mailbox-result parsing error for that `mail` command

### Requirement: Shared post-processing provides a stable runtime contract in both modes
For CAO-backed turns in both `parsing_mode=cao_only` and `parsing_mode=shadow_only`, the runtime SHALL apply a shared, parser-agnostic post-processing step after mode-specific gating/output handling.

This shared post-processing step SHALL NOT sanitize/rewrite `cao_only` extracted answer text. It SHALL canonicalize status/provenance into runtime-stable values for downstream consumers and record/log raw backend values for diagnostics.

For `shadow_only`, shared post-processing SHALL distinguish projected dialog content from any caller-owned answer association logic, SHALL expose first-class `dialog_projection` and `surface_assessment` payload fields, and SHALL NOT label projected dialog as the authoritative final answer for the current prompt by default.
For `shadow_only`, the surfaced `dialog_projection` SHALL remain a best-effort text projection that is suitable for lifecycle diffing, operator inspection, and caller-owned best-effort extraction, but SHALL NOT be represented as an exact recovered reply transcript.
For `shadow_only`, downstream machine-critical parsing SHALL rely on explicit schema-shaped output contracts or caller-owned extraction rules over the available text surfaces rather than on projection fidelity alone.
For `shadow_only`, shared post-processing SHALL NOT preserve `output_text` as a compatibility alias to projected dialog.
If raw CAO `tail` text is retained for debugging, it SHALL remain in diagnostics or internal-only fields and SHALL NOT become a first-class caller-facing shadow result field.

#### Scenario: Shared post-processing runs regardless of parsing mode
- **WHEN** a CAO-backed turn completes in `parsing_mode=cao_only` or `parsing_mode=shadow_only`
- **THEN** shared post-processing is applied before the result is surfaced to the caller

#### Scenario: `shadow_only` payload distinguishes projection from authoritative answer
- **WHEN** a CAO-backed `shadow_only` turn completes
- **THEN** the surfaced runtime payload includes projected dialog/provenance data and surface-assessment data as first-class fields
- **AND THEN** the payload does not include a shadow-mode `output_text` compatibility alias
- **AND THEN** any retained raw tail debugging data remains outside the primary caller-facing result surface
- **AND THEN** the runtime does not represent that projection as the authoritative final answer or as an exact recovered reply transcript for the submitted prompt

#### Scenario: Machine-critical shadow consumer uses explicit extraction contract
- **WHEN** a downstream caller needs reliable machine-readable data from a `shadow_only` result
- **THEN** the runtime exposes the best-effort projection surfaces without claiming exact reply extraction
- **AND THEN** the caller uses an explicit schema-shaped contract or caller-owned extractor to recover the needed payload

### Requirement: Repo-owned CAO workflows for supported shadow tools follow the shadow-first contract
For CAO-backed tools that have a runtime-owned shadow parser family, repo-owned workflows, demos, and maintainer-facing helper surfaces SHALL treat `shadow_only` as the normal parsing posture.

Such surfaces MAY rely on the existing per-tool parsing-mode default or request `shadow_only` explicitly, but SHALL NOT pin `cao_only` as their normal default unless the workflow exists specifically to exercise or debug the CAO-native path.

When one such shadow-first workflow needs text beyond completion status, it SHALL use structured shadow payloads, explicit schema/sentinel outputs, side-effect verification, or clearly labeled best-effort shadow extraction rather than assuming the final runtime `done.message` contains the exact agent reply text.

#### Scenario: Repo-owned CAO helper workflow relies on the supported tool default
- **WHEN** a repo-owned workflow starts a CAO-backed Claude or Codex session without an explicit parsing-mode override
- **THEN** the workflow runs under the runtime-resolved `shadow_only` default for that supported tool
- **AND THEN** the workflow does not introduce an unnecessary `cao_only` override just to preserve older answer-text assumptions

#### Scenario: Shadow-first workflow needs text evidence beyond neutral completion message
- **WHEN** a repo-owned CAO workflow for Claude or Codex needs text evidence from a successful `shadow_only` turn
- **THEN** it does not treat the final runtime `done.message` as the authoritative reply text
- **AND THEN** it uses structured shadow payloads, explicit schema/sentinel outputs, side-effect checks, or clearly labeled best-effort shadow extraction instead

#### Scenario: CAO-native troubleshooting remains an explicit exception
- **WHEN** a maintainer runs a dedicated troubleshooting or CAO-native coverage path for a supported tool
- **THEN** that path may still request `parsing_mode=cao_only`
- **AND THEN** the exception is explicit rather than being presented as the normal default posture

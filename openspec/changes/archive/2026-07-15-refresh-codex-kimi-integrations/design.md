## Context

Houmao currently treats a Codex four-effort table as a general fallback, although Codex 0.144.1 bundles distinct GPT-5.6 Sol, Terra, and Luna capability records. Its headless JSON protocol also includes collaboration items that the canonical parser leaves as passthrough events.

Kimi Code has moved from the 0.11 family used to author Houmao's policies and detectors to the 0.23 family. The packaged launch-policy ranges therefore reject the installed CLI. The old TUI policy also works around a former resume conflict by setting runtime config and submitting `/auto on`; current Kimi accepts native `--auto` with resume selectors. Current Kimi model aliases can declare ordered thinking efforts, and current stream JSON includes retry metadata.

The TUI registry selects the closest semver floor with no upper compatibility bound. Codex 0.144.x therefore receives a 0.116.x detector and Kimi 0.23.x receives a 0.11.x detector even though neither profile was validated against those surfaces. Current Codex also exposes delegated-agent activity, while current Kimi has changed its activity, tool, todo, background-task, and footer surfaces.

The implementation must preserve unattended operation. Normal automated TUI scenarios must not ask the operator to approve tools or answer provider questions. An exception is acceptable only when the CLI hard-codes an intervention and exposes no setting that suppresses it.

## Goals / Non-Goals

**Goals:**

- Make Codex 0.144.x and Kimi 0.23.x the maintained runtime contracts.
- Represent GPT-5.6 reasoning and Kimi model efforts without pretending every model supports one universal ladder.
- Keep Kimi unattended TUI startup native, deterministic, and free of policy-changing bootstrap turns.
- Preserve current collaboration and retry semantics in canonical headless events.
- Select TUI profiles only inside evidence-backed version intervals.
- Validate current profiles from manually labeled 20 fps recordings and varied sparse replays.
- Update all affected tests, user documentation, developer documentation, and packaged system-skill guidance.

**Non-Goals:**

- Preserve the obsolete Kimi 0.10/0.11 launch strategy as a compatibility shim.
- Add a generic provider capability service or a network dependency for model lookup.
- Guarantee exact sample-by-sample equality when sparse capture skips a transient TUI frame.
- Simulate provider network or LLM API failures that cannot be triggered deterministically.
- Add provider-native controls beyond Houmao's existing model name and reasoning preset index.

## Decisions

### Use Maintained Model-Specific Codex Tables

Add explicit GPT-5.6 prefix entries to `model_mapping_policy.py`, ordered before the legacy fallback. `gpt-5.6` follows the Codex alias target, Sol. Sol and Terra expose six positive steps through `ultra`; Luna exposes five through `max`.

The implementation will keep deterministic repository-owned tables for this change. It will add tests derived from `extern/orphan/codex/codex-rs/models-manager/models.json` and may add a developer assertion helper around `codex debug models --bundled`. It will not require that subprocess during every brain build.

Alternative considered: query `codex debug models --bundled` for every launch. This tracks upstream automatically but makes build behavior depend on an installed executable and moving local catalog. A future capability-cache change can introduce that boundary deliberately.

### Derive Kimi Efforts from the Constructed Runtime Model Alias

After setup and auth projection, model mapping will read the effective selected alias from the constructed Kimi `config.toml`. It will apply the alias's effective on-disk `support_efforts` ordering, including any Kimi-defined override, and project the selected value through `[thinking] enabled = true` plus `[thinking] effort = <value>`.

Level `0` sets thinking disabled only when the model is not always-thinking. A positive request without an ordered capability list fails clearly. Current Kimi env-model variables expose a selected native effort but no ordered effort catalog, so launch-owned normalized reasoning is rejected for that lane. Native `KIMI_MODEL_THINKING_EFFORT` remains supported as baseline configuration when no normalized reasoning level is requested. Saturation and native projection remain recorded in the existing secret-free model provenance.

Alternative considered: assign every Kimi model `low, medium, high`. Current Kimi registries expose model-specific arbitrary effort lists, so a fixed table would reproduce the same error as the current Codex fallback.

### Replace the Kimi Strategy Instead of Layering a Shim

Replace the packaged Kimi strategies with `>=0.23.0,<0.24.0` strategy entries and current source/live-probe evidence. Headless policy continues to strip prompt-mode-incompatible `--auto`, `--yolo`, and `--plan` inputs because Kimi `-p` installs automatic approval and null question handlers itself.

For TUI unattended mode, the provider hook will canonicalize caller-owned permission flags, reject incompatible `--yolo` combinations, and append one strategy-owned `--auto`. Resume translation may then add `--continue` or `--session <id>` because current Kimi permits those combinations. Remove the runtime `/auto on` refresh action and its wait/bootstrap ordering. `default_permission_mode = "auto"` may remain as fallback and inspectable runtime state, but the final CLI argument is authoritative.

Alternative considered: retain the old strategy for older Kimi installations. The project permits breaking changes, and retaining an untested launch contract would expand the maintenance matrix without serving the maintained release.

### Extend Canonical Parsing Without Changing the Event Schema

Map Codex `collab_tool_call` into the existing `action_request` and `action_result` categories. Provider-specific collaboration fields remain in canonical `data` and raw payloads. Existing renderers can then show delegation through their normal action lifecycle.

Map Kimi `turn.step.retrying` into `progress` when retrying continues and include error details as structured diagnostic context. Preserve the original payload and raw stdout. No new top-level canonical kind is required.

Alternative considered: expose both as passthrough and teach each downstream consumer. That would defeat the canonical event boundary and hide GPT-5.6 delegation from concise output.

### Bound TUI Profile Compatibility Intervals

Extend profile registration with an optional exclusive maximum version. Selection will choose the newest profile whose minimum and maximum contain the observed version. If none match, the app-specific fallback wins. Explicit test-only overrides remain available for experiments.

Register Codex 0.116.x and Kimi 0.11.x with evidence-bounded maxima. Add Codex 0.144.x and Kimi 0.23.x registrations only after their recorded validation gates pass. Versions between maintained families or newer than them use fallback rather than inheriting an old detector indefinitely.

Alternative considered: rename the old profiles to current versions after spot checks. Their signal assumptions are derived from different TUIs, so renaming would misstate provenance and preserve the selection defect.

### Treat High-Rate Manual Labels as Truth and Sparse Replays as Delay Simulations

Use the terminal recorder to capture unattended sessions at about 20 fps. Human reviewers label the source stream before comparing tracker output. Derive regular lower-rate and jittered streams from the same capture, retaining `source_sample_id` traceability.

High-rate validation remains strict where labels specify public fields. Sparse validation evaluates ordered semantic constraints and bounded drift. It may skip a short transient state but must not report readiness during observed work, invent an operator confirmation, settle success before later same-turn activity, or create another impossible lifecycle.

The Codex corpus will cover normal prompt activity and GPT-5.6 collaboration. The Kimi corpus will cover current editor, activity, tool, todo/background, retry, interruption, ready-return, and any unavoidable hard-coded intervention. All ordinary scenarios run unattended.

Alternative considered: capture each sampling rate live. Derivation from one source is more reproducible and isolates tracker sensitivity to sampling delay from provider behavior changes between runs.

### Refresh Documentation and Skills by Contract Search

Update references identified by searches for obsolete versions, old Kimi resume conflicts, `/auto on`, four-level Codex claims, and removed Kimi environment variables. This includes `docs/`, relevant `src/assets` system skills, and their tests or snapshots. Historical troubleshooting documents may retain an old observed version only when they state that it is historical evidence rather than the maintained contract.

## Risks / Trade-offs

- [Kimi 0.23.x changes again before implementation completes] → Pin source evidence to the local checkout commit, validate the installed CLI, and keep the strategy range below 0.24.0.
- [Model aliases omit or dynamically refresh effort metadata] → Fail normalized reasoning clearly and preserve native config when no Houmao reasoning level is requested.
- [A sparse replay misses a decisive modal frame] → Keep high-rate strict validation and use semantic constraints for sparse derivatives instead of pretending the missing frame was observed.
- [Delegated-agent TUI wording changes within 0.144.x] → Prefer structural regions, styles, and bounded tokens from recordings and source inspection; keep exact sentences diagnostic only.
- [Unattended mode encounters a hard-coded prompt] → Record the surface, prove no supported suppression exists, label it as an explicit exception, and do not weaken the general no-confirmation requirement.
- [Removing the old Kimi strategy breaks older local installations] → Fail with the existing explicit compatibility diagnostic and direct maintainers to install the maintained Kimi family.

## Migration Plan

1. Land deterministic model, launch-policy, adapter, and headless parser updates with unit fixtures.
2. Capture and label current unattended TUI evidence, implement bounded registry selection, and add current detector profiles.
3. Run high-rate and sparse replay validation before registering either new profile as maintained.
4. Update documentation and packaged system skills, then run repository-wide stale-contract searches.
5. Run unit, runtime, lint, typecheck, OpenSpec validation, and targeted live unattended smoke tests.

No stored-data migration is required. Older Kimi CLIs will stop resolving a maintained unattended strategy. Rollback consists of reverting the change; no persistent runtime-home format is rewritten in place.

## Open Questions

None. Any upstream hard-coded confirmation discovered during corpus capture must be documented as evidence during implementation, not resolved by weakening unattended mode in advance.

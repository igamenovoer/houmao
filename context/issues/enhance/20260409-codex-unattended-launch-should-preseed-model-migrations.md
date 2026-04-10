# Enhancement Proposal: Codex Unattended Launch Should Pre-Seed Model Migration Acknowledgements

## Status
Proposed on 2026-04-09.

## Summary
Houmao's unattended Codex launch handling should proactively suppress Codex's model-migration chooser when the generated Codex home is configured to start on an older model that upstream Codex now maps to a newer recommended model.

Today, Codex can stop at a blocking TUI screen such as:

```text
Introducing GPT-5.4

1. Try new model
2. Use existing model
```

That is incompatible with unattended startup because the terminal exists and the process is alive, but the agent is not actually ready for work.

The verified suppression path is to write the acknowledgement map into the generated Codex config before launch:

```toml
[notice.model_migrations]
"gpt-5.2" = "gpt-5.4"
```

The model key must be quoted when it contains dots.

## Why
This should be treated as a runtime-launch concern, not an operator workaround.

Recent local investigation showed:

- upstream Codex advertises upgrade metadata for `gpt-5.2` and `gpt-5.2-codex` to `gpt-5.4`
- the Codex TUI suppresses the chooser when `notice.model_migrations[old_model] == target_model`
- a live launch with an isolated `CODEX_HOME` confirmed that pre-seeding `"gpt-5.2" = "gpt-5.4"` avoids the migration screen and proceeds to the normal startup flow

Even if the repo's current default Codex fixture already uses `gpt-5.4`, unattended launch handling should not depend on "current defaults happen to be new enough." Any older pinned Codex model in a fixture, recipe, generated config, or imported user setup can reintroduce the modal.

## Requested Enhancement
1. When Houmao prepares a Codex runtime home for unattended or automation-oriented launch, inspect the configured model in the generated Codex config.
2. If that model has a known Codex upgrade target and the runtime intends to stay on the older model, write the matching acknowledgement into `notice.model_migrations` before launch.
3. Ensure TOML emission quotes dotted model keys such as `"gpt-5.2"` and `"gpt-5.2-codex"`.
4. Keep the configured `model` unchanged unless a separate policy explicitly chooses to upgrade the runtime to the new model.
5. Cover the behavior with tests so unattended Codex launch no longer relies on manual first-run confirmation.

## Desired Behavior
Given a generated Codex home with:

```toml
model = "gpt-5.2"
```

Houmao should materialize:

```toml
[notice.model_migrations]
"gpt-5.2" = "gpt-5.4"
```

before starting the TUI session, so the Codex launch path reaches the normal startup flow instead of the migration chooser.

The same rule should apply to any other old-model to new-model pair that Houmao intentionally launches unattended and that Codex declares in its model catalog.

## Acceptance Criteria
1. Unattended Codex launch preparation detects when the configured Codex model has a migration target that would otherwise trigger a first-run chooser.
2. Generated Codex runtime homes pre-seed `notice.model_migrations` for those model pairs before TUI launch.
3. TOML generation correctly quotes dotted model keys.
4. The launch path preserves the configured older model unless the user or fixture explicitly requests the newer model.
5. A Codex unattended startup configured on `gpt-5.2` no longer stops on the `Introducing GPT-5.4` modal when the generated home contains the acknowledgement mapping.
6. Tests cover at least:
   - config generation for a dotted old-model key
   - unattended startup preparation for an older Codex model
   - no regression for already-current models such as the current `gpt-5.4` fixture
7. Documentation for Codex runtime setup explains that migration acknowledgements are part of unattended home preparation when older pinned models are used.

## Likely Touch Points
- `src/houmao/project/assets/starter_agents/tools/codex/setups/`
- `tests/fixtures/agents/tools/codex/setups/`
- Codex runtime-home generation logic under `src/houmao/`
- Codex-related launch and demo tests under `tests/unit/` and `tests/integration/`
- Codex knowledge notes under `context/summaries/codex-kb/`

## Non-Goals
- No requirement to suppress unrelated first-run prompts such as directory trust in the same enhancement.
- No requirement to force all Codex fixtures onto the newest model.
- No requirement to add a generic policy engine for every possible upstream Codex notice in the same change.
- No requirement to support arbitrary guessed migration pairs that are not backed by upstream Codex model metadata.

## Suggested Follow-Up
1. Decide where the migration-pair knowledge should come from:
   - explicit Houmao-managed mapping
   - parsed upstream Codex model catalog
   - a narrower fixture-level override
2. Implement the acknowledgement write during Codex home materialization rather than as an ad hoc demo-only patch.
3. Add a focused unattended smoke test that launches Codex on an older model with auto credentials and confirms the TUI does not land on the migration chooser.
4. Cross-link implementation work to:
   - `context/issues/resolved/issue-codex-model-migration-modal-blocks-interactive-demo-startup.md`
   - `context/summaries/codex-kb/model-migration-prompt-suppression.md`

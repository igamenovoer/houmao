## Context

The interactive CAO full-pipeline demo under `scripts/demo/cao-interactive-full-pipeline-demo/` is currently organized as a reusable engine with thin shell wrappers, but the implementation and docs are still Claude-specific in several places:

- `src/gig_agents/demo/cao_interactive_demo/models.py` hard-codes `DEFAULT_TOOL_NAME = "claude"`,
- `src/gig_agents/demo/cao_interactive_demo/cli.py` still presents `--agent-name` through an engine-owned default instead of a recipe-defined default,
- `src/gig_agents/demo/cao_interactive_demo/runtime.py` still builds brains from demo-owned tool, skill, config-profile, and credential-profile defaults instead of using the existing `build-brain --recipe` path,
- startup progress and README language describe only Claude sessions,
- `inspect` exposes `claude_code_state`,
- `inspect --with-output-text` directly uses `ClaudeCodeShadowParser`, and
- the tracked verification snapshot is fixed to `tool = "claude"`.

At the same time, the repo already supports CAO-backed Codex sessions and already includes the two Codex brain recipes we want to demo:

- `codex/gpu-kernel-coder-default`
- `codex/gpu-kernel-coder-yunwu-openai`

What is still missing is a tracked Claude recipe that represents the demo's current default Claude build inputs. Right now the interactive demo is effectively using an implicit Claude recipe that lives in code instead of under the repo's canonical `agents/brains/brain-recipes/` structure.

This change is cross-cutting because it touches the shell wrappers, the Python demo engine, the persisted state model, the inspect/report surfaces, the README contract, and the demo tests.

## Goals / Non-Goals

**Goals:**

- Keep a single interactive CAO demo pack that can launch Claude or Codex.
- Preserve the current no-arg Claude path as the default operator experience.
- Make startup recipe-driven for both Claude and Codex instead of keeping Claude on a hard-coded special path.
- Add the missing tracked Claude recipe so the default demo launch is represented in the same declarative layer as the Codex launches.
- Make recipe-defined default agent names the source of truth for identity defaults, with `--agent-name` acting as an explicit override.
- Add explicit recipe-based startup selection through repo-owned brain recipes instead of demo-specific auth-mode flags.
- Prefer a clean recipe-first operator contract over backward compatibility with existing demo invocations, then fix any in-repo call sites to match.
- Persist resolved tool/variant metadata so follow-up commands keep working without repeated selection flags.
- Make inspect and verification tool-aware by using the existing runtime parser stack instead of Claude-only logic.

**Non-Goals:**

- Creating new tool config or credential profiles beyond the repo-owned profiles that already exist.
- Replacing the separate one-shot `scripts/demo/cao-codex-session/` smoke demo.
- Supporting multiple simultaneously active interactive demo run markers, one per tool or per variant.
- Changing CAO base URL behavior for this demo pack away from the fixed loopback target.
- Preserving legacy interactive-demo call shapes through compatibility shims once the recipe-first startup contract is in place.

## Decisions

### 1. Extend the existing interactive pack instead of creating a second long-running Codex pack

The existing `run_demo.sh` already delegates nearly all behavior into the shared Python engine, so the lowest-maintenance path is to generalize that engine rather than clone the interactive workflow into a second pack.

Rationale:

- The lifecycle model (start, send-turn, send-keys, inspect, verify, stop) is identical across Claude and Codex.
- Duplicating the pack would create two README/tutorial surfaces and two parallel test matrices for the same interaction model.
- The repo already keeps Codex-specific behavior lower in the stack through runtime parser and credential/profile abstractions.

Alternative considered:

- Add a separate `cao-interactive-codex-full-pipeline-demo` pack.
- Rejected because it would duplicate the long-running interactive flow and make future wrapper or inspect changes harder to keep aligned.

### 2. Make startup recipe-driven for both the default Claude path and explicit recipe selection

The startup surface will remain Claude-by-default, but the `start` subcommand will resolve all launches through brain recipes:

- `--brain-recipe <selector-relative-to-brains/brain-recipes/>`

Within this demo pack, `--brain-recipe` will be resolved under the fixed `brains/brain-recipes/` root beneath the active agent-definition directory. The selector may be either:

- a unique basename such as `gpu-kernel-coder-yunwu-openai`, or
- a relative subpath such as `codex/gpu-kernel-coder-default`

The `.yaml` suffix will be optional in either form.

Recipe lookup will require exactly one matching recipe file under that fixed root. Zero matches will fail explicitly. Ambiguous basename matches will also fail explicitly, and the operator can disambiguate by providing a selector with subdirectory context.

When the operator omits `--brain-recipe`, startup will implicitly resolve the tracked default Claude recipe:

- `claude/gpu-kernel-coder-default`

This requires adding that missing Claude recipe to the repo-owned recipe set so the default demo startup stops depending on hard-coded `tool/config_profile/credential_profile` wiring.

The selected recipe will also provide the default agent name for the launch through a tracked recipe field such as `default_agent_name`. When the operator does not provide `--agent-name`, the demo will use that recipe-defined default name. When `--agent-name <name>` is provided, it will override the recipe-defined default before agent-identity canonicalization.

The demo will resolve and load the selected recipe in Python to obtain startup metadata needed before build, including:

- the canonical recipe selector,
- `tool`,
- `default_agent_name`, and
- any recipe-owned metadata needed for persisted variant state.

After that metadata step, the demo will delegate the actual brain construction through the existing shared CLI path:

- `brain_launch_runtime build-brain --recipe <resolved-path>`

The resolved recipe, not demo-owned defaults, will fully own the build inputs for this demo path:

- `tool`
- `skills`
- `config_profile`
- `credential_profile`

This means the current demo-owned build defaults such as `DEFAULT_SKILLS` stop being part of the supported startup composition once recipe-first startup is in place.

The tracked interactive-demo recipes will also use tool-specific `default_agent_name` values instead of one shared cross-tool default identity.

Supported recipe selectors for this change include at minimum:

- `claude/gpu-kernel-coder-default`
- `codex/gpu-kernel-coder-default`
- `gpu-kernel-coder-yunwu-openai`
- `codex/gpu-kernel-coder-yunwu-openai`

Because the Claude and Codex default recipes intentionally share the same basename, `gpu-kernel-coder-default` by itself will be ambiguous and must fail with a disambiguation error.

The intended operator-facing CLI shape is:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh start

scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh start \
  --agent-name gpu-demo \
  --brain-recipe claude/gpu-kernel-coder-default

scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh start \
  --agent-name gpu-demo \
  --brain-recipe codex/gpu-kernel-coder-default

scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh start \
  --agent-name gpu-demo \
  --brain-recipe gpu-kernel-coder-yunwu-openai
```

The launch wrapper will remain a convenience entrypoint that happens to pass `--agent-name alice`, but that wrapper-level choice is not the semantic default for the demo. The shared startup path still derives its default name from the selected recipe whenever no override is supplied.

The wrapper will continue to forward the same startup-time recipe argument:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/launch_alice.sh

scripts/demo/cao-interactive-full-pipeline-demo/launch_alice.sh \
  --brain-recipe claude/gpu-kernel-coder-default

scripts/demo/cao-interactive-full-pipeline-demo/launch_alice.sh \
  --brain-recipe codex/gpu-kernel-coder-default

scripts/demo/cao-interactive-full-pipeline-demo/launch_alice.sh \
  --brain-recipe gpu-kernel-coder-yunwu-openai
```

Rationale:

- The repo already owns the Codex recipe definitions, and adding the missing Claude recipe lets recipes become the single source of truth for tool, skill, config-profile, and credential-profile composition across the demo.
- Keeping the default agent name in the recipe avoids making `alice` or any other tutorial wrapper name part of the engine contract.
- Loading recipe metadata in the demo while still invoking `build-brain --recipe` lets the demo keep selector resolution, startup messaging, and agent-name selection local without duplicating shared build composition logic.
- The `agents/` layout is fixed in this system, so the demo can accept selectors relative to `brains/brain-recipes/` and still resolve them to full recipe paths before invoking the underlying builder.
- Recipe-based selection keeps the demo CLI aligned with the existing `build-brain --recipe` workflow instead of inventing a second set of auth-oriented operator flags or reconstructing recipe fields into parallel demo defaults.
- Claude users keep the existing no-arg default path, but that path becomes an implicit recipe lookup instead of an engine-local default constant, and its identity default now comes from the recipe as well.
- Because breaking changes are acceptable for this repo, the implementation can replace old call shapes directly instead of adding compatibility branches and aliases.

Alternative considered:

- Keep Codex on recipes but leave Claude on hard-coded `tool/config_profile/credential_profile` defaults.
- Rejected because that would preserve two startup models, make the default Claude flow harder to audit, and leave the repo without a declarative Claude recipe for the tracked demo path.

- Keep a demo-owned `DEFAULT_AGENT_NAME` such as `alice` even after moving startup to recipes.
- Rejected because it would still make the tutorial wrapper leak into the core demo contract and would prevent different recipes from carrying different sensible default names.

### 3. Do not add compatibility shims for superseded demo call shapes

Once the recipe-first startup contract is implemented, the repo will treat that contract as the only supported interface for this demo pack. Existing in-repo invocations, tests, docs, and wrappers that no longer match will be updated instead of being preserved through compatibility parsing or dual-mode behavior.

Rationale:

- The user has explicitly said breaking changes are acceptable for this repo.
- Avoiding compatibility branches keeps the demo engine and shell layer simpler and makes the resulting contract easier to understand.
- The repo fully controls its own wrappers, docs, and tests, so broken internal callers can be fixed directly in the same change.

Alternative considered:

- Keep both the legacy startup contract and the new recipe-first contract working in parallel for a transition period.
- Rejected because it would complicate the implementation and tests without providing value for this repo-owned demo surface.

### 4. Resolve demo variants from the selected startup path and persist the resolved metadata

The demo engine will resolve startup selection into a canonical recipe selector and a stable variant identity:

- no-arg startup -> canonical recipe selector `claude/gpu-kernel-coder-default`
- explicit recipe startup -> canonical recipe selector derived from the selected recipe file path relative to `brains/brain-recipes/`, without `.yaml`
- resolved agent name -> recipe `default_agent_name` unless the operator supplied `--agent-name`
- variant id -> canonical recipe selector with each `/` replaced by `-`, for example `claude-gpu-kernel-coder-default` or `codex-gpu-kernel-coder-yunwu-openai`

The persisted demo state and verification report will record at minimum:

- `tool`
- `variant_id`
- `brain_recipe`

Rationale:

- The canonical recipe selector is the clearest operator-facing provenance for both the implicit default Claude launch and explicit recipe launches.
- Recipe-owned default agent names keep launch identity defaults colocated with the rest of the startup composition and let wrapper scripts remain thin conveniences.
- Persisting a canonical selector instead of the raw user input avoids ambiguity when the user typed a basename or included `.yaml`.
- Follow-up commands should only need the workspace state, not repeated variant flags.
- Stable `variant_id` values derived from the canonical selector keep verification fixtures and inspect output easy to reason about even when different tools share the same recipe basename.

Alternative considered:

- Persist the operator's raw `--brain-recipe` value exactly as typed.
- Rejected because basename selectors, optional `.yaml`, and the implicit default Claude path would produce multiple spellings for the same launch variant.

The demo will also treat previously persisted state files that no longer validate under the updated strict `DemoState` schema as stale local state during startup reset. The repo accepts breaking changes here, but startup should still replace stale local state instead of failing before it can establish the new contract.

### 5. Generalize inspect and output-tail plumbing around tool-aware parser selection

The inspect surface will stop depending on Claude-only names and parser selection. The engine will use the persisted `tool` to select the runtime parser stack and expose generic live-state naming such as `tool_state` instead of `claude_code_state`.

`inspect --with-output-text` will use the runtime-owned parser selection path for the selected tool so Claude continues to use the Claude parser and Codex uses the Codex parser.

Rationale:

- The repo already has a unified `ShadowParserStack(tool=...)` abstraction for Claude and Codex.
- Keeping Claude-only field names would make Codex support look bolted on and would leak an implementation mismatch into docs and tests.

Alternative considered:

- Keep `claude_code_state` for compatibility and add parallel Codex-only fields.
- Rejected because the interactive demo pack is an operator surface owned by this repo, and a generic state field is simpler than a provider-specific branch explosion.

### 6. Keep one current-run marker for the whole demo pack

The pack will continue to use one `current_run_root.txt` marker rather than one per tool or variant.

Rationale:

- This preserves the current mental model: one active interactive demo workspace at a time.
- It keeps wrapper behavior and existing follow-up commands simple.

Alternative considered:

- Maintain one current-run marker per tool or per variant.
- Rejected for now because it adds state-management complexity before there is evidence that operators need parallel active demo sessions.

## Risks / Trade-offs

- [Generic inspect field rename] -> Update README, expected reports, and tests together so repo-owned consumers move in one change.
- [Basename lookup could become ambiguous later] -> Allow selectors with subdirectory context and fail basename-only lookup with an explicit ambiguity error when multiple recipes share the same basename. This change intentionally exercises that path by adding `claude/gpu-kernel-coder-default` alongside `codex/gpu-kernel-coder-default`.
- [One shared current-run marker replaces active runs across tools] -> Keep replacement behavior explicit in docs and accept this as part of the current single-active-demo model.
- [Variant/recipe mapping drift] -> Centralize the recipe resolution, recipe-default-name handling, and canonical-selector-to-variant mapping in the Python demo engine and cover them with unit tests.
- [Strict state schema rejects older local state] -> Treat unreadable persisted state as stale local state during startup reset and replace it with freshly written state under the new contract.
- [Parser divergence between tools] -> Reuse the existing runtime parser stack rather than introducing demo-local parser branching.
- [Breaking repo-local invocations during migration] -> Update all in-repo wrappers, docs, tests, and helper references in the same change instead of preserving compatibility code.

## Migration Plan

1. Extend the shared recipe model plus tracked demo recipes with `default_agent_name`, add the missing Claude recipe, and update the demo to resolve recipe metadata in Python.
2. Switch the demo build path to the existing `build-brain --recipe` CLI and retire demo-owned build composition defaults such as `DEFAULT_SKILLS`.
3. Persist the canonical recipe selector plus derived tool and normalized `variant_id` metadata in demo state and report artifacts, and treat stale incompatible state as replaceable during startup reset.
4. Update startup so `--agent-name` overrides the recipe-defined default name, then update inspect and verification flows to use the selected tool and the persisted recipe-backed variant metadata.
5. Update shell wrappers, in-repo callers, and README examples to use the new recipe-first contract directly.
6. Refresh unit and integration coverage for recipe resolution, state replacement, persisted variant behavior, inspect output, and verification snapshots after updating repo-local callers.

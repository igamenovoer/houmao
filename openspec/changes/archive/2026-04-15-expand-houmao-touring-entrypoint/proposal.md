## Why

The packaged `houmao-touring` skill is positioned as the system entrypoint — the README tells first-time users to install skills and invoke `houmao-touring` — but today the skill only offers a linear welcome, a narrow "advanced" branch limited to pairwise loops, no compact glossary, and no quickstart path. First-time users either restart setup from scratch or have to read through multiple downstream skill pages before they can place the vocabulary. Re-orienting users cannot see a compact map of what else Houmao offers beyond the pairwise loop hint.

This change expands `houmao-touring` into a proper entrypoint: a state-adaptive welcome, an explicit posture → branch routing table during orientation, a self-contained concepts glossary, a quickstart branch that adapts to whichever CLI tools the host already has, and an advanced-usage branch that enumerates the broader advanced surface (memory, gateway extras, advanced-usage pattern, credential management, low-level agent definition, generic loops, pairwise loops) with equal weight and no prioritization. All new content lives inside the packaged asset directory so the skill remains self-contained after `pip install`.

## What Changes

- Add a state-adaptive welcome rule to `houmao-touring/SKILL.md` so the full welcome text is shown on a blank-slate workspace and a short one-liner is shown when Houmao state already exists.
- Extend `branches/orient.md` with an explicit posture → next-likely-branch routing table for the common workspace states (blank slate, project only, specialist exists, managed agent running, multi-agent).
- Add a new `branches/quickstart.md` that detects available host CLI tools (for example `claude`, `codex`, `gemini`) via `command -v`, lists what it found without priority, and walks the caller through a minimal specialist-backed launch using the downstream manager skills.
- Expand `branches/advanced-usage.md` to enumerate the broader advanced feature surface (pairwise loops v1 and v2, generic loop, advanced-usage pattern, memory manager, gateway extras such as mail-notifier and reminders, credential manager, low-level agent-definition skill) as a flat brief list with no priority and no recommendation, keeping the existing pairwise loop guidance as one of the entries.
- Add a new `references/concepts.md` as a compact self-contained glossary covering `specialist`, `easy profile`, `launch profile`, `managed agent`, `recipe`, `tool adapter`, `gateway`, `mailbox root`, `principal id`, `user agent`, `master`, `loop plan`, and related vocabulary.
- Add a guardrail to `houmao-touring/SKILL.md` that all touring-skill content must be self-contained inside the packaged asset directory and SHALL NOT reference paths outside `src/houmao/agents/assets/system_skills/houmao-touring/` or files that only exist in the development repository.

## Capabilities

### New Capabilities

- none

### Modified Capabilities

- `houmao-touring-skill`: add requirements for state-adaptive welcome, posture → branch routing matrix, quickstart branch with host-tool detection, broader advanced-usage feature enumeration, self-contained concepts reference, and self-containment of all packaged touring content.

## Impact

- Affected packaged asset directory: `src/houmao/agents/assets/system_skills/houmao-touring/` (SKILL.md, `branches/orient.md`, `branches/advanced-usage.md`, new `branches/quickstart.md`, new `references/concepts.md`).
- Affected specs: `openspec/specs/houmao-touring-skill/spec.md` receives new requirements (no removals).
- Indirect documentation: README `houmao-touring` row may be refreshed to mention the quickstart and features-map entries, but README changes are optional and not required by this change.
- No Python source changes. No dependency changes. No CLI command shape changes. No breaking changes.
- System-skill catalog entry in `src/houmao/agents/assets/system_skills/catalog.toml` remains unchanged.

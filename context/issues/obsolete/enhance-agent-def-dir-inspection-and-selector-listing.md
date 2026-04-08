# Enhancement Proposal: Add Agent-Definition Directory Inspection And Launch-Selector Listing

> Obsolete as of 2026-04-08.
> Moved from `context/issues/enhance/enhance-agent-def-dir-inspection-and-selector-listing.md` to `context/issues/obsolete/`.
> Retained for historical reference only.


## Status
Proposed

## Summary
Add a supported `houmao-mgr` inspection surface that reads the effective agent-definition directory and reports what is available there before launch time.

At minimum, operators should be able to discover:

- the effective agent-definition root currently in use,
- launchable native selectors resolved by `--agents`,
- available provider/tool lanes for those selectors,
- matching recipe paths,
- optional role and blueprint bindings when present, and
- clear validation errors when the directory is missing required structure.

The immediate user-facing goal is to answer questions like "what can I launch from this agent-def dir?" without manually scanning `brains/brain-recipes/`, `roles/`, and `blueprints/`.

## Why
Today `houmao-mgr` can launch from a native selector:

```bash
pixi run houmao-mgr agents launch --agents <selector> --provider <provider> ...
```

but it does not expose a first-class discovery command for the available pre-launch selectors in the effective agent-definition root.

That creates avoidable friction:

- operators have to inspect the filesystem manually to find launchable selectors,
- users can confuse "managed agents currently running" with "agents that are launchable from this repo",
- provider-specific selector availability is not obvious without understanding the resolver rules,
- debugging wrong `AGENTSYS_AGENT_DEF_DIR` values is harder than it should be,
- interactive testing flows have to guess selectors instead of discovering them from the CLI.

The current resolver behavior already encodes a clear discovery contract:

- the effective agent-definition root comes from `AGENTSYS_AGENT_DEF_DIR` or `.agentsys/agents`,
- native selectors are resolved from `brains/brain-recipes/<tool>/`,
- selector names may map through `<selector>.yaml` or `<selector>-default.yaml`,
- optional roles are inferred from `roles/<selector>/system-prompt.md`.

That means the repo already has enough structure to support a reliable inspection command; the missing piece is an operator-facing surface.

## Requested Enhancement
### 1. Add a first-class inspection command
Add one supported `houmao-mgr` command family for agent-definition discovery. The exact naming can change, but it should be something in the spirit of:

```bash
pixi run houmao-mgr brains list
pixi run houmao-mgr brains inspect
```

or:

```bash
pixi run houmao-mgr admin inspect-agent-def-dir
```

The important part is that the command is easy to find and clearly meant for pre-launch discovery rather than post-launch managed-agent state.

### 2. List launchable native selectors
The inspection surface should list selectors that can be passed to:

```bash
pixi run houmao-mgr agents launch --agents <selector> --provider <provider>
```

At minimum, each row or record should include:

- selector name,
- provider or tool lane,
- resolved recipe path,
- whether the selector resolves through `<selector>.yaml` or `<selector>-default.yaml`,
- whether a matching role prompt exists.

### 3. Report the effective agent-definition root explicitly
The command should show which agent-definition directory was used and how it was chosen:

- explicit `AGENTSYS_AGENT_DEF_DIR`, or
- default `.agentsys/agents` under the working directory.

This should make misconfiguration obvious before launch attempts fail.

### 4. Provide structured output
In addition to a human-readable table, support machine-readable output such as JSON so wrappers, demos, and tests can inspect available selectors programmatically.

Example shape:

```json
{
  "agent_def_dir": "/repo/tests/fixtures/agents",
  "source": "AGENTSYS_AGENT_DEF_DIR",
  "selectors": [
    {
      "selector": "projection-demo",
      "provider": "codex",
      "tool": "codex",
      "recipe_path": "brains/brain-recipes/codex/projection-demo-default.yaml",
      "role_name": "projection-demo",
      "has_role_prompt": true
    }
  ]
}
```

Exact field names can change, but the command should expose enough information for non-interactive callers to choose a valid selector confidently.

### 5. Optionally summarize related agent-def content
If the command surface grows slightly beyond selector listing, it should also be able to summarize:

- available roles,
- available blueprints,
- available config profiles and credential profiles referenced by recipes,
- obvious directory validation problems.

This is useful because operators usually want "what is configured here?" rather than only "what filenames exist?".

### 6. Fail clearly on invalid agent-def structure
When the effective agent-definition root is missing required directories or contains ambiguous/broken selector state, the inspection command should fail with explicit validation output.

Examples:

- missing `brains/brain-recipes/<tool>/`,
- unreadable or invalid recipe files,
- duplicate selector resolution ambiguity,
- role path exists but prompt file is missing.

The command should be safer and more informative than waiting for `agents launch` to fail later.

## Acceptance Criteria
1. `houmao-mgr` exposes a supported pre-launch inspection command for the effective agent-definition directory.
2. The command can list launchable native selectors that correspond to `agents launch --agents ...`.
3. The output identifies the effective agent-definition root and whether it came from `AGENTSYS_AGENT_DEF_DIR` or the default location.
4. Human-readable output is available for interactive use.
5. Machine-readable output is available for automation.
6. Provider/tool lane information is included so operators can tell which selectors are valid for which launch provider.
7. Broken or incomplete agent-definition structure fails with clear diagnostics.
8. Docs describe the discovery command and how it relates to `agents launch`, recipes, roles, and blueprints.
9. Tests cover at least one valid listing case and one invalid agent-def error case.

## Likely Touch Points
- `src/houmao/agents/native_launch_resolver.py`
- `src/houmao/srv_ctrl/commands/brains.py`
- `src/houmao/srv_ctrl/commands/admin.py`
- `docs/reference/agents_brains.md`
- `docs/reference/houmao_server_pair.md`
- `tests/fixtures/agents/README.md`
- CLI tests covering selector discovery and invalid directory handling

## Non-Goals
- No requirement to launch or validate every listed selector during inspection.
- No requirement to replace `agents list`, which should remain the post-launch managed-agent view.
- No requirement to expose secret credential contents.
- No requirement to build a full interactive TUI browser for agent-def data in the first step.

## Suggested Direction
- Keep the first implementation read-only and local.
- Reuse the existing selector-resolution rules rather than inventing a second discovery contract.
- Prefer one clear, supported command over asking operators to scan the filesystem manually.
- Make the JSON output stable enough for tutorial packs, wrappers, and tests to consume.

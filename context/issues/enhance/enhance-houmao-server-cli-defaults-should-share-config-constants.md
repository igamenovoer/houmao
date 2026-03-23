# Enhancement Proposal: Houmao Server CLI Defaults Should Share Config Constants

## Status
Proposed

## Summary
`houmao-server serve` currently repeats several default values that also exist in `HoumaoServerConfig`. The duplication is understandable because the CLI layer and the config model each need their own defaulting behavior, but the current form uses repeated literals instead of one canonical source.

That creates a quiet drift risk. A default can be changed in one place and forgotten in the other, which then makes CLI help, runtime behavior, and direct config construction disagree.

The system should keep separate defaulting responsibilities while removing repeated magic values. The likely direction is to define shared server-default constants and use them from both the Click options and `HoumaoServerConfig`.

## Why
The current structure has two valid consumers of defaults:

- the Click CLI needs defaults so omitted options resolve predictably and `--help` shows the correct value,
- the config model needs defaults so non-CLI construction paths such as `HoumaoServerConfig()` and `create_app(config=None)` behave consistently.

Those two needs do not require duplicated literals.

Today the `serve` command and `HoumaoServerConfig` both carry simple scalar defaults for values such as:

- `api_base_url`
- `watch_poll_interval_seconds`
- `recent_transition_limit`
- `completion_stability_seconds`
- `unknown_to_stalled_timeout_seconds`
- `startup_child`

This is already enough surface area for accidental mismatch. The recent `watch_poll_interval_seconds` default change is a concrete example of the kind of update that has to be remembered in more than one place.

The problem is not that both layers define defaults. The problem is that they define them independently with repeated literals.

## Proposed Direction

### 1. Introduce one canonical source for simple server defaults
Define explicit shared constants for scalar `houmao-server` defaults.

Example shape:

```python
DEFAULT_HOUMAO_SERVER_API_BASE_URL = "http://127.0.0.1:9889"
DEFAULT_WATCH_POLL_INTERVAL_SECONDS = 0.5
DEFAULT_RECENT_TRANSITION_LIMIT = 24
```

The exact constant names and module location can be decided later, but they should be normal application constants rather than values extracted indirectly from Pydantic field metadata.

### 2. Use those constants from both the CLI and the config model
The Click options in `serve.py` should reference the shared constants.

`HoumaoServerConfig` should also reference the same constants for its field defaults.

This preserves:

- correct CLI help output,
- correct behavior for omitted CLI flags,
- correct behavior for direct non-CLI config construction.

### 3. Keep special cases explicit instead of forcing everything into one pattern
Not every field has the same defaulting shape.

Examples:

- `runtime_root` uses CLI `None` plus runtime resolution logic and also has a config `default_factory`
- `supported_tui_processes` is an override-style CLI input while the config model owns the default process map

The enhancement should focus on repeated scalar defaults first instead of flattening all config behavior into one abstraction.

### 4. Avoid introspecting Pydantic model fields to discover defaults
Although the CLI could technically read `HoumaoServerConfig.model_fields[...]`, that is a weak coupling point.

The preferred design is:

- shared constants as the canonical values,
- the config model consumes those constants,
- the CLI consumes those constants.

This is clearer than making the CLI depend on Pydantic internals for help text and option defaults.

## Acceptance Criteria
1. Repeated scalar defaults used by both `houmao-server serve` and `HoumaoServerConfig` come from one shared canonical source.
2. The `serve` CLI help continues to show the correct defaults.
3. Direct `HoumaoServerConfig()` construction continues to produce the same effective defaults as the CLI path when options are omitted.
4. The refactor does not force `runtime_root` and `supported_tui_processes` into an unnatural single-default pattern.
5. Docs or code comments make it clear why both layers still declare defaults while sharing the same values.

## Likely Touch Points
- `src/houmao/server/config.py`
- `src/houmao/server/commands/serve.py`
- `src/houmao/server/commands/common.py`
- optional tests covering config defaults and CLI help/default behavior

## Non-Goals
- No change to the semantics of any existing default in this proposal alone.
- No requirement to redesign Click option parsing or Pydantic model construction.
- No requirement to unify complex default factories and override-only CLI inputs under one mechanism.
- No requirement to implement environment-variable or config-file precedence changes as part of this cleanup.

## Suggested Follow-Up
1. Inventory all scalar defaults duplicated between `serve.py` and `HoumaoServerConfig`.
2. Introduce shared constants for those values.
3. Update CLI and config consumers to use the constants.
4. Add a focused test that would fail if the CLI and config model drift on one of those shared defaults in the future.

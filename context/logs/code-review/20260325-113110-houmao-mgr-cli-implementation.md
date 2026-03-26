# Code Review: `houmao-mgr` CLI Implementation

**Date**: 2026-03-25
**Reviewer**: Claude (automated review)
**Scope**: `src/houmao/srv_ctrl/` — the full `houmao-mgr` CLI surface (entry point, command groups, managed-agent helpers, runtime-artifact materialization, passthrough)

## 1. Overview

`houmao-mgr` is the pair-management CLI for the Houmao agent framework, providing operator-facing control over `houmao-server` and locally launched managed agents. It replaces the deprecated `cao-server + cao` toolchain.

**Files reviewed** (14 source files, 4 test files):

| File | Lines | Role |
|---|---|---|
| `cli.py` | 7 | Re-export entry point |
| `__init__.py` | 6 | Package re-export |
| `commands/main.py` | 37 | Click root group and `main()` wrapper |
| `commands/common.py` | 268 | Shared helpers (emit, resolve, validate) |
| `commands/server.py` | 219 | Server lifecycle (`start`, `stop`, `status`, `sessions`) |
| `commands/brains.py` | 184 | Local brain construction (`build`) |
| `commands/admin.py` | 56 | Maintenance (`cleanup-registry`) |
| `commands/agents/__init__.py` | 7 | Agents package re-export |
| `commands/agents/core.py` | 217 | Core agent commands (`launch`, `list`, `show`, `state`, `history`, `prompt`, `interrupt`, `stop`) |
| `commands/agents/gateway.py` | 222 | Gateway lifecycle and request commands |
| `commands/agents/mail.py` | 132 | Mailbox operations (`status`, `check`, `send`, `reply`) |
| `commands/agents/turn.py` | 85 | Headless turn inspection (`submit`, `status`, `events`, `stdout`, `stderr`) |
| `commands/managed_agents.py` | 1196 | Shared managed-agent discovery, state inspection, and dual-path control |
| `commands/runtime_artifacts.py` | 327 | Server-backed launch artifact materialization |
| `commands/passthrough.py` | 25 | CAO compatibility passthrough |

**Tests**:
- `tests/unit/srv_ctrl/test_commands.py` — 5 unit tests
- `tests/unit/srv_ctrl/test_managed_agents.py` — 3 unit tests
- `tests/unit/srv_ctrl/test_runtime_artifacts.py` — 1 unit test
- `tests/integration/srv_ctrl/test_cli_shape_contract.py` — 2 integration tests

## 2. Strengths

1. **Clear authority separation**: Commands are cleanly divided by authority — `server` for process lifecycle, `agents` for managed-agent control, `brains` for offline construction, `admin` for local maintenance. The separation maps 1:1 to the mental model a human operator would hold.

2. **Registry-first discovery with graceful server fallback**: `resolve_managed_agent_target()` first checks the shared registry for local records, then falls back to the server. This allows local-only agents to be controllable even when no server is running — a solid design for the pair architecture.

3. **Consistent JSON output convention**: Every command emits structured JSON via `emit_json()`, making the CLI trivially scriptable. The Pydantic-aware serialization path (`model_dump(mode="json")`) keeps output stable.

4. **Strong type discipline**: Pydantic v2 models for all external payloads, frozen dataclasses for internal value objects, typed `ParamSpec`/`TypeVar` generics for the decorator helpers. This aligns well with the project's mypy-strict convention.

5. **Dual-path (server vs. local) control**: The `ManagedAgentTarget` abstraction cleanly encapsulates whether a command routes through the server REST API or the local runtime controller. Each public function in `managed_agents.py` consistently branches on `target.mode`.

6. **Good integration test coverage for the launch-to-control lifecycle**: `test_cli_shape_contract.py::test_houmao_mgr_agents_launch_supports_registry_first_local_control` exercises the full `launch -> list -> state -> stop` path with a fake headless backend, giving confidence in the registry-publish-and-resume pipeline.

## 3. Issues and Suggestions

### 3.1 Critical / High Priority

#### 3.1.1 `assert` used for runtime invariants in production code (`managed_agents.py`)

Throughout `managed_agents.py`, `assert target.client is not None` and `assert target.controller is not None` guard mode-dependent branches (lines 201, 203, 215, 216, 243, 246, 281, 306, 322, 338, 349, 363, 384, 402, 413, 451, 490, 527, 547, 554, 580, 610, 637). Python `assert` statements are stripped when Python is run with `-O` (optimize mode), meaning these guards silently disappear and the code would raise `AttributeError` on `None` instead of a clear invariant violation.

**Suggestion**: Replace each `assert` with an explicit guard:
```python
if target.client is None:
    raise click.ClickException("Internal error: server mode target is missing a pair client.")
```
Or, if the branch truly is unreachable, use a narrow helper:
```python
def _require_client(target: ManagedAgentTarget) -> HoumaoServerClient:
    if target.client is None:
        raise RuntimeError("server-mode target missing client")
    return target.client
```
This also eliminates the type-narrowing gap that mypy can sometimes miss through bare `assert`.

#### 3.1.2 File handle leak in `resolve_body_text` (`common.py:219`)

```python
value = open(body_file, encoding="utf-8").read()
```

The file is opened but never explicitly closed. While CPython's reference-counting GC will close it promptly, this is a lint violation (ruff `SIM115` / `B007`) and a real leak risk on alternate runtimes (PyPy).

**Suggestion**: Use a `with` statement or `Path.read_text()`:
```python
value = Path(body_file).read_text(encoding="utf-8")
```

#### 3.1.3 Fragile `getattr` fallback chains in `admin.py:36-42`

```python
removed_agent_ids = tuple(
    getattr(result, "removed_agent_ids", getattr(result, "removed_agent_keys", ()))
)
```

This three-deep `getattr` chain across two possible attribute names suggests the upstream return type is not stable. If the attribute API of `cleanup_stale_live_agent_records` changes again, this code silently returns empty tuples instead of failing.

**Suggestion**: Pin the expected return type. If the upstream function returns a typed dataclass, type-annotate `result` and access attributes directly. If a migration is in progress, add a single adapter function with a deprecation comment, rather than scattering `getattr` chains.

### 3.2 Medium Priority

#### 3.2.1 `managed_agents.py` is ~1200 lines and growing — consider splitting

This file is the largest in the CLI layer and serves three distinct purposes:
1. **Target resolution** (`resolve_managed_agent_target`, `list_managed_agents`, `_list_registry_identities`, etc.)
2. **Public command helpers** (prompt, interrupt, stop, gateway, mail, headless-turn)
3. **Local headless-turn artifact inspection** (~200 lines of `_snapshot_from_turn_dir`, `_list_local_headless_turns`, `_load_turn_events`, etc.)

**Suggestion**: Split into 2-3 modules:
- `managed_agents.py` — target resolution and identity helpers
- `managed_agent_commands.py` — public dual-path command implementations
- `managed_agent_local_turns.py` — local headless-turn snapshot inspection

This would improve navigability and reduce merge conflicts.

#### 3.2.2 Duplicated pair-verification logic across `server.py` commands

Both `status_server_command` (line 81-85) and `stop_server_command` (line 130-134) perform the same `health.houmao_service != "houmao-server"` check with the same error message. This is already extracted as `require_supported_houmao_pair()` in `common.py`, but `status` and `stop` intentionally bypass it to handle the "no server running" case differently.

**Suggestion**: Extract a `_require_houmao_service(health: HoumaoHealthResponse) -> None` guard that raises if the service is not `houmao-server`, and call it after the health check succeeds. This eliminates the three near-identical error-message strings.

#### 3.2.3 `_PROVIDERS_REQUIRING_WORKSPACE_ACCESS` is identical to `_PROVIDERS` (`agents/core.py:33-45`)

```python
_PROVIDERS = frozenset({"claude_code", "codex", "gemini_cli"})
_PROVIDERS_REQUIRING_WORKSPACE_ACCESS = frozenset({"claude_code", "codex", "gemini_cli"})
```

These two frozen sets are currently identical, which means the trust confirmation always triggers. If the intent is that some future provider will not need workspace access, the forward-looking design is fine — but it should have a brief comment explaining the distinction. Otherwise, remove the redundant set and simplify.

**Suggestion**: Add a one-line comment: `# Subset of _PROVIDERS that read/write the working directory. Currently all of them.`

#### 3.2.4 Broad exception catch in `require_supported_houmao_pair` (`common.py:64`)

```python
except Exception as exc:
    raise click.ClickException(...) from exc
```

Catching `Exception` is overly broad — it will swallow `KeyboardInterrupt` cousins via `BaseException` subclasses that inherit from `Exception`, programming errors (e.g., `TypeError`, `AttributeError`), etc. The intent is to catch connection failures.

**Suggestion**: Narrow the catch to `(ConnectionError, OSError, httpx.HTTPError)` or whatever the underlying `HoumaoServerClient.health_extended()` can raise on connection failure.

#### 3.2.5 `_completion_source_from_stdout` reads the entire event file twice

In `_snapshot_from_turn_dir`, line 1046 calls `_completion_source_from_stdout()` which re-loads `load_headless_turn_events(stdout_path)`. If `headless_turn_events()` is later called on the same snapshot, the same file is loaded a third time.

**Suggestion**: Load events once in `_snapshot_from_turn_dir` and derive `completion_source` from the loaded list. Pass the preloaded events into the snapshot or compute `completion_source` lazily.

#### 3.2.6 `ManagedAgentTarget.mode` is a raw `str` — should be a `Literal`

```python
@dataclass(frozen=True)
class ManagedAgentTarget:
    mode: str  # "server" | "local"
```

Using a raw `str` means typos in mode checks (`target.mode == "servr"`) are silently wrong.

**Suggestion**: Use `Literal["server", "local"]` or a `StrEnum`:
```python
from typing import Literal
mode: Literal["server", "local"]
```

#### 3.2.7 Inconsistent return type annotations in public functions of `managed_agents.py`

- `prompt_managed_agent()` returns `object` (line 268)
- `mail_status()` returns `object` (line 406)
- `mail_check()` returns `object` (line 434)
- `mail_send()` returns `object` (line 471)
- `mail_reply()` returns `object` (line 510)

Other functions return specific Pydantic models. The `object` return type defeats downstream type checking.

**Suggestion**: Return a union of the actual types (e.g., `HoumaoManagedAgentRequestAcceptedResponse | dict[str, Any]`) or introduce a thin wrapper model for the local-mode mail/prompt responses.

### 3.3 Low Priority / Style

#### 3.3.1 Module docstring in `__init__.py` says "CAO-compatible"

```python
"""CAO-compatible Houmao service-management CLI package."""
```

Given the rename from `houmao-srv-ctrl` to `houmao-mgr` and the explicit rejection of mixed CAO pairs, this docstring is misleading.

**Suggestion**: Update to `"""Houmao pair-management CLI package (`houmao-mgr`)."""`

#### 3.3.2 `_CAO_DEFAULT_PORT` naming in `common.py`

The constant `_CAO_DEFAULT_PORT` (line 19) and env var `CAO_PORT` are CAO-era names. The CLI itself rejects mixed CAO usage. This is confusing for anyone reading the code fresh.

**Suggestion**: Either rename to `_DEFAULT_PAIR_PORT` / `HOUMAO_PAIR_PORT` and add a compatibility alias, or at minimum add a comment: `# Legacy name; kept for backward-compatible env-var lookup.`

#### 3.3.3 `passthrough.py` has no callers

`passthrough_command()` creates one Click command that delegates to the installed `cao` executable. No file in the codebase calls this function or registers any passthrough command.

**Suggestion**: If this is dead code left from the `houmao-srv-ctrl` rename, remove it. If it is planned for future use, add a `# TODO` comment.

#### 3.3.4 `cli.py` and `__init__.py` are near-identical re-exports

Both files re-export `main` from `commands.main`. `cli.py` exists solely because `pyproject.toml` points at `houmao.srv_ctrl.cli:main`. The `__init__.py` export is unused externally.

**Suggestion**: Either remove the `__init__.py` re-export or merge the two into a single entry point. Having both is not harmful but is mildly confusing.

#### 3.3.5 Missing `__init__.py` for `tests/integration/srv_ctrl/`

The test directory `tests/integration/srv_ctrl/` has no `__init__.py`. While pytest discovers tests without it, adding one aligns with the rest of the test tree and prevents import-path shadowing.

#### 3.3.6 Local import pattern in `prompt_managed_agent` and `interrupt_managed_agent`

Several functions use local imports inside function bodies:
```python
def prompt_managed_agent(...):
    ...
    from houmao.server.models import HoumaoManagedAgentSubmitPromptRequest
```

This avoids a circular import or reduces startup cost, but the pattern is inconsistent — other functions in the same file import from `houmao.server.models` at the module top level (line 56-79). If the circular import risk is real, all related imports should be deferred; if not, move them to the top.

**Suggestion**: Audit whether these models truly cause a circular import. If they do, consolidate all deferred imports into a `_lazy_imports()` helper or a `TYPE_CHECKING` block. If they don't, move them to the top with the other server model imports.

## 4. Test Coverage Assessment

| Area | Unit | Integration | Gap |
|---|---|---|---|
| CLI shape (command inventory) | 1 test | - | Adequate |
| `server status/stop/sessions` | 2 tests | 1 test | Adequate |
| `agents launch` | 1 test | 1 test | Adequate for happy path; no test for build failure or session-start error |
| `agents list/state/show/stop` | - | covered by integration | Could use unit tests for the dual-path local/server branching |
| `agents prompt/interrupt` | - | - | **No dedicated test** — only covered indirectly |
| `agents gateway *` | - | - | **No test** for gateway attach, detach, prompt, interrupt, status |
| `agents mail *` | - | - | **No test** for mail send/check/reply/status |
| `agents turn *` | - | - | **No test** for headless turn submit/status/events/stdout/stderr |
| `brains build` | - | - | **No test** |
| `admin cleanup-registry` | - | - | **No test** |
| `managed_agents` dual-path | 3 tests | - | Good for resolution; no unit tests for local-mode prompt/stop/interrupt |
| `runtime_artifacts` | 1 test | - | Adequate for `materialize_delegated_launch` |
| `passthrough` | - | - | No test (dead code) |

**Key gaps**: `agents gateway`, `agents mail`, `agents turn`, `brains build`, and `admin cleanup-registry` have zero test coverage at either level.

## 5. Summary of Recommendations (prioritized)

| Priority | Item | Section |
|---|---|---|
| High | Replace `assert` with explicit guards in `managed_agents.py` | 3.1.1 |
| High | Fix file handle leak in `resolve_body_text` | 3.1.2 |
| High | Stabilize `getattr` fallback chains in `admin.py` | 3.1.3 |
| Medium | Split `managed_agents.py` (~1200 lines) into focused modules | 3.2.1 |
| Medium | Narrow `except Exception` to connection-specific exceptions | 3.2.4 |
| Medium | Type `ManagedAgentTarget.mode` as `Literal["server", "local"]` | 3.2.6 |
| Medium | Tighten return types from `object` to specific models | 3.2.7 |
| Medium | Deduplicate pair-verification logic in `server.py` | 3.2.2 |
| Medium | Avoid re-reading turn event files multiple times | 3.2.5 |
| Low | Update stale CAO-era naming (`_CAO_DEFAULT_PORT`, docstrings) | 3.3.1, 3.3.2 |
| Low | Remove or annotate dead `passthrough.py` | 3.3.3 |
| Low | Add tests for `gateway`, `mail`, `turn`, `brains build`, `admin` | 4 |

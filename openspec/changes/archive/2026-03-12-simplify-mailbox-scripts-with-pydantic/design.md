## Context

The projected mailbox helper scripts under `src/gig_agents/mailbox/assets/rules/scripts/` are intentionally small wrappers, but the shared implementation in `src/gig_agents/mailbox/managed.py` carries a large amount of hand-written payload parsing and validation logic. That module currently defines request dataclasses with custom `from_payload()` loaders plus many helper validators for strings, booleans, timestamps, message ids, nested principal payloads, and attachment payloads.

That design now sits next to two signals that point in a different direction:

- the projected mailbox dependency manifest already declares `pydantic`,
- the repository already uses strict pydantic models in mailbox protocol parsing and in runtime boundary validation.

Because the mailbox rules bundle is projected into shared mailbox roots, each dependency listed in `rules/scripts/requirements.txt` becomes part of the mailbox-local protocol contract. That makes dependency additions expensive, but it also means already-declared dependencies should earn their keep. In this case, `pydantic` can simplify the managed mailbox boundary substantially without changing mailbox transport semantics.

## Goals / Non-Goals

**Goals:**

- Use `pydantic` as the single schema-validation layer for Python managed mailbox helper payloads.
- Remove duplicated hand-written payload parsing and validation helpers from the managed mailbox layer.
- Keep the mailbox helper invocation contract stable: `--mailbox-root`, `--payload-file`, and one JSON object written to stdout.
- Keep mailbox filesystem layout, SQLite behavior, lock acquisition order, and success-result semantics unchanged.
- Keep the projected mailbox dependency contract explicit and minimal.

**Non-Goals:**

- No mailbox protocol version bump, SQLite schema change, or mailbox root migration.
- No change to runtime mail command behavior or mailbox routing semantics.
- No adoption of an ORM, query builder, or alternative lock library.
- No requirement to adopt `typer` or any new CLI framework for the wrapper scripts.
- No introduction of a second validation stack such as `msgspec`, `attrs`, or marshmallow.

## Decisions

### 1) Replace managed request dataclasses with strict pydantic models

The managed mailbox layer will use strict pydantic models for request payloads instead of frozen dataclasses with `from_payload()` constructors.

At minimum, this applies to the delivery, mailbox-state mutation, repair, registration, and deregistration request types. Nested principal and attachment payloads should also validate through shared typed models rather than untyped `dict[str, object]` payload fragments.

Where the canonical mailbox protocol models already express the right semantics, the managed layer should reuse them directly or reuse their validator helpers. Where managed operations need different constraints, such as filesystem-path-safe mailbox addresses or local mailbox-path requirements, the managed layer should define managed-specific pydantic models on top of those shared scalar validators.

Rationale:

- this removes a large amount of manual parsing code,
- it aligns the mailbox scripts with the repository's existing pydantic-backed boundary style,
- it makes nested validation and field-path error reporting much easier to keep consistent.

Alternatives considered:

- Keep manual dataclasses and helper functions. Rejected because it preserves duplication and makes every new script payload expensive to add safely.
- Add a different schema library such as `msgspec` or marshmallow. Rejected because the repo already standardizes on `pydantic` in adjacent boundary layers.

### 2) Keep database and filesystem mutation logic explicit

This change will simplify the mailbox boundary layer, not replace the operational core. SQLite statements, transaction boundaries, filesystem artifact creation, symlink projection, repair behavior, and lock acquisition should remain explicit Python logic.

Rationale:

- the mailbox code is heavily coupled to precise transaction timing and filesystem side effects,
- raw SQL and explicit filesystem operations are currently easier to reason about than adding ORM or lock-library abstraction,
- the biggest maintainability problem today is validation and boundary parsing, not the mutation logic itself.

Alternatives considered:

- Introduce `sqlalchemy`, `sqlmodel`, or another higher-level data layer. Rejected because it adds more abstraction than value for this local, protocol-heavy code path.
- Introduce a lock helper package. Rejected because the mailbox contract intentionally exposes visible `.lock` files under the shared mailbox root.

### 3) Keep the wrapper script surface stable and centralize common execution glue

The projected wrapper scripts should keep their current operational contract, but their shared execution glue should be centralized so each wrapper does not repeat the same argument parsing, payload loading, validation, error conversion, and JSON emission flow.

The success-path shape remains one JSON object to stdout. Validation or operational failures should also remain one JSON object to stdout with `ok: false`, but malformed payloads should surface structured, field-aware error text rather than ad hoc messages built from many local helpers.

Rationale:

- the wrappers are mailbox-managed protocol surface and should remain predictable,
- shared execution glue reduces boilerplate without forcing a new CLI framework into the mailbox dependency contract,
- this preserves compatibility with existing runtime expectations and tests.

Alternatives considered:

- Adopt `typer` for all mailbox wrapper scripts. Considered, but not selected as a required part of this design because the wrappers only expose a very small flag surface today.

### 4) Treat `rules/scripts/requirements.txt` as the exact managed helper dependency contract

The projected dependency manifest should stay aligned with the Python imports used by the managed helper set. `pydantic` becomes a required and intentional part of that contract rather than a nominal or unused dependency entry.

Where dependency versions must be expressed in `rules/scripts/requirements.txt`, the manifest should use lower-bound-only requirements such as `pydantic>=2.12` rather than exact pins or upper-bounded ranges. This keeps the projected helper set explicit about minimum supported versions without needlessly constraining mailbox-local environments that already satisfy newer compatible versions.

`PyYAML` remains part of the dependency contract because canonical mailbox message parsing and serialization still rely on YAML front matter helpers in the mailbox protocol module.

Rationale:

- mailbox-local helper dependencies are part of the shared operational contract published into mailbox roots,
- dependency drift between code and `requirements.txt` creates operator confusion and brittle runtime behavior,
- lower-bound-only requirements communicate the tested floor without turning the mailbox-local manifest into a tightly pinned environment file,
- keeping the list short reduces agent-side or operator-side installation burden.

Alternatives considered:

- Add several convenience packages for CLI, front matter, SQL, or locking. Rejected because the simplification payoff is small compared with increasing the mailbox-local dependency surface.

## Risks / Trade-offs

- [Risk] Stricter payload validation may reject malformed inputs that previously slipped through. → Mitigation: keep models aligned with the currently intended payload shapes and add regression tests for accepted payloads plus explicit tests for failure paths.
- [Risk] Reusing canonical mailbox models directly may over-constrain managed helper payloads. → Mitigation: introduce managed-specific models or annotated scalar types where managed flows need stronger filesystem-path or operation-specific validation.
- [Risk] Validation error wording will become more structured and may change exact message text. → Mitigation: keep the contract at the level of explicit field-aware validation failures and update tests to assert stable high-level content rather than fragile full-string matches.
- [Risk] Centralizing wrapper execution glue could accidentally blur script-specific behavior. → Mitigation: keep each wrapper's request model and handler explicit while only deduplicating the common parse/emit/error path.

## Migration Plan

No mailbox data migration is required. The change does not alter canonical message files, mailbox directory layout, lock layout, or SQLite schema.

Deployment consists of shipping the updated package build and re-materializing or validating mailbox roots so the projected `rules/scripts/` files and `requirements.txt` reflect the new implementation. Rollback is straightforward: restore the previous package version and re-materialize the prior mailbox-managed assets if necessary.

## Open Questions

- Should the implementation model only request payloads with pydantic, or should success-result payloads also be represented with pydantic models for consistency? The proposal does not require result models, but they may further reduce ad hoc JSON shaping.

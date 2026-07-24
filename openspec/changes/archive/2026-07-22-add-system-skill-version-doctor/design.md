## Context

Houmao 1.2.1 packages six standalone public system skills. Managed agent homes normally receive the four-member agent pack through the v4 lifecycle, while operators can also copy roots or use the external Skills CLI. Lifecycle-managed homes have a v2 receipt with package version and content digests. External installations do not.

The portable unit visible in every installation method is each root `SKILL.md`. Its YAML frontmatter already identifies the skill, but it does not identify the Houmao release that authored the file. The sixteen shared children use `SKILL-MAIN.md` and are versioned as content owned by the shared root.

The current `system-skills status` command reports receipt ownership and content integrity. It is not a general health command for receiptless installations, and no `system-skills doctor` command exists. Managed-agent registry records identify the tool and runtime manifest; the associated brain manifest records the persistent tool home.

## Goals / Non-Goals

**Goals:**

- Put exact Houmao release identity in every standalone public system skill.
- Keep one version authority for a standalone tree, including its owned commands, references, assets, scripts, and child routines.
- Diagnose expected pack completeness, installed content integrity, frontmatter validity, and version equality without mutation.
- Support explicit tool homes and convenient managed-agent targeting.
- Diagnose copy, symlink, lifecycle-managed, and receiptless external installations.
- Keep release artifacts synchronized with the project version.

**Non-Goals:**

- Do not version parent-scoped children independently.
- Do not add compatibility ranges, dependency solving, upgrade negotiation, or automatic repair.
- Do not reject installation, launch, join, prompt generation, or skill execution because of version metadata.
- Do not change v4 manifest records, v2 receipts, pack membership, or projection transactions.
- Do not version legacy skills, generated execplan skills, or `houmao-auto-system-prompt` in this change.

## Decisions

### 1. Use a Quoted Literal in the Six Standalone Roots

Each public root `SKILL.md` will contain this YAML frontmatter field:

```yaml
houmao_version: "1.2.1"
```

The value must equal the `[project].version` string in `pyproject.toml` for source and distribution validation. Quoting prevents YAML parsers from coercing numeric-looking releases. The field belongs only to the six roots listed by the v4 static manifest. Everything below one root inherits that root's release identity.

An alternative was adding versions to manifest records or only to the receipt. Those locations cannot identify receiptless copy and Skills CLI installations. Per-child versions were rejected because children are not independently installed release units.

### 2. Keep Static Files Static and Validate Release Synchronization

The build and install paths will copy or link the checked-in bytes. They will not inject the running package version. A small source checker will read `pyproject.toml`, enumerate the exact six manifest roots, parse each top-level frontmatter block, and require one matching string value.

Unit tests will cover the same invariant. Distribution tests will inspect wheel and sdist copies. The release workflow will run the checker before building, and the local `build-dist` workflow will expose the same failure early.

An alternative was runtime or build-time template rendering. That would make source directories differ from installed artifacts and would break static copy-paste installation.

### 3. Isolate Diagnostic Parsing from Lifecycle Enforcement

A dedicated read-only diagnostic layer will parse installed `SKILL.md` frontmatter. It will not add version checks to manifest loading, staging, install, sync, upgrade, status, brain building, managed launch, relaunch, rebuild, join, or generated prompts.

The parser will require a YAML mapping, a matching non-empty `name`, and a non-empty string `houmao_version`. It will retain the observed string exactly. Version comparison uses exact string equality with `houmao.version.get_version()`. PEP 440 parsing can improve malformed-version diagnostics, but normalization will not turn unequal source strings into a match.

This separation makes the metadata informative. A stale or malformed version never blocks lifecycle mutation or agent operation.

### 4. Doctor Checks an Explicit Expected Pack

Doctor will inspect a deterministic expected set instead of guessing from directories. It accepts repeatable `--pack admin|agent`; omission defaults to `agent`, matching its per-agent diagnostic purpose.

Two target modes are supported:

- Explicit home mode uses `--tool <tool>` and the existing optional `--home <path>` resolution.
- Managed-agent mode uses exactly one of `--agent-id` or `--agent-name`. It resolves one known local registry record, reads its session and brain manifests, and obtains the authoritative tool and home. It rejects ambiguous names, external agents, missing manifests, and combinations with `--tool` or `--home`.

Managed-agent mode can inspect a stopped agent when its registry and persistent home evidence remain valid. It does not require a live gateway or TUI session.

An alternative was inferring expected packs only from the receipt. Receiptless installations would then lack a checkable expectation. Another alternative was checking every known skill directory, which would not detect a missing expected root.

### 5. Report Integrity and Version as Separate Dimensions

For each expected standalone skill, doctor reports:

- name, role, expected packs, and destination;
- installation integrity such as `absent`, `complete`, `incomplete`, `drifted`, or `conflicting`;
- observed `houmao_version` when readable;
- version status: `match`, `mismatch`, `missing`, `invalid`, or `unavailable`;
- concise issue details.

Integrity checks reuse static manifest expectations and tree digests where possible. Receipt presence adds ownership evidence, but receipt absence alone does not make an external installation unhealthy. Shared routines also require the exact sixteen `SKILL-MAIN.md` children.

The aggregate is healthy only when every expected root is structurally complete, content-compatible with the running package, and version-matched. A running package version of `0+unknown` produces `unavailable`, not a false match.

Plain output summarizes the target and expected release, then lists failures. Structured output includes every member for automation. Healthy diagnostics exit with code 0; detected health failures exit with code 1. Click usage and target-resolution errors retain code 2. These exit codes affect only doctor.

### 6. Keep Receipt and Existing Status Semantics Unchanged

The v2 receipt continues to record the package version captured at lifecycle mutation plus per-tree digests. Doctor reads installed frontmatter even when a receipt exists. It can show receipt evidence, but it does not treat the receipt package version as the installed skill version.

No receipt migration is required. Older installed roots will report `missing` until an operator chooses to upgrade or reinstall them. Existing `status` output remains focused on ownership and content integrity.

## Risks / Trade-offs

- [Release bump misses one root] → Run the exact-six synchronization checker in tests, local distribution builds, and the tagged release build.
- [User edits `houmao_version` without updating content] → Report version and digest integrity separately; require both for healthy doctor output.
- [Receiptless installations cannot prove ownership] → Use explicit expected packs and direct installed-tree checks; label receipt evidence separately.
- [Managed-agent registry points to stale manifests] → Fail target resolution clearly and allow explicit `--tool` plus `--home` fallback.
- [Exact version equality is stricter than compatibility] → Keep it diagnostic only. This change intentionally does not define compatibility ranges.
- [A valid policy installs both packs in an agent home] → Allow repeatable explicit `--pack`; doctor checks the caller's declared expectation.

## Migration Plan

1. Add `houmao_version: "1.2.1"` to the six checked-in roots and add release synchronization checks.
2. Add the diagnostic parser, result models, target resolution, CLI command, renderers, and tests.
3. Update distribution and release checks, then document doctor and the non-enforcement boundary.
4. Publish the next Houmao release with versioned static roots. Existing installations remain usable.
5. Operators may run doctor and explicitly reinstall or upgrade unhealthy homes. Doctor performs no repair itself.

Rollback removes doctor and the synchronization checks. The extra YAML key is harmless to standard skill consumers and can remain during rollback.

## Open Questions

None. The requested behavior fixes exact release equality as a diagnostic signal rather than a compatibility policy.

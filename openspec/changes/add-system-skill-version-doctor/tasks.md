## 1. Versioned Static Skill Sources

- [x] 1.1 Add quoted `houmao_version: "1.2.1"` frontmatter to each of the six public standalone `SKILL.md` roots without changing descriptions, activation metadata, routing, or skill meaning.
- [x] 1.2 Confirm that all sixteen shared `SKILL-MAIN.md` children, legacy skills, generated skill templates, project-authored fixtures, and `houmao-auto-system-prompt` remain outside the version contract.
- [x] 1.3 Add a strict reusable top-level skill frontmatter parser that detects missing files, malformed delimiters or YAML, duplicate keys, mismatched names, missing or non-string versions, and malformed release strings.
- [x] 1.4 Keep version parsing out of static manifest loading and all lifecycle mutation preflight paths so version metadata remains diagnostic only.

## 2. Release Synchronization

- [x] 2.1 Add a source checker that reads `[project].version` from `pyproject.toml`, enumerates exactly the six public manifest roots, and validates exact quoted `houmao_version` equality.
- [x] 2.2 Make the source checker report each failing skill, observed value or parse problem, and expected project version without rewriting any file.
- [x] 2.3 Add a Pixi task and local distribution-build prerequisite for the version synchronization check.
- [x] 2.4 Update the tagged PyPI release workflow to run the source checker before building wheel and sdist artifacts.
- [x] 2.5 Extend distribution tests to verify all six wheel and sdist root versions and the absence of version metadata from all shared child entrypoints.

## 3. Doctor Diagnostic Core

- [x] 3.1 Add typed doctor target, member, receipt-evidence, and aggregate result models with separate integrity and version status fields.
- [x] 3.2 Resolve repeatable expected packs through the v4 manifest, default omitted doctor selection to `agent`, and deduplicate overlapping standalone roots.
- [x] 3.3 Implement receipt-independent destination checks for expected top-level directories, canonical `SKILL.md`, matching skill names, complete tree shape, and packaged-source digest compatibility.
- [x] 3.4 Require `houmao-shared-routines` to contain exactly the sixteen expected `SKILL-MAIN.md` child entrypoints during doctor inspection.
- [x] 3.5 Compare each observed version exactly with `houmao.version.get_version()` and classify `match`, `mismatch`, `missing`, `invalid`, and `unavailable` independently from integrity.
- [x] 3.6 Include current, absent, legacy, corrupt, or unsupported receipt evidence when available without using receipt `package_version` as the observed skill version.
- [x] 3.7 Treat a complete receiptless copy or Skills CLI installation as eligible for healthy results when direct structure, digest, and version checks pass.
- [x] 3.8 Compute aggregate health from every expected member and guarantee that the diagnostic core performs no filesystem writes or lifecycle actions.

## 4. Doctor Target Resolution

- [x] 4.1 Add explicit-home doctor resolution using supported `--tool` values and the existing optional `--home` environment and project-default rules.
- [x] 4.2 Add authoritative `--agent-id` resolution through one known local registry record, session manifest, brain manifest, recorded tool, and persistent home.
- [x] 4.3 Add unique `--agent-name` resolution with a clear ambiguity diagnostic that directs the operator to `--agent-id`.
- [x] 4.4 Allow stopped managed-agent diagnosis when registry and home authority remain readable, without requiring live gateway, lease, tmux, or TUI evidence.
- [x] 4.5 Reject external agents, stale or missing authority files, zero or multiple target modes, and combinations of agent selectors with `--tool` or `--home` before inspection.

## 5. CLI Surface and Output

- [x] 5.1 Add `doctor` to the `houmao-mgr system-skills` Click command family with repeatable `--pack`, direct-home options, and managed-agent selectors.
- [x] 5.2 Add structured output containing target provenance, running Houmao version, selected packs, receipt posture, aggregate health, and complete per-member integrity and version evidence.
- [x] 5.3 Add concise plain output that identifies the target and expected release, summarizes health, and lists each failing member with corrective context.
- [x] 5.4 Return exit code 0 for healthy diagnostics, code 1 after emitting detected health failures, and standard Click code 2 for usage or target-resolution errors.
- [x] 5.5 Ensure doctor never calls install, sync, upgrade, uninstall, agent launch, or repair paths and never creates or changes a receipt.

## 6. Non-Enforcement Regression Coverage

- [x] 6.1 Prove install and sync accept old, missing, malformed, or mismatched installed version metadata according to their existing receipt, digest, ownership, and conflict rules.
- [x] 6.2 Prove managed launch, rebuild, relaunch, and join do not use `houmao_version` as a compatibility or authorization gate.
- [x] 6.3 Prove v4 manifest and v2 receipt parsing and serialization remain schema-compatible and add no required per-skill version record.
- [x] 6.4 Prove copy and symlink projection preserve the checked-in static version metadata without dynamic rendering.

## 7. Automated Doctor Coverage

- [x] 7.1 Add parser tests for valid metadata, exact string preservation, duplicate keys, malformed YAML, wrong names, missing fields, non-string versions, and invalid release values.
- [x] 7.2 Add core tests for healthy copy and symlink agent packs, selected admin and combined packs, missing roots, incomplete shared children, edited content, old versions, and `0+unknown` runtime version.
- [x] 7.3 Add receipt tests proving absent receipts can be healthy and current, legacy, corrupt, unsupported, or disagreeing receipts remain separate evidence.
- [x] 7.4 Add managed-target tests for authoritative ids, unique and ambiguous names, stopped agents, external records, stale manifests, and selector conflicts.
- [x] 7.5 Add CLI smoke tests for help, default agent expectation, explicit packs, explicit tool homes, managed-agent targeting, plain and structured output, exit codes, and byte-for-byte read-only behavior.

## 8. Documentation

- [x] 8.1 Update the system-skills CLI reference with the top-level version contract, six-root scope, child inheritance, exclusions, and release synchronization rule.
- [x] 8.2 Document doctor examples for explicit homes, authoritative agent ids, friendly names, repeatable packs, receiptless installs, JSON output, and exit codes.
- [x] 8.3 Explain the difference between frontmatter version, receipt package version, and content digest evidence.
- [x] 8.4 State clearly that version mismatch is diagnostic only and that repair requires a separate explicit install or upgrade decision.
- [x] 8.5 Update README or overview references where needed so the discoverable system-skills command inventory includes doctor without duplicating the full reference.

## 9. Verification

- [x] 9.1 Run strict OpenSpec validation and resolve every artifact and delta-spec error.
- [x] 9.2 Run focused frontmatter, source-sync, doctor-core, target-resolution, CLI, lifecycle, managed-home, documentation, and distribution tests.
- [x] 9.3 Run the new version synchronization task and verify a temporary project-version mismatch fails without editing source files.
- [x] 9.4 Run `pixi run format`, inspect the diff, and confirm that subskill content and unrelated user work remain unchanged.
- [x] 9.5 Run `pixi run lint` and resolve all change-related findings.
- [x] 9.6 Run `pixi run typecheck` and resolve all change-related strict typing failures.
- [x] 9.7 Run `pixi run test` and relevant runtime-focused suites, reporting only independently confirmed baseline failures.
- [x] 9.8 Run `pixi run build-dist` and `pixi run check-dist`, then inspect wheel and sdist version metadata.
- [x] 9.9 Run `git diff --check` and review the final diff for any accidental runtime version enforcement or receipt schema change.

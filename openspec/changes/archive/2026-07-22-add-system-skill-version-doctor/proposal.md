## Why

Houmao system skills can be copied or installed through external Skills tooling without a Houmao lifecycle receipt, so an operator cannot reliably tell which Houmao release authored an installed skill. The six standalone skill roots need portable release metadata and a read-only diagnostic that checks managed-agent homes without turning metadata into a runtime compatibility gate.

## What Changes

- Add a quoted `houmao_version` field to the YAML frontmatter of each of the six standalone public `SKILL.md` roots. The value follows the Houmao project release version.
- Keep `houmao_version` out of all sixteen parent-scoped `SKILL-MAIN.md` children, legacy skills, generated loop skills, and the separate `houmao-auto-system-prompt` asset.
- Add release-synchronization validation so checked-in top-level skill metadata and built wheel and sdist assets match the project version before release.
- Add `houmao-mgr system-skills doctor` as a read-only diagnostic for an explicit tool home or a uniquely resolved managed agent. Doctor checks the expected agent pack, installation integrity, top-level frontmatter validity, and `houmao_version` equality with the running Houmao package.
- Report missing, malformed, unversioned, matching, and mismatched skill metadata per standalone skill in plain and structured output, with a diagnostic process exit status suitable for automation.
- Leave install, sync, upgrade, status, launch, rebuild, relaunch, join, and skill invocation behavior unchanged. Those paths neither require nor compare `houmao_version`; only doctor interprets installed version metadata.
- Keep the v4 system-skill manifest and v2 lifecycle receipt schemas unchanged. Doctor reads installed `SKILL.md` frontmatter directly so it also works when a static skill collection was installed without a Houmao receipt.

## Capabilities

### New Capabilities

- `houmao-system-skill-version-metadata`: Defines the top-level-only `houmao_version` contract, release synchronization, exclusions, and portable frontmatter parsing rules.

### Modified Capabilities

- `houmao-mgr-system-skills-cli`: Adds the read-only `system-skills doctor` command, target resolution, per-skill results, aggregate health, and diagnostic exit behavior.
- `houmao-system-skill-installation`: Makes explicit that lifecycle and managed-runtime installation paths preserve but do not enforce or compare skill version metadata.
- `docs-cli-reference`: Documents version metadata, doctor targeting and output, receiptless diagnostics, and the boundary between diagnostic mismatch reporting and runtime enforcement.

## Impact

The change affects the six public system-skill roots, system-skill frontmatter parsing and diagnostic models, the `houmao-mgr system-skills` Click command group, managed-agent home resolution, release and distribution validation, CLI and lifecycle tests, and system-skills reference documentation. It adds no runtime dependency and does not change static pack membership, receipt ownership, content-digest integrity, or installation transactions.

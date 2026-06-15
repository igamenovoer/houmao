# docs-system-skills-overview-guide Specification

## ADDED Requirements

### Requirement: System-skills overview explains Kimi reachability constraints

The getting-started guide `docs/getting-started/system-skills-overview.md` SHALL mention Kimi as a supported explicit external-home installation target for Houmao-owned system skills.

The guide SHALL explain Kimi home resolution at a narrative level: omitted-home installs use `KIMI_CODE_HOME` when set, otherwise `<cwd>/.kimi-code`, and projected skills land under the resolved home's `skills/` directory.

The guide SHALL distinguish Kimi projection from Kimi discovery. It SHALL state that project `.kimi-code/skills` is a Kimi project discovery root when Kimi runs from that project, but arbitrary `<KIMI_CODE_HOME>/skills` projections are not automatically discovered by current Kimi Code unless Kimi configuration includes them.

The guide SHALL explain that Houmao-managed Kimi TUI launches make managed projected skills reachable through Kimi `extra_skill_dirs`, while Kimi headless prompt mode may use `--skills-dir` as a headless launch-policy detail.

#### Scenario: Reader sees Kimi in explicit install guidance

- **WHEN** a reader opens `docs/getting-started/system-skills-overview.md`
- **THEN** the guide includes Kimi in explicit external install guidance for `houmao-mgr system-skills install`
- **AND THEN** it explains the omitted-home default and projected `skills/` path for Kimi

#### Scenario: Reader understands Kimi discovery caveat

- **WHEN** a reader reviews Kimi system-skill guidance
- **THEN** the guide distinguishes files projected under a resolved Kimi home from directories Kimi Code scans automatically
- **AND THEN** it tells the reader that arbitrary `KIMI_CODE_HOME` skill projections require Kimi configuration or a native discovery root to be reachable

#### Scenario: Reader sees managed Kimi TUI skill reachability

- **WHEN** a reader checks managed-home auto-install guidance
- **THEN** the guide states that managed Kimi TUI launches use Kimi-supported additive configuration for projected skills
- **AND THEN** it does not say that managed Kimi TUI launches rely on a `--skills-dir` argument

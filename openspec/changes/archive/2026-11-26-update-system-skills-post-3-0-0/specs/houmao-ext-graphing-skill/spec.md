# Spec Delta

## ADDED Requirements

### Requirement: Graphing extension decomposes monolithic SKILL-MAIN.md into commands and references
`houmao-ext-graphing` SHALL refactor its 282-line `SKILL-MAIN.md` monolith into a lean ~85-line router (`SKILL-MAIN.md`), dedicated `commands/templated-graphics.md` and `commands/freeform-graphics.md` pages (each with numbered `## Workflow` and fallback), and `references/schema-and-render.md` deduplicating repeated guardrails (`179` vs `280`).

#### Scenario: Graphing subcommands become independently navigable executable pages
- **WHEN** a reviewer inspects `houmao-ext-graphing` against `imsight-agent-skill-handling`
- **THEN** `SKILL-MAIN.md` stays concise (~85 lines) with `## Workflow`, `## Actor Frame Gate`, `## Subcommands` table (`help`, `templated-graphics`, `freeform-graphics`), and skill-specific `DO NOT ...` guardrails
- **AND THEN** `commands/templated-graphics.md` and `commands/freeform-graphics.md` each define a numbered `## Workflow`, and `references/schema-and-render.md` owns schema discovery, render CLI commands, and JSON/Altair examples

### Requirement: Graphing extension aligns schema discovery and render CLI guidance with current runtime
`houmao-ext-graphing` SHALL verify and align `houmao-mgr ag-ui impl` discovery, validation, and rendering commands (`houmao.graphic.template` v3 `plotly2d`, `houmao.graphic.vegalite` v1) with current CLI options in `references/schema-and-render.md`.

#### Scenario: Schema discovery and render workflow match current ag-ui CLI
- **WHEN** an agent authors a chart through `houmao-ext-graphing->templated-graphics()` or `freeform-graphics()`
- **THEN** the command workflow uses exact current `houmao-mgr ag-ui impl` subcommands and `houmao-mgr ag-ui protocol events validate`

### Requirement: Graphing extension preserves layer hierarchy, declarative JSON, and security guardrails
`houmao-ext-graphing` SHALL preserve `## Actor Frame Gate`, layer selection (`houmao.graphic.template` v3 `plotly2d` before `houmao.graphic.vegalite` v1; no `new-component` for built-in charts; retired `houmao.chart.bar|line|pie`), inline `traces[].data`, declarative JSON only, validate->render->validate->`interop-ag-ui`, and all unsafe-content bans.

#### Scenario: Unsafe content and raw Python remain prohibited across refactored pages
- **WHEN** an agent authors a graphic via `houmao-ext-graphing`
- **THEN** it emits declarative JSON only (never Python source, raw HTML, SVG, JS URLs, remote `data.url`, iframes, credentials, or 3D scene traces) and hands validated AG-UI events to `houmao-interop-ag-ui`

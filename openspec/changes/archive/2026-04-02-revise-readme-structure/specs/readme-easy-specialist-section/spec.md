## ADDED Requirements

### Requirement: README includes an Easy Specialists usage section

The `README.md` SHALL include a usage section titled "Easy Specialists" positioned after the `agents join` quick-start section and before any full-preset-launch content. This section SHALL demonstrate the `houmao-mgr project easy specialist` workflow as the natural next step for users who want a reusable named agent without learning the full agent-definition-directory layout.

#### Scenario: Reader finds easy specialist workflow in README

- **WHEN** a reader scans the README usage sections
- **THEN** they find an "Easy Specialists" section that shows `project init` → `specialist create` → `instance launch` → prompt → stop in a compact code block

#### Scenario: Easy specialist section uses correct CLI flags

- **WHEN** inspecting the easy specialist code example in README
- **THEN** the `specialist create` and `instance launch` commands use flags that match the actual Click command definitions in `src/houmao/project/easy.py` and the CLI module

#### Scenario: Easy specialist section links to docs for details

- **WHEN** a reader wants more detail about easy specialists
- **THEN** the section includes a link to `docs/getting-started/easy-specialists.md` or the GitHub Pages equivalent

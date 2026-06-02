## 1. Project Directory Selection

- [ ] 1.1 Add a project-group context model that carries an optional `--project-dir` selector from `houmao-mgr project` to nested project subcommands.
- [ ] 1.2 Extend project overlay resolution helpers to resolve an explicit human-facing project directory as `<project-dir>/.houmao` before cwd discovery.
- [ ] 1.3 Update `project init` so `houmao-mgr project --project-dir <dir> init` creates or validates `<dir>/.houmao`.
- [ ] 1.4 Update project status output and diagnostics to describe explicit project-directory selection distinctly from env-selected overlay roots and auto-discovery.
- [ ] 1.5 Update all project subgroup helpers so `specialist`, `profile`, `agents`, `credentials`, `skills`, `mailbox`, and `migrate` honor the group-level project selector.

## 2. Credential Command Consolidation

- [ ] 2.1 Remove the top-level public `houmao-mgr credentials` registration from the root command tree.
- [ ] 2.2 Keep `houmao-mgr project credentials <tool> ...` as the public project-backed credential surface and remove project-target selector options from that path.
- [ ] 2.3 Add retained direct native-agent credential commands under `houmao-mgr internals native-agent credentials <tool> ...`.
- [ ] 2.4 Rewire direct native credential commands to use `--native-agent-root` or `HOUMAO_NATIVE_AGENT_ROOT` instead of `--agent-def-dir`.
- [ ] 2.5 Preserve project-backed and direct native credential storage semantics while changing only command routing and target selection.

## 3. Brain Build Relocation

- [ ] 3.1 Remove the top-level public `houmao-mgr brains` registration from the root command tree.
- [ ] 3.2 Add retained direct brain build plumbing under `houmao-mgr internals native-agent brain build`.
- [ ] 3.3 Rewire direct brain build to use the native-agent root selection contract instead of public `--agent-def-dir`.
- [ ] 3.4 Ensure project and managed-agent launch paths continue to build brain homes internally without requiring users to call direct build commands.

## 4. Agent-Facing Surfaces

- [ ] 4.1 Update command-template ids, metadata, and render tests for `project --project-dir`, internal native credentials, and internal native brain build.
- [ ] 4.2 Remove or rename top-level credentials and top-level brain build templates so maintained public templates match the new CLI tree.
- [ ] 4.3 Update config-draft or generated authoring guidance that emits project credential, native credential, or brain-build command examples.
- [ ] 4.4 Update packaged `houmao-credential-mgr` guidance to route through `project --project-dir ... credentials` and `internals native-agent credentials`.
- [ ] 4.5 Update packaged `houmao-agent-definition` guidance to avoid top-level target-variant commands and route direct native build work through internals.

## 5. Documentation And References

- [ ] 5.1 Update CLI reference docs to remove top-level public `credentials` and `brains` command groups.
- [ ] 5.2 Document `houmao-mgr project --project-dir <dir>` as the explicit project selection surface.
- [ ] 5.3 Document `internals native-agent credentials` and `internals native-agent brain build` in the internals reference.
- [ ] 5.4 Update README, getting-started, system-skill, and project-aware-operation docs that mention `--project`, `--agent-def-dir`, top-level `credentials`, or top-level `brains build`.
- [ ] 5.5 Update demos, scripts, and fixture instructions that used top-level target-variant commands.

## 6. Verification

- [ ] 6.1 Add or update unit tests for project `--project-dir` selection across `status`, `init`, `specialist`, `profile`, `agents`, `credentials`, `skills`, and `mailbox`.
- [ ] 6.2 Add or update CLI shape tests proving top-level `credentials` and `brains` are absent from public help.
- [ ] 6.3 Add or update tests for `internals native-agent credentials` and `internals native-agent brain build`.
- [ ] 6.4 Run focused command tests for credentials, brain build, project overlay resolution, command templates, system skills, and docs checks.
- [ ] 6.5 Run `pixi run lint`.
- [ ] 6.6 Run `pixi run typecheck`.
- [ ] 6.7 Run `pixi run test`.
- [ ] 6.8 Run `openspec validate consolidate-project-targeting-cli --strict`.

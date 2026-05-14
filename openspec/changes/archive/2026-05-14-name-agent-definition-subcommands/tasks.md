## 1. Agent-Definition Router

- [x] 1.1 Revise `houmao-agent-definition/SKILL.md` to expose the skill subcommands `roles`, `recipes`, `raw-profiles`, `specialists`, `profiles`, `create-agent-fast-forward`, `launch-agent`, and `stop-agent`.
- [x] 1.2 Add routing rules that make ambiguous profile wording default to `profiles` and reserve `raw-profiles` for explicit raw, recipe-backed, or exact `project agents launch-profiles` requests.
- [x] 1.3 Update the entry-page workflow so explicitly named subcommands route directly without asking for a lane decision.
- [x] 1.4 Resolve the existing `actions/*` pages by routing them through the new subcommand table or marking them as legacy low-level-only references.

## 2. Subskill Renames And References

- [x] 2.1 Rename the low-level launch-profile subskill route to `raw-profiles` while preserving the underlying `houmao-mgr project agents launch-profiles ...` command guidance.
- [x] 2.2 Rename the ready-profile subskill file and heading to `create-agent-fast-forward`.
- [x] 2.3 Update the fast-forward subskill text to say it creates/selects a specialist, creates/updates an easy profile, prints the launch command, and does not launch.
- [x] 2.4 Update credential-routing references so credential discovery applies to `specialists` and the specialist-create portion of `create-agent-fast-forward`.

## 3. Neighboring Skills And Catalog Text

- [x] 3.1 Update `houmao-specialist-mgr` compatibility wrapper text to route old specialist/profile/ready-profile requests to the new `houmao-agent-definition` subcommands.
- [x] 3.2 Update neighboring skill references that mention ready profiles, explicit launch profiles, or easy profile routing.
- [x] 3.3 Update packaged catalog and agent prompt summaries so `houmao-agent-definition` advertises subcommand-based routing.

## 4. Documentation And Specs

- [x] 4.1 Update README system-skill prose/table to name `profiles`, `raw-profiles`, and `create-agent-fast-forward`.
- [x] 4.2 Update `docs/getting-started/system-skills-overview.md` with the default easy-profile routing and raw-profile escape hatch.
- [x] 4.3 Update `docs/reference/cli/system-skills.md` with the new skill subcommand names and underlying CLI mapping.
- [x] 4.4 Keep compatibility wording only where useful for old prompts; make the new subcommand names primary.

## 5. Verification

- [x] 5.1 Run `openspec validate --changes name-agent-definition-subcommands`.
- [x] 5.2 Run focused system-skill catalog tests affected by skill names, catalog descriptions, and projected skill contents.
- [x] 5.3 Run focused documentation tests affected by README and system-skill overview changes.
- [x] 5.4 Run `git diff --check`.

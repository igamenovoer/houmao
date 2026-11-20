# DSH Skill Installation and Native Refresh Test

Date: 2026-11-20. Status: `hmtest-demo-task` installed in the live uv-installed DSH Web agent and exercised end to end. The explicit refresh path returned `already_current`; DSH discovered the new bundle before a forced reload, so the native reload mutation remains unverified.

Context: [debug-intent.md](../debug-intent.md), [Iteration 2](../iterations/2026-11-19-plan-2-dsh-rc3-run-modes.md). Fixture: `tests/fixtures/skills/hmtest-demo-task`, committed as `2ee2f8e8 test: add demo skill routing fixture`.

## Target

- Run: `tmp/houmao-30-iter2-rc3/runs/self-hosted-dsh-web-manager-2752bd4a0bc9`
- Agent: `49f2ba49-e7be-4463-bdbf-a788f4ff9596`
- Backend: `dsh_web`, native session `session-c22df0f3-5c06-4362-bab0-897fc205c0c0`
- Native home: `tmp/houmao-30-iter2-rc3/runs/self-hosted-dsh-web-manager-2752bd4a0bc9/workdir/.houmao/runtime/homes/dsh-brain-20261120-030332Z-fae160`
- Gateway: `http://127.0.0.1:36205`, `gateway_health: healthy`
- Toolchain: uv-installed `houmao-mgr 3.0.0rc3` on Python 3.13.18. The uv tool and running agent were installed from `5bba95e0`; the skill fixture was committed later as `2ee2f8e8`.

## Discovery Boundary

The effective DSH profile mounts `skill-filesystem` with `includeDefaultRoots: false`, `customSkillDirs: [$DSH_HOME/skills]`, and `watch: false`. Here `$DSH_HOME` is the native home above, not the operator's OS home. asm has no DSH provider, and `.agents/skills` is outside this profile's roots. Installation therefore means placing the bundle at `$DSH_HOME/skills/hmtest-demo-task`.

## Baseline

The skill catalog before installation contained five entries:

```text
dsh-doc, office, office-docx, office-pptx, office-xlsx
```

`refresh --check` reported `freshness: current`, `coverage_complete: true`, and `current` for both the `catalog` and `body` skill components.

## Installation

The fixture was copied into the native custom skill root:

```bash
H=.../homes/dsh-brain-20261120-030332Z-fae160
cp -a tests/fixtures/skills/hmtest-demo-task "$H/skills/hmtest-demo-task"
```

The copied tree contained the parent `SKILL.md`, its `agents/openai.yaml`, and all three `subskills/*/SKILL-MAIN.md` entries with their `agents/openai.yaml` files.

## Refresh Observation

A second `refresh --check` without any explicit refresh already returned six skills, including `hmtest-demo-task`, with `freshness: current` and `coverage_complete: true`.

The explicit refresh then returned:

```text
outcome = already_current
method = noop
effects = absent
native_settled = True
native_ready = True
```

Its observation still listed:

```text
catalog current: dsh-doc, hmtest-demo-task, office, office-docx, office-pptx, office-xlsx
body    current: dsh-doc, hmtest-demo-task, office, office-docx, office-pptx, office-xlsx
```

Observed behavior: the new bundle appeared in the live native catalog before an explicit refresh, despite `watch: false` in the launch patch. The cause is not proven. It could be a per-step or per-snapshot rescan, or a watcher outside the inspected patch. This run therefore confirms refresh's `already_current` no-op behavior, not its `native_reload` mutation path.

## Runtime Verification

The agent was prompted through the maintained fixture:

```text
Use the skill hmtest-demo-task with its greet-name route. The name is Ada. Return only the final task output.
```

The completed response was:

```text
Hello, Ada!
```

The native session journal showed the agent reading both the parent entrypoint and the selected child:

- `$H/skills/hmtest-demo-task/SKILL.md`
- `$H/skills/hmtest-demo-task/subskills/greet-name/SKILL-MAIN.md`

This verifies discovery of the parent bundle, parent-to-subskill routing, and loading of the child from the installed tree.

## GUI Catalog Visibility

An already-open DSH Web tab can keep a stale `/` skill list after an external install. The installed skill was absent from the operator's open tab and appeared after a page reload. A later probe that added a temporary skill while a fresh tab was open saw the new entry without reload, so this is a tab or per-session catalog cache boundary, not a missing installation. Reload the tab or open a new session when the `/` menu does not match `refresh --check`.

## Body Update Check

The installed child was changed from `Hello, <name>!` to `Hi, <name>!`, including its workflow, output contract, and guardrail, then the agent was prompted:

```text
Reload the skill hmtest-demo-task and use its greet-name route with the name Ada. Follow the current file contents and return only the final task output.
```

The response was:

```text
Hi, Ada!
```

No refresh was run between the edit and the prompt. The updated body was read on the next load, matching the documented `next_load` body boundary.

The installed copy was then restored from the committed fixture:

```bash
rm -rf "$H/skills/hmtest-demo-task"
cp -a tests/fixtures/skills/hmtest-demo-task "$H/skills/hmtest-demo-task"
diff -r tests/fixtures/skills/hmtest-demo-task "$H/skills/hmtest-demo-task"
```

`diff -r` was clean, and a final `refresh --check` returned `freshness: current` with all six skills.

## Fourth Subskill Update

A fourth child, `title-case`, was added to the fixture. The parent `SKILL.md` description changed from "three self-contained demo tasks" to "four self-contained demo tasks", and the parent routing table gained the `title-case` row. The updated tree was copied over the installed copy:

```bash
rm -rf "$H/skills/hmtest-demo-task"
cp -a tests/fixtures/skills/hmtest-demo-task "$H/skills/hmtest-demo-task"
```

The immediate `refresh --check` again reported `freshness: current` and `coverage_complete: true`; it did not report `pending`. The explicit `refresh` returned:

```text
outcome = already_current
method = noop
effects = absent
```

A fresh Web page showed the updated description in the `/hmtest` menu:

```text
Use when a test needs a small parent skill that installs four self-contained demo tasks...
```

The agent was then prompted to use the new route:

```text
Use the skill hmtest-demo-task with its title-case route. The title is "the quick brown fox". Return only the final task output.
```

It read `$H/skills/hmtest-demo-task/subskills/title-case/SKILL-MAIN.md` and returned:

```text
The Quick Brown Fox
```

The update was picked up and usable before any explicit native reload. `refresh` had nothing to reconcile and returned `already_current`; this run still does not demonstrate a refresh-created catalog reload.

## Findings

- Installation works through `$DSH_HOME/skills`. The generic `.agents/skills` path used by asm's fallback provider does not reach this DSH profile because default roots are disabled.
- `refresh --check` is a valid read-only freshness probe. It exits zero only for complete confirmed freshness.
- `refresh` returned `already_current` with `method: noop` and `effects: absent`, which preserves the running agent and conversation. The native reload path remains unexercised in this run.
- DSH made the new bundle visible before an explicit refresh despite `watch: false`. Do not attribute that catalog application to Houmao refresh without further evidence.
- Skill body updates are picked up on the next load without refresh. Catalog-visible changes should still be checked with `refresh --check` and refreshed when the observation reports `pending`.
- The installed copy is runtime state under the run's private home. A fresh launch or native home rebuild will not preserve it. A durable test must reinstall it during fixture preparation or add the skill root to the launch profile.
- Mutating refresh requires an attached gateway; this run had a healthy attached gateway. The no-op path did not need a native mutation.

## Next Steps

- Force a catalog-visible change that DSH does not auto-discover, such as a provider configuration change or an unobserved root update, to exercise `refresh` with `method: native_reload`.
- Test skill removal and rename through `refresh --check` and `refresh`, recording whether each observes `pending` or `already_current`.
- Decide whether update tests should edit the installed copy or replace it from the source fixture between observations.
- Decide the durable installation route for repeatable runs: fixture preparation copy, native-home link, or a launch-profile skill root.

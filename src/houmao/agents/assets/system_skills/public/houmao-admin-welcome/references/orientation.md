# State-Aware Orientation

Use this reference for an empty invocation or `start-guided-tour`. The purpose is to identify posture and offer a useful path without mutating state.

## Read-Only Inspection

Use the selected Houmao launcher consistently. Prefer `houmao-mgr` on `PATH`, then `uv tool run --from houmao houmao-mgr`; use a development launcher only when those do not satisfy the session.

Inspect only what is needed:

| Area | Read-only evidence |
|---|---|
| Project | `houmao-mgr project status` in the explicit or current project directory |
| Definitions | `houmao-mgr project specialist list` and `project profile list` after a project exists |
| Runtime | `houmao-mgr agents global list` |
| Loops | Existing loop artifacts beneath an explicit project or loop directory |

Do not scan home directories, credential contents, unrelated repositories, or every gateway and mailbox during orientation. If inspection cannot run, report posture as unknown and offer `inspect first`.

## Intent Guess Matrix

| Observed posture | Likely path |
|---|---|
| No project overlay | Single Agent Full Run, beginning with project readiness |
| Project exists, no specialists | Single Agent Full Run, beginning with agent definition |
| Definitions exist, no running agents | Single Agent Full Run, beginning with launch readiness |
| One running agent | Single Agent Full Run, beginning with inspection or follow-up operation |
| Multiple running agents | Operator-Controlled Agent Team |
| Loop artifacts or an explicit orchestration goal | Pro Agent Loop |
| Existing project with unclear next step | Existing Project Reorientation |
| Component, architecture, or working-logic wording | Subsystem Exploration |

The guess orders choices. It never authorizes a concrete operation.

## Response Shape

Give one sentence describing Houmao, then a compact current-posture summary, likely path with reason, path choices, and required input. Keep tables to four columns or fewer. Offer `more detail` for deeper architecture or command examples.

For a blank workspace, explain that project readiness is the first stage of Single Agent Full Run. Also offer Subsystem Exploration and read-only inspection. For an existing project, offer the likely path, Existing Project Reorientation, Subsystem Exploration, and another guided path when relevant.

Do not answer a bare invocation with only an activation acknowledgement or “how can I help?” Wait for confirmation before handing any executable operation to `$houmao-admin-entrypoint`.

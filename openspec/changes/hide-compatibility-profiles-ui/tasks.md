## 1. Project CLI And Overlay Behavior

- [x] 1.1 Remove the public `--with-compatibility-profiles` option from `houmao-mgr project init`.
- [x] 1.2 Keep any remaining compatibility-profile directory creation helper internal-only, or remove it if local usage is limited and the cleanup stays small.
- [x] 1.3 Update project-overlay and project-command tests so default init still avoids optional roots and `project init --with-compatibility-profiles` is no longer accepted or documented.

## 2. User-Facing Documentation And Skills

- [x] 2.1 Remove compatibility-profile bootstrap and layout guidance from getting-started docs, including quickstart and agent-definition layout pages.
- [x] 2.2 Remove compatibility-profile bootstrap and layout guidance from CLI reference docs for `houmao-mgr project init` and project layout notes.
- [x] 2.3 Update `houmao-project-mgr` packaged skill instructions and references so agents no longer ask users whether to pre-create compatibility profiles.
- [x] 2.4 Update system-skill tests or snapshots that currently assert `--with-compatibility-profiles` appears in project-init guidance.

## 3. Canonical Layout And Fixtures

- [x] 3.1 Remove `compatibility-profiles/` from supported tracked agent-definition layout documentation and fixture README material.
- [x] 3.2 Relocate, inline, or delete obsolete Markdown compatibility-profile fixtures so supported live fixture trees no longer expose `compatibility-profiles/` as a canonical directory.
- [x] 3.3 Verify native `server-api-smoke` role and preset fixture consumers still launch through roles/presets rather than compatibility-profile Markdown.

## 4. Verification

- [x] 4.1 Run focused unit tests for project overlay bootstrap, project CLI commands, and system-skill assets.
- [x] 4.2 Run any smoke/unit tests affected by moved `server-api-smoke` fixtures.
- [x] 4.3 Grep maintained user-facing docs and packaged skill assets to confirm `compatibility-profiles` and `--with-compatibility-profiles` no longer appear outside internal source, archived specs, or explicitly test-only compatibility paths.
- [x] 4.4 Run OpenSpec validation/status for `hide-compatibility-profiles-ui` before implementation is considered complete.

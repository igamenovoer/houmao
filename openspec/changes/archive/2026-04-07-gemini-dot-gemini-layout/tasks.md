## 1. Change Gemini managed skill destinations

- [x] 1.1 Update the Gemini tool adapter and shared Gemini system-skill destination constants to use `.gemini/skills` instead of `.agents/skills`.
- [x] 1.2 Update managed brain construction and Gemini mailbox runtime skill projection to install selected and runtime-owned Gemini skills under `.gemini/skills`.
- [x] 1.3 Update `houmao-mgr system-skills` Gemini install behavior to keep `<cwd>` as the effective home root while projecting Gemini skills under `<home>/.gemini/skills`.

## 2. Migrate legacy Houmao-managed Gemini paths

- [x] 2.1 Use shared installer ownership tracking to migrate previously recorded Gemini system-skill paths from `.agents/skills` to `.gemini/skills` on reinstall or auto-install.
- [x] 2.2 Add managed-home cleanup for legacy Houmao-managed `.agents/skills` content during Gemini home rebuild or reuse so stale alias content is not left active.
- [x] 2.3 Ensure Gemini mailbox and system-skill prompting no longer treats `.agents/skills` as the maintained Gemini skill root.

## 3. Verify contracts, tests, and docs

- [x] 3.1 Update Gemini fixtures and automated tests to assert `.gemini/skills` for managed builds, mailbox skill projection, join-time installs, and `system-skills`.
- [x] 3.2 Update Gemini-facing CLI and runtime documentation to describe `.gemini/skills` as the maintained managed skill surface.
- [x] 3.3 Run OpenSpec validation and the relevant targeted test coverage for Gemini build, join, mailbox, and `system-skills` flows.

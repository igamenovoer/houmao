## 1. Update Packaged Skill Launcher Contracts

- [x] 1.1 Revise the seven affected top-level system-skill `SKILL.md` files to teach `command -v houmao-mgr` first, uv-tool fallback second, later development launchers, and explicit user launcher override behavior.
- [x] 1.2 Update the shared mailbox launcher reference page to match the new PATH-first, uv-second launcher policy.

## 2. Align Downstream Skill Guidance

- [x] 2.1 Revise affected action pages that currently refer to a separately "resolved" launcher so they no longer imply the old development-hint-first probing behavior.
- [x] 2.2 Remove or rewrite guardrail text that encodes the old Pixi-first or `.venv`-first precedence assumptions.

## 3. Refresh Validation

- [x] 3.1 Update unit tests and other text assertions that currently expect `uv run houmao-mgr` or the old launcher precedence wording in packaged system skills.
- [x] 3.2 Run the relevant OpenSpec validation and targeted test coverage for the changed skill assets.

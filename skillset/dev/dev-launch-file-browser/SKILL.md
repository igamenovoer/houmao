---
name: dev-launch-file-browser
description: 'Manual invocation only; use only when the user explicitly requests `dev-launch-file-browser` by exact name or asks to launch, start, stop, verify, or reset the in-repo Filestash file browser under `dockers/dev-helpers/filestash/` so they can browse repository files and generated artifacts through the local web UI.'
---

# Dev Launch File Browser

Use the repo-owned Filestash helper for repository file browsing. Do not replace it with ad hoc `docker run` commands or a separate compose stack.

## Workflow

1. Check the repo-owned helper files when you need current settings.

- Read `dockers/dev-helpers/filestash/.env` for the current port, connection label, and password.
- Read `dockers/dev-helpers/filestash/README.md` only when you need the documented prerequisites or reset procedure.

2. Use the repo-owned wrapper scripts.

- Start or ensure the helper is running with `./dockers/dev-helpers/filestash/up.sh`.
- Verify the running helper with `./dockers/dev-helpers/filestash/verify.sh` when the user asks for confirmation or the startup output looks suspicious.
- Stop the helper with `./dockers/dev-helpers/filestash/down.sh`.
- Reset the helper by stopping it, removing `dockers/dev-helpers/filestash/.data`, then starting it again.

3. Report access details from `.env`, not from stale memory.

- URL: `http://127.0.0.1:${FILESTASH_HTTP_PORT}/login`
- Connection label: `FILESTASH_CONNECTION_LABEL`
- Password: `FILESTASH_DEFAULT_PASSWORD`

4. Surface prerequisite failures directly.

- If the image is missing, tell the user the helper expects `machines/filestash:latest` to already exist locally.
- If `up.sh` fails because `node` or `jq` is missing, report that clearly and stop.
- If the container starts but verification fails, report the failing step and prefer `verify.sh` output over guessing.

## Guardrails

- Do not edit the helper stack just to launch it unless the user explicitly asks for changes.
- Do not invent alternate ports, passwords, or image names. Read the current values from `.env` and the compose file.
- Do not claim the browser is ready unless `up.sh` succeeds. Use `verify.sh` when the user asks for confidence or when the state is unclear.

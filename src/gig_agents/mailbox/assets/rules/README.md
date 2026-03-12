# Filesystem Mailbox Rules

This mailbox root is managed by `gig-agents`.

## Managed assets

- `protocols/filesystem-mailbox-v1.md` documents the v1 filesystem mailbox contract shipped with this build.
- `scripts/requirements.txt` declares the third-party Python dependencies needed by the managed mailbox scripts in this mailbox root.
- `scripts/register_mailbox.py` is the managed entrypoint for `safe`, `force`, and `stash` mailbox registration flows.
- `scripts/deregister_mailbox.py` is the managed entrypoint for `deactivate` and `purge` mailbox deregistration flows.
- `scripts/deliver_message.py` is the managed delivery entrypoint for mailbox writes that touch projections or SQLite state.
- `scripts/insert_standard_headers.py` is the managed helper for standard mailbox front matter and header normalization.
- `scripts/update_mailbox_state.py` is the managed entrypoint for mailbox-state mutations.
- `scripts/repair_index.py` is the managed entrypoint for repair or reindex flows.

## Usage

- Inspect this `rules/` tree before interacting with shared mailbox state.
- Treat the managed filenames under `rules/scripts/` as part of the mailbox protocol surface for the current `protocol-version.txt`.
- Inspect `scripts/requirements.txt` before invoking a managed Python helper script so the required dependencies are available.
- Do not replace missing managed scripts by improvising local alternatives; treat missing managed assets as a mailbox initialization problem.

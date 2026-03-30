# Filesystem Mailbox Rules

This mailbox root is managed by `Houmao`.

## Managed assets

- `protocols/filesystem-mailbox-v1.md` documents the v1 filesystem mailbox contract shipped with this build.
- `scripts/` may contain compatibility or diagnostic helper assets published by the runtime.
- When those helpers are published, `scripts/requirements.txt` declares their third-party Python dependencies.
- Those compatibility helpers validate payload files through strict shared `pydantic` schemas before they mutate mailbox files, shared `index.sqlite`, mailbox-local `mailbox.sqlite`, or locks.

## Usage

- Inspect this `rules/` tree first for mailbox-local policy guidance such as formatting, etiquette, and workflow hints.
- Treat ordinary mailbox work as a Houmao-owned workflow through gateway HTTP or `houmao-mgr agents mail ...`; do not treat `rules/scripts/` as the first-choice public execution contract.
- If you intentionally invoke a published compatibility helper, inspect `scripts/requirements.txt` first so the required dependencies are available.
- Expect every published Python compatibility helper to write exactly one JSON object to stdout for both success and failure outcomes. Schema validation failures are reported there before any mailbox mutation is attempted.
- Do not replace missing compatibility scripts by improvising local alternatives. Ordinary mailbox workflows should keep working without them; missing helpers matter only for compatibility or diagnostics.

# Mailbox Demo Python Fixture

This dummy project is the default narrow workdir for mailbox tutorial-pack and runtime-agent smoke flows.

It is intentionally small:

- one `pyproject.toml`
- one tiny `src/mailbox_demo/` package
- one small pytest module

The tracked fixture stays source-only. Demo helpers copy this tree into a run-local `project/` directory, initialize a fresh git repository there, and let the live agent work inside that isolated copy.

# Redirect: Split Fixture Lanes

`tests/fixtures/agents/` is no longer the maintained canonical fixture root.

Use these lanes instead:

- `tests/fixtures/plain-agent-def/` for the maintained secret-free direct-dir fixture tree
- `tests/fixtures/auth-bundles/` for maintained local-only credential bundles
- fresh `.houmao/` overlays or demo-owned tracked `inputs/agents/` trees for maintained project-aware and demo-local flows

Local host-only auth data may still exist under this retired path during migration, but maintained code, docs, tests, and demos should stop reading from it.

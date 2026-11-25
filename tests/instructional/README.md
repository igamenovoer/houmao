# Instructional Test Bundles

Agent-driven live verification bundles for Houmao, organized as self-contained directories under `tests/instructional/<case-slug>/`. Each bundle owns its own `README.md` harness contract (`Launch`, `Doctor`, `Drive`, `Evidence`, `Cleanup`, `Helpers`), scenario files under `cases/`, and optional durable scripts under `helpers/`.

Run bundles against a live checkout using the project-local Git-ignored temporary root `tmp/instructional-tests/<run-id>/` for temporary scripts (`scripts/`), disposable runtime state (`runtime/`), and surviving proof artifacts (`evidence/<case-slug>/<scenario-slug>/`). Do not collect these suites from CI (`pixi run test`).

## Bundles

| Bundle | Harness | Coverage |
| --- | --- | --- |
| `agent-mail-stalwart` | [agent-mail-stalwart/README.md](agent-mail-stalwart/README.md) | Product provisioning and direct JMAP attachment, notifier wake-up, threaded reply and archive, and a two-agent mail round trip. |
| `skill-update` | [skill-update/README.md](skill-update/README.md) | Intra-agent and inter-agent versioned `skills` mount updates on managed DSH Web agents, including peer authorization, keyed-roster revocation, busy/queued self-push handling, and next-turn skill loading. |

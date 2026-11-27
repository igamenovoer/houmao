# Instructional Test Bundles

Agent-driven live verification bundles for Houmao, organized as self-contained directories under `tests/instructional/<case-slug>/`. Each bundle owns its own `README.md` harness contract (`Launch`, `Doctor`, `Drive`, `Evidence`, `Cleanup`, `Helpers`), scenario files under `cases/`, and optional durable scripts under `helpers/`.

Run bundles against a live checkout using the project-local Git-ignored temporary root `tmp/instructional-tests/<run-id>/` for temporary scripts (`scripts/`), disposable runtime state (`runtime/`), and surviving proof artifacts (`evidence/<case-slug>/<scenario-slug>/`). Do not collect these suites from CI (`pixi run test`).

## Bundles

| Bundle | Harness | Coverage |
| --- | --- | --- |
| `agent-cccc` | [agent-cccc/README.md](agent-cccc/README.md) | Two-agent CCCC chat discovery, handle-based threaded replies and receipts, push batching, busy-agent pending delivery, in-turn gateway queue reads, gateway reattachment recovery, and no-mail channel auditing. |
| `agent-cccc-cuda-coop` | [agent-cccc-cuda-coop/README.md](agent-cccc-cuda-coop/README.md) | Five-minute observation of spontaneous CCCC chat among four Qwen 3.8 peers optimizing GDN prefill or fused MoE in private workdirs. |
| `agent-hermes` | [agent-hermes/README.md](agent-hermes/README.md) | Live managed Hermes agent verification on self-hosted Qwen 3.8 with `xhigh` thinking across `service`, `headless`, and `tui` modes, multi-agent shared-gateway isolation, local filesystem (`offline`) mail, and Stalwart JMAP (`online`) mail. |
| `agent-mail-stalwart` | [agent-mail-stalwart/README.md](agent-mail-stalwart/README.md) | Product provisioning and direct JMAP attachment, notifier wake-up, threaded reply and archive, and a two-agent mail round trip. |
| `skill-update` | [skill-update/README.md](skill-update/README.md) | Intra-agent and inter-agent versioned `skills` mount updates on managed DSH Web agents, including peer authorization, keyed-roster revocation, busy/queued self-push handling, and next-turn skill loading. |

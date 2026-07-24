# Use Cases

This directory contains the foundational Agent Definition lifecycle use cases.

## Index

| ID | Use Case | Owning Change |
| --- | --- | --- |
| `UC-01` | [Author and Deploy an Agent Definition With Skills From a Directory](uc-01-author-and-deploy-agent-definition-with-skills-from-directory.md) | `deploy-predefined-agent-blueprints` |
| `UC-02` | [Deploy an Agent With Definition-Declared Arguments](uc-02-deploy-agent-with-definition-declared-arguments.md) | `deploy-predefined-agent-blueprints` |

## Related Changes

- `add-agent-definition-batch-deployment` owns UC-03.
- `add-managed-agent-instance-state` owns UC-04 and UC-06.
- `add-private-agent-workspaces` owns UC-05.

Authoring preserves `intent/src`, derives a reviewable interpretation under `intent/derived`, and materializes an immutable Agent Definition Revision. Deployment consumes that revision through a typed Deployment Request and deterministic Deployment Plan. It creates project objects but does not launch a managed agent.

# Push Receipts

A commit receipt identifies a saved candidate and its base. The push receipt records `operation_id`, `candidate`, `expected_base`, and the admitted `publisher`. Use the original operation ID to inspect an attempt. Keep `published_commit`, `effective_commit`, `activation`, `native_settled`, and `native_ready` separate in the report.

| Outcome | Interpretation and Follow-Up |
| --- | --- |
| `published` | The receipt confirms the visible published revision. Read the activation and native fields to establish effectiveness and readiness. |
| `busy` | The candidate stays saved and the attempt was refused. Any later publication is an explicit new attempt after readiness with a fresh ID. |
| `queued` | The gateway retained a managed-self intent and is waiting for idle maintenance. Check status using its original ID. |
| `conflict` | Verify the selected target and current base. If the publication changed, prepare a fresh draft at that base. |
| `unconfirmed` or no response | Use the original operation ID with `status`. The request may have taken effect. |
| `pending` or `unknown` | Use read-only status to track the strongest retained evidence while settlement is unresolved. |
| `refused` or `unavailable` | Report the returned reason and the remaining authorization, mount, or native prerequisite. |

A successful immediate push exit confirms publication. A successful deferred push exit can also report accepted work waiting for idle. The published tree can still have partial or unknown native activation. A reconciliation read uses current read authority even for the original publisher.

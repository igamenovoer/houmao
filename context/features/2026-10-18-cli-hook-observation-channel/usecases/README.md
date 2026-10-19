# Use Cases

This directory contains feature-specific use cases for the CLI Hook Observation Channel.

## Index

| ID | Use Case | Status |
| --- | --- | --- |
| `UC-01` | Enable and Verify Hook Observation for a Managed Claude Launch | Draft |
| `UC-02` | Merge Hook Lifecycle with TUI Surface State for a Normal Turn | Draft |
| `UC-03` | Detect Permission Waits and API Failures from Hooks | Draft |
| `UC-04` | Degrade to TUI-Only State When Hooks Are Unavailable | Draft |

## Notes

- All use cases assume a managed Claude Code session with the TUI tracker installed. Joined sessions and unmanaged launches are out of scope.
- The hook channel is observational. No use case permits a hook to block, deny, modify, or accelerate a provider action.
- Each use case separates hook-owned lifecycle facts from TUI-owned surface facts. A design that collapses those facts into one source violates the feature requirement.
- Qualification evidence for these use cases belongs in design and test artifacts, not in the use cases themselves.

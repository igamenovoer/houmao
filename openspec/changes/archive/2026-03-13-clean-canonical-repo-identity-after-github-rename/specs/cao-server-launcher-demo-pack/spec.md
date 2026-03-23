## MODIFIED Requirements

### Requirement: Demo runner SHALL execute launcher `status`, `start`, and `stop` with structured outputs
The tutorial pack runner SHALL invoke
`python -m houmao.cao.tools.cao_server_launcher` for `status`,
`start`, and `stop`, and SHALL capture JSON outputs into the demo workspace for
verification/report generation.

The runner SHALL verify launcher start/stop behavior using artifact paths under
`runtime_root/cao-server/<host>-<port>/`.

The runner SHALL also verify the standalone-service contract by performing a
launcher `status` check after `start` has already returned.

#### Scenario: End-to-end run exercises standalone launcher lifecycle across command boundaries
- **WHEN** a developer runs the demo with prerequisites satisfied
- **THEN** the run executes launcher `status`, `start`, a later post-start `status`, and `stop` in one flow
- **AND THEN** the post-start `status` confirms the CAO service is still healthy after the `start` command has exited
- **AND THEN** the run report includes parsed results from those JSON outputs

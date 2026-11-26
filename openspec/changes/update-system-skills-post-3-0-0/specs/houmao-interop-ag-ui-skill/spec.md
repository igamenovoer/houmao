# Spec Delta

## ADDED Requirements

### Requirement: AG-UI interop decomposes monolithic SKILL-MAIN.md into commands and references
`houmao-interop-ag-ui` SHALL refactor its 262-line `SKILL-MAIN.md` monolith into a lean ~85-line router (`SKILL-MAIN.md`), four command pages (`commands/{validate,frame,render,publish}.md`, each with numbered `## Workflow` and fallback), and `references/protocol-and-impl.md` deduplicating overlapping `## Safety` and `## Guardrails` rules.

#### Scenario: AG-UI subcommands become navigable workflow pages without entrypoint bloat
- **WHEN** a reviewer inspects `houmao-interop-ag-ui` against `imsight-agent-skill-handling`
- **THEN** `SKILL-MAIN.md` stays concise (~85 lines) with `## Workflow`, `## Actor Frame Gate`, `## Subcommands` table (`help`, `validate`, `frame`, `render`, `publish`), and skill-specific `DO NOT ...` guardrails
- **AND THEN** `commands/{validate,frame,render,publish}.md` each own an executable `## Workflow`, and `references/protocol-and-impl.md` owns protocol/impl/publish details and table payload examples

### Requirement: AG-UI interop documents request vs prompt permission semantics on gateway input paths
`houmao-interop-ag-ui` SHALL clarify `agent.request.submit` (`agent-requester` default) vs `agent.prompt.direct` (`agent-operator`) semantics when AG-UI or workbench clients interact with gateway input paths alongside AG-UI event publishing.

#### Scenario: AG-UI client input paths reflect built-in permission distinction
- **WHEN** an agent or workbench documentation flow discusses AG-UI-connected input submission
- **THEN** `references/protocol-and-impl.md` distinguishes `agent.request.submit` work requests from `agent.prompt.direct` direct turns without altering live-only AG-UI event publish rules

### Requirement: AG-UI interop preserves protocol/impl/new-component split, durable identity, and live-only fanout
`houmao-interop-ag-ui` SHALL preserve `## Actor Frame Gate`, `ag-ui protocol` vs `ag-ui impl` vs `new-component`, `agent_id`/`agent_name` durability vs transient gateway URLs, live-only fanout semantics (`stored_count: 0`, `delivered_count`, `default_sink_due_to_no_destination`, `last-sent-thread`, `--run-id`), no `--endpoint` on publish, and no raw hand-written AG-UI JSON.

#### Scenario: Zero-delivery or default-sink publish never claims GUI visibility
- **WHEN** `gateway ag-ui publish` reports `delivered_count: 0` or `default_sink_due_to_no_destination`
- **THEN** `houmao-interop-ag-ui` instructs the agent not to claim the GUI displayed the message and to ask the user to connect or mark the target pane active before retrying

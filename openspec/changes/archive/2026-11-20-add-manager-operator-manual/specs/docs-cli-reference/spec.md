# CLI Reference Delta

## ADDED Requirements

### Requirement: The manager reference introduces the operator manual

The `houmao-mgr` reference SHALL list `manual` as a public command group, show how to open the index, a catalog, and a page, and describe its role as offline operating guidance for agents using the manager directly.

#### Scenario: A CLI reference reader finds workflow guidance

- **WHEN** a reader opens the manager CLI reference
- **THEN** the reference shows `houmao-mgr manual`, `houmao-mgr manual start`, and `houmao-mgr manual start first-agent`
- **AND THEN** it directs readers to the packaged manual for workflow decisions and to command help for command syntax

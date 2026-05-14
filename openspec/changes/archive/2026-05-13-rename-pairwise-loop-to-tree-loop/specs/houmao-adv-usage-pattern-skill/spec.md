## ADDED Requirements

### Requirement: Advanced usage pattern presents local-close edge loop terminology
The packaged `houmao-adv-usage-pattern` skill SHALL use `local-close edge loop` as the canonical user-facing name for the elemental two-agent driver/worker protocol.

The skill SHALL preserve `pairwise edge-loop` as an alias where existing pattern filenames, links, or older pairwise loop guidance refer to that protocol.

The advanced-usage chooser SHALL describe tree loop planners as the owners of composed local-close tree topology and generic loop planners as the owners of directed graph loop topology.

#### Scenario: Chooser names elemental protocol clearly
- **WHEN** the advanced-usage chooser recommends the two-agent driver/worker protocol
- **THEN** it calls the behavior a local-close edge loop
- **AND THEN** it may include the pairwise edge-loop pattern name as an alias for compatibility

#### Scenario: Chooser routes composed topology
- **WHEN** the user needs recursive child edges, multiple local-close edges, rendered control graphs, or run control
- **THEN** the advanced-usage skill routes to a tree-loop or generic-loop planning skill
- **AND THEN** it does not describe the elemental edge protocol as the owner of composed topology

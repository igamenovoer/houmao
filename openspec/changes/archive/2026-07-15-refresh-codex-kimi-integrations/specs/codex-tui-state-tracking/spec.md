## ADDED Requirements

### Requirement: Codex delegated work remains active until the parent turn settles
For a maintained Codex 0.144.x TUI profile, visible GPT-5.6 multi-agent or collaboration activity SHALL count as current-turn active evidence. A parent turn SHALL remain active while delegated agents are running, waiting on current collaboration work, or reporting current progress, even if the editor frame remains visible.

The tracker SHALL report ready only after delegation activity has settled and the current surface satisfies the normal stable ready-return contract. Missed short-lived delegation frames at lower capture rates SHALL not create an impossible state sequence or a false successful completion before later active evidence.

#### Scenario: Running delegated agents keep the turn active
- **WHEN** the current Codex surface reports one or more delegated agents still running
- **THEN** tracked state remains active
- **AND THEN** the visible editor does not alone make the surface prompt-ready

#### Scenario: Sparse replay remains semantically valid
- **WHEN** a lower-rate replay skips one intermediate delegation transition
- **THEN** the resulting tracked sequence remains consistent with the observed later activity and stable ready return
- **AND THEN** the tracker does not emit an irreversible false terminal result between those observations


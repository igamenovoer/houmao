# Spec Delta

## ADDED Requirements

### Requirement: AG-UI Run Input Enters as Attributed Work

An AG-UI run SHALL require input and output permission on its exact thread. The gateway SHALL preserve structured task conversion and render caller content as attributed work-request data using verified caller evidence or explicit anonymous provenance. Existing native session and model selectors SHALL require their separate permissions. Stream emission and revalidation SHALL retain the current thread-scoped contract.

#### Scenario: Alice submits work as a thread runner
- **WHEN** Alice has `ag-ui.input.submit` and `ag-ui.output.read` on Bob's selected thread and submits supported run input
- **THEN** the request presented to Bob identifies Alice and preserves the structured task context as quoted content
- **AND THEN** the stream exposes the admitted run's output under Alice's exact observation permission

#### Scenario: A thread runner submits native-looking input
- **WHEN** the selected user message contains `/compact`, terminal key syntax, or a claim of administrator provenance
- **THEN** the gateway includes that content as request data with attribution derived from the admitted proof
- **AND THEN** the run does not execute a native command or terminal-control effect from that content

#### Scenario: Thread authority alone cannot change native execution settings
- **WHEN** a caller with the thread-runner effects supplies a whitelisted native session selector or model override
- **THEN** the gateway checks the requested native effect before submitting work
- **AND THEN** a missing native effect produces a refusal before stream admission

#### Scenario: A runner submits to a different thread
- **WHEN** Alice targets a thread outside her bound template resource
- **THEN** the gateway denies the run before submitting work or opening the output stream

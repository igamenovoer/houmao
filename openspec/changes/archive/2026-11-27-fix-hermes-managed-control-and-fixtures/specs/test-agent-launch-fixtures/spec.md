# Spec Delta

## MODIFIED Requirements

### Requirement: Fixture lifecycle uses captured ownership on either server

Fixture follow-up and cleanup SHALL use the captured agent or verify the run’s ownership at its captured terminal coordinates. Tmux-backed fixture tests SHALL use isolated test-owned socket resources, including tests of the shared default.

#### Scenario: One shared fixture stops without affecting another

- **WHEN** two fixture runs have active sessions on the same test-owned Houmao default server
- **AND WHEN** the operator stops the first run
- **THEN** only that run’s session stops and the second run can still be controlled

#### Scenario: A fixture follow-up runs from another tmux server

- **WHEN** the caller’s enclosing tmux socket differs from the run’s saved socket
- **THEN** fixture checks and terminal operations use the saved binding for that run

#### Scenario: A Stopped Manager Fixture Resumes the Same Runtime

- **WHEN** an operator relaunches a captured manager fixture through the manager and the captured runtime has a newer verified active generation
- **THEN** the next fixture prompt or stop uses that generation of the same runtime
- **AND THEN** the fixture refreshes its lifecycle snapshot while retaining the captured ownership and prior evidence
- **AND THEN** an existing run with verifiable legacy metadata remains usable

#### Scenario: Stop Confirms the Captured Runtime Is Already Stopped

- **WHEN** the fixture confirms that its captured manager runtime is stopped
- **THEN** stop succeeds without sending another lifecycle operation

#### Scenario: A Reused Agent ID Cannot Redirect Fixture Operations

- **WHEN** the captured identity resolves to a replacement runtime, an incomplete lifecycle transition, or authority that the fixture cannot verify
- **THEN** the fixture reports the ownership or lifecycle problem before prompting or stopping
- **AND THEN** it leaves the stored identity and existing evidence available for follow-up

## ADDED Requirements

### Requirement: Manager Fixture Failures Identify Private Diagnostics

When a manager command fails during fixture operation, the fixture SHALL report its exit status and the path to its private diagnostic when saved. Public errors SHALL omit raw command arguments, prompt content, credentials, and raw provider diagnostics.

#### Scenario: A Manager Prompt Fails

- **WHEN** the manager returns a failure for a fixture prompt
- **THEN** fixture error output retains its structured error message and includes the manager exit code and exact saved diagnostic path
- **AND THEN** the diagnostic remains private to that run and redacts credential values

#### Scenario: The Initial Prompt Fails After Birth

- **WHEN** a manager fixture captures a verified launch identity and its initial prompt fails
- **THEN** the failure retains that identity for scoped cleanup and reports the prompt diagnostic
- **AND THEN** prompt output cannot replace the captured launch authority

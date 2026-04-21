## ADDED Requirements

### Requirement: Pairwise-v3 initialize materializes per-agent memo guidance
The `initialize` guidance in `houmao-agent-loop-pairwise-v3` SHALL be the canonical prestart step that materializes run-owned guidance into the related agents' memo surfaces.

When the pairwise-v3 plan provides launch-profile references for required participants, `initialize` SHALL inspect the launch profile's mailbox association before launching that participant.

When the pairwise-v3 plan provides launch-profile references for required participants, `initialize` SHALL use those launch profiles to launch missing participants before email/mailbox verification and memo materialization continue.

If a required participant is still missing and no launch profile was provided for it, `initialize` SHALL fail closed rather than inventing a launch.

If a required participant's launch profile does not declare the mailbox association needed for the run's default email/mailbox communication posture, `initialize` SHALL fail closed before launching that participant.

For the designated master, `initialize` SHALL write memo material that captures the run's organization rules, objective, workspace contract summary, participant set, delegation boundaries, completion posture, stop posture, and the routing or dispatch guidance needed to supervise the run.

For each additional participant whose managed memory is being used, `initialize` SHALL write memo material that captures that participant's local goal, immediate-driver relationship, allowed obligations, result-return contract, and relevant workspace or bookkeeping posture.

Before pairwise-v3 `initialize` reaches `ready`, it SHALL verify that the designated master and every required participant can participate in the email/mailbox communication posture used by the run.

If any required participant lacks that email/mailbox support, pairwise-v3 `initialize` SHALL fail closed and SHALL NOT treat the run as ready for ordinary `start`.

The same email/mailbox capability check SHALL block `recover_and_continue` from returning the run to `running`.

When `recover_and_continue` restores one run whose accepted posture included agent email notification, it SHALL re-enable that notification for rebound participants that expose the required live gateway and mailbox surfaces before the run returns to `running`.

Pairwise-v3 `initialize` SHALL NOT require a durable initialize page plus memo-pointer pattern as the ordinary participant-facing contract for v3.

#### Scenario: Initialize writes master and worker memo guidance
- **WHEN** a pairwise-v3 run completes `initialize`
- **THEN** the designated master's memo contains the durable supervision contract for that run
- **AND THEN** each participant memo contains the local run guidance that participant needs before execution begins

#### Scenario: Initialize launches missing participants from provided launch profiles
- **WHEN** a pairwise-v3 run is being initialized
- **AND WHEN** one required participant is missing but the plan provides a launch profile for that participant
- **THEN** `initialize` launches that participant before continuing
- **AND THEN** email/mailbox verification and memo materialization use the launched participant

#### Scenario: Initialize refuses launch profiles without mailbox association
- **WHEN** a pairwise-v3 run is being initialized
- **AND WHEN** one required participant is missing
- **AND WHEN** the plan provides a launch profile for that participant but that profile does not declare mailbox association
- **THEN** `initialize` fails closed before launching that participant
- **AND THEN** the run does not become ready

#### Scenario: Initialize refuses missing participants without launch profiles
- **WHEN** a pairwise-v3 run is being initialized
- **AND WHEN** one required participant is missing and the plan provides no launch profile for that participant
- **THEN** `initialize` fails closed
- **AND THEN** the run does not become ready

#### Scenario: Initialize does not rely on durable initialize pages for ordinary v3 start
- **WHEN** a pairwise-v3 run uses the ordinary memo-first initialize flow
- **THEN** the participant-facing prestart contract is materialized directly into memo surfaces
- **AND THEN** ordinary start does not depend on a separate durable initialize page being created first

#### Scenario: Initialize refuses runs without email capability
- **WHEN** a pairwise-v3 run is being initialized
- **AND WHEN** the designated master or any required participant lacks email/mailbox support
- **THEN** the system refuses to treat the run as ready
- **AND THEN** ordinary `start` does not proceed

#### Scenario: Recovery refuses runs without email capability
- **WHEN** a pairwise-v3 run is being restored through `recover_and_continue`
- **AND WHEN** the designated master or any required participant lacks email/mailbox support
- **THEN** the system refuses to return the run to `running`
- **AND THEN** continuation does not proceed

#### Scenario: Recovery re-enables agent email notification
- **WHEN** a pairwise-v3 run is being restored through `recover_and_continue`
- **AND WHEN** rebound participants expose the required live gateway and mailbox surfaces
- **THEN** the system re-enables their agent email notification posture before the run returns to `running`
- **AND THEN** the recovery summary reports that notifier restoration

### Requirement: Pairwise-v3 ordinary start is a lightweight memo-read trigger
The ordinary `start` guidance in `houmao-agent-loop-pairwise-v3` SHALL treat `initialize` as the readiness boundary and SHALL send a compact kickoff trigger only after `initialize` is complete.

That kickoff trigger SHALL target the designated master and SHALL instruct the master to read its memo material and begin the run.

Pairwise-v3 ordinary `start` SHALL send that kickoff through the run's mail-capable communication posture by default.

Pairwise-v3 ordinary `start` SHALL use direct prompt delivery only when the user explicitly requests that transport.

Pairwise-v3 ordinary `start` SHALL NOT require writing or refreshing a durable `start-charter` page.

Pairwise-v3 ordinary `start` SHALL NOT require an explicit `accepted` or `rejected` reply from the designated master before the run is treated as started.

#### Scenario: Start triggers the master without start-charter material
- **WHEN** a pairwise-v3 run is ready after `initialize`
- **THEN** ordinary `start` sends a compact kickoff trigger to the designated master
- **AND THEN** that trigger does not depend on a durable `start-charter` page

#### Scenario: Start uses mail delivery by default
- **WHEN** ordinary `start` is invoked for a pairwise-v3 run whose initialize work is complete
- **AND WHEN** the user did not explicitly request direct prompt delivery
- **THEN** the system sends the kickoff trigger through mail
- **AND THEN** it does not default to direct prompt delivery

#### Scenario: Start does not wait for master acceptance
- **WHEN** ordinary `start` is invoked for a pairwise-v3 run whose initialize work is complete
- **THEN** the system does not wait for an explicit `accepted` or `rejected` reply from the designated master
- **AND THEN** the run proceeds based on the memo material already prepared during `initialize`

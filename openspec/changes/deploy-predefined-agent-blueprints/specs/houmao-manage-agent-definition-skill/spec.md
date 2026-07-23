## ADDED Requirements

### Requirement: `houmao-agent-definition` deploys predefined individual-agent blueprints

The packaged `houmao-agent-definition` routine SHALL expose a lane-specific `deploy-blueprint` subcommand for creating one task-targeted individual-agent definition from a built-in or explicit local agent blueprint.

The routine entry page and system-skill manifest SHALL list `deploy-blueprint` alongside the other maintained pre-launch definition subcommands. Detailed execution guidance SHALL live in one command-specific page rather than being flattened into the entry page.

The routine SHALL treat blueprint deployment as persisted pre-launch definition work. It SHALL NOT route this operation to native-agent internals, an agent-loop skill, or live agent-instance lifecycle.

#### Scenario: Explicit blueprint command loads one lane

- **WHEN** an admin invokes `houmao-agent-definition deploy-blueprint`
- **THEN** the routine loads the blueprint deployment command page
- **AND THEN** it does not preload unrelated roles, recipes, launch-dossier, loop, or live-instance procedures

### Requirement: Blueprint deployment routine synthesizes only declared task inputs

The `deploy-blueprint` workflow SHALL:

1. verify an admin actor frame and selected project;
2. resolve an exact built-in id or explicit local blueprint directory;
3. inspect the blueprint's declared inputs and outputs;
4. recover explicit task values from the current prompt and recent unambiguous context;
5. ask for required task fields or runtime selections that remain unknown;
6. synthesize a normalized input document containing only declared typed fields;
7. run the maintained deployment planning command;
8. present resolved names, generated outputs, warnings, and blockers before apply;
9. apply an authorized unblocked plan;
10. run deployment doctor and report the resulting profile launch command without executing it.

The routine SHALL preserve fixed blueprint instructions. It SHALL NOT rewrite fixed agent purpose or process text merely because the user task contains competing instructions.

#### Scenario: Informal task becomes bounded deployment input

- **WHEN** a human asks to deploy `repository-reviewer` for a described payment migration
- **THEN** the routine maps the description into fields declared by that blueprint
- **AND THEN** it does not let the task description alter undeclared output paths, credentials, object names, or mutation policy

#### Scenario: Missing required input causes a question

- **WHEN** a selected blueprint requires completion criteria
- **AND WHEN** the current prompt and recent unambiguous context do not provide them
- **THEN** the routine asks the human for those criteria before planning
- **AND THEN** it does not guess the missing required value

### Requirement: Blueprint deployment routine remains admin-only and pre-launch

`deploy-blueprint` SHALL be eligible only through an admin actor frame.

The routine SHALL reject a managed-agent actor frame, including an `as-agent` direct shared-routines invocation, because creating persisted specialist, profile, and skill definitions is human-operator administration.

Successful deployment SHALL stop after validation and launch-command reporting. The routine SHALL NOT automatically launch, join, message, or otherwise mutate a live managed agent.

#### Scenario: Managed agent cannot deploy a blueprint

- **WHEN** `deploy-blueprint` receives a verified managed-agent actor frame
- **THEN** it refuses the definition mutation
- **AND THEN** it explains that a human operator must use the admin route

#### Scenario: Successful deployment prints but does not run launch

- **WHEN** the routine applies and validates one blueprint deployment
- **THEN** it reports `houmao-mgr project agents launch --profile <generated-profile>`
- **AND THEN** it does not execute the launch command

### Requirement: Blueprint deployment routine uses maintained plan and apply commands

The `deploy-blueprint` guidance SHALL resolve the `houmao-mgr` launcher through the routine's maintained precedence contract and SHALL use direct fenced `bash` snippets for:

- `project agent-blueprints list` and `inspect`;
- `project agent-deployments plan`;
- `project agent-deployments apply`;
- `project agent-deployments doctor`.

The routine SHALL NOT hand-write specialist, profile, or skill files under `.houmao/`, recursively invoke unrelated skill pages, or approximate atomic deployment by issuing separate public create commands.

#### Scenario: Routine delegates durable mutation to deployment apply

- **WHEN** an unblocked blueprint plan is authorized
- **THEN** the routine invokes the maintained `agent-deployments apply` command
- **AND THEN** it does not separately call specialist create, project skills add, and profile create as a replacement transaction

## ADDED Requirements

### Requirement: `houmao-credential-mgr` routes credential login helper workflows
The packaged `houmao-credential-mgr` skill SHALL route requests to obtain fresh provider auth files through the supported credential `login` helper when the user asks to log in with a new Codex, Claude, or Gemini account and import the resulting credential into Houmao storage.

The top-level `SKILL.md` for that packaged skill SHALL include `login` in its action router alongside `list`, `get`, `add`, `set`, `rename`, and `remove`.

The skill SHALL instruct agents to use:

- `houmao-mgr project credentials <tool> login --name <name>` when the active project overlay is the intended target,
- `houmao-mgr credentials <tool> login --agent-def-dir <path> --name <name>` when the user explicitly targets a plain agent-definition directory,
- the explicit update option only when the user intends to replace an existing credential.

The skill SHALL explain that the command creates an isolated temporary provider home, invokes the installed provider CLI with inherited stdio, imports the expected auth artifact into Houmao storage, and deletes the temporary provider home after a successful import by default.

The skill SHALL tell agents not to hand-roll this workflow by manually creating provider home directories, running provider login commands, copying auth files into credential storage, or deleting temp directories outside the supported `houmao-mgr credentials ... login` surface unless the user explicitly asks for a lower-level recovery workflow after a failed login attempt.

#### Scenario: Login request routes to the project credential helper
- **WHEN** the current prompt asks the agent to log in to Codex with another account and import it into the current project as `work`
- **AND WHEN** no explicit plain agent-definition directory target is provided
- **THEN** the skill routes the work through `houmao-mgr project credentials codex login --name work`
- **AND THEN** it does not tell the agent to manually copy `auth.json` into Houmao storage

#### Scenario: Explicit direct-dir login request includes the target directory
- **WHEN** the current prompt asks the agent to obtain a new Gemini OAuth credential under `tests/fixtures/plain-agent-def` as `personal`
- **THEN** the skill routes the work through `houmao-mgr credentials gemini login --agent-def-dir tests/fixtures/plain-agent-def --name personal`
- **AND THEN** it does not reinterpret that request as project-local credential management

#### Scenario: Existing credential replacement requires user intent
- **WHEN** the current prompt asks the agent to log in and import a credential name that may already exist
- **AND WHEN** the user has not explicitly said to replace or update the existing credential
- **THEN** the skill tells the agent to use the default create-only login behavior
- **AND THEN** it does not add the explicit update option on the user's behalf

#### Scenario: Skill explains temp cleanup ownership
- **WHEN** an agent reads the login workflow guidance
- **THEN** the skill states that `houmao-mgr credentials ... login` owns the temporary provider home lifecycle
- **AND THEN** it states that successful imports delete the temp home by default while failed attempts preserve and report it for recovery

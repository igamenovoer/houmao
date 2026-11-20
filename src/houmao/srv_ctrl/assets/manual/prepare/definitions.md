# Choose a Specialist, Profile, or Definition

Use this when preparing or reusing a worker. A specialist defines the worker's role, tool, and skill bindings. Reuse an existing specialist when it fits. Use `project skills` to register shared project skills and `project specialist` to bind them to the role.

Create a `project profile` when launches from the same specialist need recurring choices such as workdir, credentials, run mode, mailbox, or memo seed. Use `project profile get --name "$profile"` to confirm the source specialist and saved defaults.

Use an immutable Agent Definition Revision when the role, skills, and typed deployment inputs need to move together across projects. Run `project agent-definitions plan` for the chosen revision, review the inputs and plan, then apply it. Verify the deployment and record the returned `project agents launch` handoff. Run it when the user asks to start the worker.

For syntax, run `houmao-mgr project agent-definitions --help`. [Launch Profiles](https://igamenovoer.github.io/houmao/getting-started/launch-profiles/) · [Agent Definitions](https://igamenovoer.github.io/houmao/getting-started/agent-definitions/)

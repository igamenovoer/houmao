# Choose and Verify Workspaces

Select where each worker should read and write before launching it. Share a workdir when agents need the same uncommitted files and writes are coordinated. Use separate Git worktrees when agents will edit independently. Each worktree has its own working files, so pass a commit or patch when a worker needs another worktree's changes.

Set the launch workdir explicitly and verify each target's location, branch or revision, and access to the required inputs. The project selection still determines which Houmao definitions and configuration the launch uses.

A deployed definition can also provide a private workspace for its individual agent. Inspect that workspace with `agents single --agent-id <id> instance-state workspace inspect`. Inside a verified managed session, `agents self instance-state workspace resolve workspace.artifacts` resolves a declared artifact label to its path. Use the resolved path for the deliverable and verify it is accessible to anyone receiving it.

See `houmao-mgr project agents launch --help` for workdir selection. [Private workspaces](https://igamenovoer.github.io/houmao/getting-started/agent-definitions/#optional-private-workspaces)

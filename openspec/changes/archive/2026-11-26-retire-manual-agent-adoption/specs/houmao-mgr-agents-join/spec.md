## REMOVED Requirements

### Requirement: `houmao-mgr agents join` adopts an existing supported TUI from the current tmux session

**Reason:** Manual TUI adoption is retired. Managed lifecycle authority originates at launch.

**Migration:** Launch a new managed TUI through a supported Houmao launch. Wind down management of an existing joined session with its owning release before upgrading.

### Requirement: `houmao-mgr agents join --headless` adopts a tmux-backed native headless logical session

**Reason:** Manual headless adoption is retired.

**Migration:** Launch a new managed headless agent. Use managed relaunch for supported provider-native chat continuation within a managed runtime.

### Requirement: `houmao-mgr agents join` fails closed when adoption authority is incomplete or inconsistent

**Reason:** The adoption command and its authority checks are retired.

**Migration:** Use a supported managed launch. The previous release remains the tool for winding down an existing joined runtime.

### Requirement: `houmao-mgr agents join` exposes an explicit opt-out for default Houmao-owned system-skill installation

**Reason:** The retired command no longer installs skills into an adopted native home.

**Migration:** Use the supported managed-launch skill policy or the explicit system-skill installation workflow.

### Requirement: `houmao-mgr agents join` creates memo-pages memory for adopted sessions

**Reason:** Adoption no longer creates managed session memory.

**Migration:** Use the memory provisioned by a supported managed launch. Keep existing files when winding down the joined runtime.

### Requirement: Joined tmux sessions persist primary surface handles without changing adoption authority

**Reason:** Joined manifests no longer confer managed terminal authority.

**Migration:** Use the recorded primary terminal surface of a supported Houmao-launched runtime.

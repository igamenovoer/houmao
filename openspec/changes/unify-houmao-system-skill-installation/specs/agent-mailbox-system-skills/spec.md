## MODIFIED Requirements

### Requirement: Joined-session adoption installs Houmao-owned mailbox skills by default
When `houmao-mgr agents join` adopts a mailbox-enabled session, the join workflow SHALL install the current Houmao-owned system-skill selection resolved from the packaged catalog’s managed-join auto-install set list for the adopted tool home by default so later runtime-owned prompts can rely on the current Houmao-owned mailbox skills being installed.

That joined-session installation SHALL:
- resolve the adopted tool home through the join workflow’s authoritative home-resolution path,
- invoke the shared Houmao system-skill installer rather than a mailbox-only installation code path,
- include the current Houmao-owned mailbox skills in the resolved managed-join auto-install selection for the adopted tool,
- project Houmao-owned mailbox skills only under reserved `houmao-<skillname>` paths in the visible skill destination for that tool,
- preserve unrelated user-authored skill directories,
- fail explicitly when default installation is required but the target skill destination cannot be resolved or updated safely.

The join workflow MAY expose an explicit operator opt-out for default Houmao-owned skill installation. When that opt-out is used, later runtime-owned mailbox prompts and docs SHALL NOT assume the current Houmao-owned mailbox skills are installed for that joined session.

#### Scenario: Joined mailbox-enabled session receives the managed-join mailbox skill set by default
- **WHEN** an operator uses `houmao-mgr agents join` to adopt a mailbox-enabled session without opting out of Houmao skill installation
- **THEN** the join workflow installs the current Houmao-owned system-skill selection resolved from the managed-join auto-install set list into the adopted tool home
- **AND THEN** that resolved selection includes the current Houmao-owned mailbox skills needed for later runtime-owned mailbox prompts

#### Scenario: Join preserves unrelated user-authored skills
- **WHEN** `houmao-mgr agents join` installs the current Houmao-owned system-skill selection resolved from the managed-join auto-install set list into an adopted tool home
- **THEN** it writes only to reserved Houmao-owned skill paths for the current skill set
- **AND THEN** it does not delete or overwrite unrelated user-authored non-Houmao skill directories in that same visible skill destination

#### Scenario: Join fails closed when required default Houmao-owned skill installation cannot complete
- **WHEN** `houmao-mgr agents join` is using default Houmao-owned current-skill installation
- **AND WHEN** the adopted tool home or skill destination cannot be resolved or updated safely
- **THEN** the join command fails explicitly
- **AND THEN** it does not publish a managed session whose later runtime prompts would assume missing Houmao-owned mailbox skills

#### Scenario: Explicit join opt-out disables the installed-mailbox-skill assumption
- **WHEN** an operator uses the explicit opt-out for default Houmao-owned skill installation during `houmao-mgr agents join`
- **THEN** the join workflow may continue without projecting the current Houmao-owned mailbox skills
- **AND THEN** later runtime-owned mailbox prompts for that joined session do not assume the current Houmao-owned mailbox skills are installed

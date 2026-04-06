## Why

Operators currently have only one projection mode for Houmao-owned system skills: copy the packaged skill tree into the target tool home. That is portable, but it is inefficient for local development and maintenance workflows where an operator wants the installed skill directory to follow the packaged asset in place instead of duplicating it into every home.

## What Changes

- Add an explicit `--symlink` flag to `houmao-mgr system-skills install` for operator-driven installs into an explicit tool home.
- Make `--symlink` install each selected Houmao-owned skill as a directory symlink in the tool-native skill root instead of copying the packaged skill tree.
- Require `--symlink` installs to use absolute filesystem targets for the packaged skill asset root so the link does not depend on project-relative layout.
- Extend Houmao-owned system-skill install state to record which projection mode owns each installed skill so reinstall and migration between copy and symlink modes remain safe and idempotent.
- Extend `houmao-mgr system-skills status` to report the recorded projection mode for installed Houmao-owned skills.
- Keep the default installer behavior and Houmao-managed auto-install flows copy-based in this change.
- Fail explicit symlink installation when the packaged skill asset cannot be addressed as a real filesystem directory.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-system-skill-installation`: The shared installer gains an explicit symlink projection mode for operator-driven installs, records projection mode in install state, and preserves safe replacement semantics when projection mode changes.
- `houmao-mgr-system-skills-cli`: The CLI install surface gains `--symlink` and the status surface reports projection mode for installed Houmao-owned skills.

## Impact

Affected areas include [`src/houmao/agents/system_skills.py`](/data1/huangzhe/code/houmao/src/houmao/agents/system_skills.py), [`src/houmao/srv_ctrl/commands/system_skills.py`](/data1/huangzhe/code/houmao/src/houmao/srv_ctrl/commands/system_skills.py), and the unit tests covering installer behavior and CLI output. The install-state JSON schema/version and operator-facing docs for `houmao-mgr system-skills` will also need updates.

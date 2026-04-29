## Why

Launch profiles can currently override launch posture, auth, model, prompt, mailbox, and memo behavior, but they cannot add profile-specific skills without changing the underlying specialist or recipe. Operators need reusable per-profile skill overlays, including private path-backed skills for one profile, without forcing every temporary or experimental skill into the shared project skill repository.

## What Changes

- Allow explicit launch profiles and easy profiles to reference additional registered project skills by name.
- Allow explicit launch profiles and easy profiles to store profile-private skill paths that are projected only during agent launch.
- Add CLI patch operations:
  - `--add-registered-skill <name>`
  - `--remove-registered-skill <name>`
  - `--add-private-skill <path>` for copy-mode private skills
  - `--add-private-skill-symlink <path>` for symlink-mode private skills
  - `--remove-private-skill <path>`
- Keep registered skill references tied to the existing project skill registry; registered skill projection continues to use the current registered-skill contract.
- Keep private path skills out of the project skill registry and out of `.houmao/content/skills/`; they are copied or symlinked into the built agent home only for launches from that profile.
- Define deterministic merge behavior where profile-private skill names take precedence over source or registered skills with the same installed skill directory name.
- Extend launch provenance and profile inspection output to report registered and private profile skill overlays.
- Prevent project skill removal while a stored launch profile still references that project skill by name.

## Capabilities

### New Capabilities

### Modified Capabilities
- `houmao-mgr-project-agents-launch-profiles`: Explicit launch profiles can store and patch registered and private skill overlays.
- `houmao-mgr-project-easy-cli`: Easy profiles can store and patch the same registered and private skill overlays.
- `houmao-mgr-agents-launch`: Launch-profile-backed managed launch merges source skills, registered profile skills, and private profile skills before brain-home construction.
- `houmao-mgr-project-skills-cli`: Project skill removal protects project skills referenced by launch profiles as well as specialists.

## Impact

- Affects project catalog schema and projection rendering for launch profiles.
- Affects explicit launch-profile and easy-profile CLI option parsing, get/list payloads, and mutation semantics.
- Affects managed brain-home construction to support profile-private skill source projections.
- Affects project skill removal validation.
- Adds unit coverage for profile storage, projection YAML, launch merge precedence, private skill copy/symlink projection, and removal protection.

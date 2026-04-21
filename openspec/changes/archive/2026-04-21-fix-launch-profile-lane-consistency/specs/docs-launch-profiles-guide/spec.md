## ADDED Requirements

### Requirement: Launch-profiles guide explains lane-bounded management over shared storage
The launch-profiles guide SHALL explain that easy profiles and explicit launch profiles share one catalog-backed launch-profile family and project into the same compatibility path family under `.houmao/agents/launch-profiles/<name>.yaml`.

The guide SHALL also state that this shared storage and shared projection path do not make the two command families interchangeable.

At minimum, the guide SHALL explain:

- easy profiles are managed through `houmao-mgr project easy profile ...`,
- explicit launch profiles are managed through `houmao-mgr project agents launch-profiles ...`,
- wrong-lane management attempts fail with guidance to the correct command family instead of reading, mutating, or deleting the other lane's profile.

#### Scenario: Reader understands shared projection path does not collapse lane ownership
- **WHEN** a reader studies the launch-profiles guide to understand why both profile kinds appear under `.houmao/agents/launch-profiles/`
- **THEN** the guide explains that both lanes share the same stored launch-profile family and compatibility projection path
- **AND THEN** the guide explains that easy and explicit profile management remains lane-bounded
- **AND THEN** the guide directs the reader to `project easy profile ...` for easy profiles and `project agents launch-profiles ...` for explicit launch profiles

## MODIFIED Requirements

### Requirement: Shared agent registry uses a fixed per-user root with isolated live-agent directories
The shared agent registry SHALL keep its fixed per-user root under the Houmao-owned home anchor and SHALL support an env-var override named `HOUMAO_GLOBAL_REGISTRY_DIR`.

When `HOUMAO_GLOBAL_REGISTRY_DIR` is set to an absolute directory path, the system SHALL use that value as the effective registry root instead of the home-relative default. The override SHALL support CI, tests, and similarly controlled environments.

#### Scenario: Env-var override relocates the shared registry root
- **WHEN** `HOUMAO_GLOBAL_REGISTRY_DIR` is set to an absolute directory path
- **THEN** the system uses that directory as the effective shared registry root

### Requirement: Shared-registry records persist authoritative agent identity rather than registry-specific agent keys
Shared-registry records SHALL persist the canonical `HOUMAO-...` agent identity together with the authoritative `agent_id`.

When the system bootstraps an initial `agent_id` from canonical agent identity, it SHALL use the full lowercase `md5("HOUMAO-<name>").hexdigest()` value.

#### Scenario: Initial authoritative agent id is derived from the HOUMAO canonical name
- **WHEN** the system bootstraps the initial `agent_id` for canonical agent name `HOUMAO-gpu`
- **THEN** it uses the full lowercase `md5("HOUMAO-gpu").hexdigest()` value as the authoritative identity

### Requirement: Shared registry agent-name input accepts an optional `AGENTSYS-` prefix and canonicalizes internally
The shared registry SHALL accept agent-name input in namespace-free form such as `gpu` or in canonical Houmao form such as `HOUMAO-gpu`.

When the caller omits the exact `HOUMAO-` prefix, the system SHALL canonicalize the input to `HOUMAO-<name>` before hashing, publication, duplicate detection, lookup, or record comparison.

#### Scenario: Namespace-free agent input is canonicalized to the HOUMAO form
- **WHEN** a caller resolves shared-registry agent input `gpu`
- **THEN** the system canonicalizes that input to `HOUMAO-gpu` before publication, duplicate detection, lookup, or record comparison

#### Scenario: Canonical HOUMAO agent input is accepted directly
- **WHEN** a caller resolves shared-registry agent input `HOUMAO-gpu`
- **THEN** the system treats `HOUMAO-gpu` as the canonical name


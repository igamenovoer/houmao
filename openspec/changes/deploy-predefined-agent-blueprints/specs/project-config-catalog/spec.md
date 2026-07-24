## ADDED Requirements

### Requirement: Project catalog stores canonical Agent Deployment ownership
The project catalog SHALL store one ordinary Agent Deployment record with definition, request, plan, generated project-object, managed-content, registered-skill, and instance-contract relationships.

#### Scenario: Applied deployment is inspected
- **WHEN** an operator inspects an applied Agent Deployment
- **THEN** the catalog SHALL identify every owned project object and file-backed content reference

### Requirement: Large deployment content remains file-backed
Definition snapshots, requests, plans, rendered files, and registered-skill trees SHALL remain file-backed with catalog relationships and digests.

#### Scenario: Registered skill is reused by digest
- **WHEN** two deployments use byte-identical immutable registered-skill content
- **THEN** the project MAY share one cached content object while preserving both deployment relationships

### Requirement: Deployment provenance contains references without secrets
The catalog SHALL record resolved tool and credential identities, typed deployment inputs, and content digests. It SHALL NOT store credential secrets.

#### Scenario: Credential is selected
- **WHEN** a Deployment Request resolves a credential
- **THEN** the catalog SHALL store only the registered credential reference and compatibility evidence

### Requirement: Project migration adds deployment storage explicitly
Projects on the maintained preceding schema SHALL run `houmao-mgr project migrate` before Agent Deployment mutation.

#### Scenario: Old project attempts apply
- **WHEN** an unmigrated project plans or applies an Agent Deployment
- **THEN** Houmao SHALL fail with exact migration guidance

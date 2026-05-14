## ADDED Requirements

### Requirement: V5 pairwise-named loop skill presents tree loop terminology
The packaged `houmao-agent-loop-pairwise-v5` skill SHALL keep its skill name, packaged asset directory name, and explicit activation handle unchanged.

The skill SHALL describe tree-loop behavior as the canonical local-close tree or forest topology when it explains generated loop topology to users.

The skill SHALL present `pairwise loop` as a legacy alias only where useful for compatibility with the package name or older user language.

The skill body SHALL not introduce extra "v5" branding outside the skill name or package identity.

#### Scenario: V5 remains explicitly invokable
- **WHEN** a user explicitly invokes `houmao-agent-loop-pairwise-v5`
- **THEN** the skill remains the correct packaged entrypoint
- **AND THEN** the user-facing workflow describes tree-loop behavior instead of making pairwise loop the primary concept name

#### Scenario: V5 avoids extra version branding
- **WHEN** v5 guidance is revised for terminology
- **THEN** added prose avoids unnecessary `v5` wording in the skill body
- **AND THEN** the package name and explicit invocation handle remain unchanged

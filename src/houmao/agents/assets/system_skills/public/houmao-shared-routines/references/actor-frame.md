# Actor Frame Contract

Every shared child or loop sibling receives an immutable frame with `actor_kind`, `entrypoint_name`, `verified_self_identity`, `requested_target`, `selected_route`, and `selected_operation`.

Admin frames use `verified_self_identity=null`, require explicit targets for target-sensitive work, and never reinterpret the current session as self. Agent frames require freshly verified self identity before every substantive route, default to that self only where supported, and require an explicit target for peer work. Direct shared and loop calls default to admin; a leading `as-agent` qualifier creates a fresh verified-agent frame. Missing or mismatched frames fail closed at every child or sibling boundary.

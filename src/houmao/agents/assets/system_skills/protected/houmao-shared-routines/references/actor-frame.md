# Actor Frame Contract

Every protected route receives an immutable frame with `actor_kind`, `entrypoint_name`, `verified_self_identity`, `requested_target`, and `selected_routine`.

Admin frames use `verified_self_identity=null`, require explicit targets for target-sensitive work, and never reinterpret the current session as self. Agent frames require freshly verified self identity before every substantive route, default to that self where supported, and require an explicit target for peer work. Missing or mismatched frames fail closed at every protected router.

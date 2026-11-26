# Spec Delta

## REMOVED Requirements

### Requirement: Joined-session adoption creates a new agent frame after success
**Reason**: The explicit adoption path no longer establishes agent identity in the caller's session.
**Migration**: Use the agent entrypoint from a verified Houmao-launched runtime. The caller retains its admin frame.

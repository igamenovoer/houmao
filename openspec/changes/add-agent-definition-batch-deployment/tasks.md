## 1. Batch Request and Planning

- [x] 1.1 Add Batch Deployment Request models with count, shared inputs, member overrides, and explicit delegation flags
- [x] 1.2 Add field-limited name, registered-tool, and existing-credential-reference candidate validation
- [x] 1.3 Expand one Batch Request into ordered ordinary member Deployment Requests
- [x] 1.4 Reuse single-deployment planning for each member
- [x] 1.5 Add cross-member name, path, tool, credential, and project collision validation
- [x] 1.6 Add Batch Deployment Plan serialization, digests, preview, and focused tests

## 2. Recoverable Batch Apply

- [x] 2.1 Add batch operation ids, journal states, and operation-owned staging paths
- [x] 2.2 Prepare every member before catalog visibility
- [x] 2.3 Insert all ordinary Agent Deployments through one catalog transaction
- [x] 2.4 Record operation id and member ordinal on each deployment without adding a batch entity
- [x] 2.5 Add doctor recovery for interrupted preparation, commit, and publication
- [x] 2.6 Add failure-injection tests proving no partial catalog-visible member set

## 3. CLI, Skills, and Verification

- [x] 3.1 Add maintained batch plan, apply, inspect-operation, and doctor commands
- [x] 3.2 Extend the existing Agent Definition routine with plural collection and delegation preview
- [x] 3.3 Update admin-entrypoint and shared-routines routing while preserving admin-only posture
- [x] 3.4 Return one launch handoff per successful member without launching
- [x] 3.5 Add UC-03 behavior tests, operator documentation, and strict OpenSpec validation
- [x] 3.6 Run focused suites plus project format, lint, typecheck, and unit tests

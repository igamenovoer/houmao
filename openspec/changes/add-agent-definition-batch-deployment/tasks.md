## 1. Batch Request and Planning

- [ ] 1.1 Add Batch Deployment Request models with count, shared inputs, member overrides, and explicit delegation flags
- [ ] 1.2 Add field-limited name, registered-tool, and existing-credential-reference candidate validation
- [ ] 1.3 Expand one Batch Request into ordered ordinary member Deployment Requests
- [ ] 1.4 Reuse single-deployment planning for each member
- [ ] 1.5 Add cross-member name, path, tool, credential, and project collision validation
- [ ] 1.6 Add Batch Deployment Plan serialization, digests, preview, and focused tests

## 2. Recoverable Batch Apply

- [ ] 2.1 Add batch operation ids, journal states, and operation-owned staging paths
- [ ] 2.2 Prepare every member before catalog visibility
- [ ] 2.3 Insert all ordinary Agent Deployments through one catalog transaction
- [ ] 2.4 Record operation id and member ordinal on each deployment without adding a batch entity
- [ ] 2.5 Add doctor recovery for interrupted preparation, commit, and publication
- [ ] 2.6 Add failure-injection tests proving no partial catalog-visible member set

## 3. CLI, Skills, and Verification

- [ ] 3.1 Add maintained batch plan, apply, inspect-operation, and doctor commands
- [ ] 3.2 Extend the existing Agent Definition routine with plural collection and delegation preview
- [ ] 3.3 Update admin-entrypoint and shared-routines routing while preserving admin-only posture
- [ ] 3.4 Return one launch handoff per successful member without launching
- [ ] 3.5 Add UC-03 behavior tests, operator documentation, and strict OpenSpec validation
- [ ] 3.6 Run focused suites plus project format, lint, typecheck, and unit tests

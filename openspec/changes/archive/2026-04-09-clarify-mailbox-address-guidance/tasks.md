## 1. Runtime Default Alignment

- [x] 1.1 Update late filesystem mailbox binding so omitted `address` input derives the ordinary Houmao mailbox address pattern `<agentname>@houmao.localhost` instead of reconstructing `<principal_id>@agents.localhost`.
- [x] 1.2 Add or update focused automated coverage for omitted late-binding address derivation, including the split between principal id `HOUMAO-<agentname>` and mailbox address `<agentname>@houmao.localhost`.

## 2. System Skill Guidance

- [x] 2.1 Update `houmao-mailbox-mgr` guidance for mailbox account creation and late binding so it explains that `HOUMAO-*` mailbox local parts under `houmao.localhost` are reserved for Houmao-owned system principals.
- [x] 2.2 Update `houmao-mailbox-mgr` and `houmao-touring` examples to use address `research@houmao.localhost` with principal id `HOUMAO-research` and to recommend `houmao.localhost` when the user has not specified a mailbox domain.

## 3. Docs And Verification

- [x] 3.1 Update affected getting-started, CLI, and mailbox-reference pages so active mailbox account creation examples no longer teach `HOUMAO-...@agents.localhost` as the ordinary managed-agent pattern.
- [x] 3.2 Run targeted validation for the late-binding default path and any touched documentation or skill assets, and record the relevant commands and results.

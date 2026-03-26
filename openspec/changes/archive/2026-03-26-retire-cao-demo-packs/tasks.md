## 1. Spec And Documentation Retirement

- [x] 1.1 Update active OpenSpec capability contracts to retire the CAO launcher demo pack and the CAO interactive demo capability family.
- [x] 1.2 Remove or rewrite active README and docs links that still present the retired CAO demo packs as supported workflows.
- [x] 1.3 Add or redirect active operator guidance to the maintained `scripts/demo/houmao-server-interactive-full-pipeline-demo/` workflow or existing retirement-reference pages.

## 2. Demo Pack Removal

- [x] 2.1 Delete `scripts/demo/cao-server-launcher/` and its tracked assets.
- [x] 2.2 Delete `scripts/demo/cao-interactive-full-pipeline-demo/` and its tracked assets.

## 3. Demo-Owned Source And Test Cleanup

- [x] 3.1 Remove workflow-exclusive source modules under `src/houmao/demo/cao_interactive_demo/` that exist only for the retired CAO interactive demo.
- [x] 3.2 Preserve shared helper modules or constants that maintained packs still import, and narrow package exports as needed so removing workflow modules does not break maintained imports.
- [x] 3.3 Remove unit and integration tests dedicated only to the retired CAO demo packs.

## 4. Verification

- [x] 4.1 Run targeted searches to confirm active docs, tests, and specs no longer advertise the retired CAO demo packs as supported workflows.
- [x] 4.2 Run the relevant targeted test subset for any preserved helper modules still used by maintained packs.

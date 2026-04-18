## 1. Gateway notifier state and prompt rendering

- [x] 1.1 Extend gateway mail-notifier request/status models and durable notifier storage with `appendix_text`, preserving omitted-vs-provided semantics for `PUT`.
- [x] 1.2 Update gateway notifier runtime logic so `GET` returns effective appendix text, `PUT` preserves or replaces it correctly, `DELETE` disables polling without erasing it, and notifier prompt rendering appends non-empty appendix text.
- [x] 1.3 Add or update gateway runtime tests for appendix status reads, omitted-field preservation, empty-string clearing, disable preservation, and prompt rendering behavior.

## 2. Launch-profile and easy-profile defaults

- [x] 2.1 Extend the shared launch-profile model and persistence layer with an optional gateway mail-notifier appendix default.
- [x] 2.2 Update `houmao-mgr project agents launch-profiles` and `houmao-mgr project easy profile` to set, report, and clear the stored notifier appendix default.
- [x] 2.3 Update launch/runtime materialization so profile-owned appendix defaults seed runtime gateway notifier state for future notifier control without rewriting stored profiles from later live edits.
- [x] 2.4 Add or update tests covering explicit launch-profile and easy-profile appendix defaults plus launch-time seeding into runtime notifier state.

## 3. Proxy and CLI surfaces

- [x] 3.1 Update direct/passive/server gateway clients, services, and app routes so managed-agent gateway mail-notifier proxy calls preserve `appendix_text` unchanged in both request and response paths.
- [x] 3.2 Extend `houmao-mgr agents gateway mail-notifier` to accept appendix text on enable and display effective appendix text in notifier output.
- [x] 3.3 Add or update proxy and CLI tests covering non-empty appendix forwarding, empty-string clearing, omitted appendix preservation, and emitted status fields.

## 4. Documentation and validation

- [x] 4.1 Update gateway mail-notifier reference docs and launch-profile docs to describe appendix state, API semantics, launch-profile defaults, easy-profile coverage, and prompt-rendering behavior.
- [x] 4.2 Run the relevant targeted test suites for gateway runtime, launch profiles, easy profiles, passive/server proxy, and CLI notifier coverage and fix any contract mismatches they expose.

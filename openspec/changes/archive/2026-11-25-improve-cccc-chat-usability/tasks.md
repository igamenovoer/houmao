# Tasks

## 1. CLI Endpoint Diagnostics and Reply Hints

- [x] 1.1 Describe `--gateway-url` as the gateway base in CLI help and add the two fixed, redacted diagnostics. Extend `test_cccc_client.py` to verify a rejected plugin URL, malformed or credential-bearing input, and unavailable managed-self authority through the runtime client selection path. Verify failures make zero HTTP requests and a valid signer-bound HTTPS prefix is used for the selected instance.
- [x] 1.2 Render the gateway base and local plugin URLs with the ordinary chat reply example. Update the CCCC reference and `examples/cccc-gateway/agent-instructions.md` with the same inputs. Extend the offer test in `test_cccc_plugin.py` to verify a nondefault instance, the scoped reference, and delivery through ordinary dispatch. Check that the shown reply syntax parses with the current CLI.

## 2. Web and Headless Readiness

- [x] 2.1 Document the shared `GET /v1/status` preflight in the gateway protocol reference and link to it from the CCCC guide. Include surface-selected diagnostics, unconfirmed observations, live admission, and separate CCCC binding checks. Verify the documented statuses and paths against the Web and headless gateway projections and the CCCC binding response.

## 3. Delivery Receipt Ordering

- [x] 3.1 Describe newest-first creation order, the limit, and `has_more` in `chat deliveries --help`, the CCCC lookup reference, and the tracked provider protocol reference. Verify the CLI help output states the order and the gateway response preserves the provider list.
- [x] 3.2 Extend `test_handoff_receipt_retry_and_no_reconnect_replay` to assert the retry and original attempt IDs and states on the same event. Verify that a limit of one returns the retry with `has_more: true` against the pinned compatible provider using the existing isolated `HOUMAO_CCCC_TEST_URL` fixture.

## 4. Package Compatibility References

- [x] 4.1 Update `docs/reference/gateway/cccc.md` and `docs/reference/gateway/plugins.md` from the current SDK and package declarations. Verify SDK `2` and Houmao `>=3.0.0rc1,<4` against both package sources, and verify CCCC receiver protocol `1` against its provider reference. Run `pixi run docs-build` to check the updated guides and their links.

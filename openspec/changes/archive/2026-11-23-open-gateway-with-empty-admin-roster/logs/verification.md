# Verification

## Admission and Browser Handoff

The verified HTTPS fixture admitted unsigned status and controls with an empty roster. First enrollment required proof on both route classes, and final-key removal reopened them. The proxy refused browser handoff and ticket issuance through the advertised HTTPS address. The passive fixtures covered anonymous forwarding, a roster change before downstream admission, and revalidation before direct operations. [HTTPS integration](../../../../tests/integration/agents/realm_controller/test_gateway_https_access.py) · [Passive admission tests](../../../../tests/unit/passive_server/test_auth_admission.py)

A fresh Chromium session followed the bare owner-local gateway URL into DSH Web using an empty roster. It reached the clean native origin, selected the exact managed session, and verified browser and API continuity with a controlled model. The raw native browser path passed separately. The exact-relaunch integration enrolled a fixture admin to verify that stale self proof was refused and current self proof succeeded. These runs used local fixture credentials and isolated tmux servers. [Browser fixture](../../../../tests/integration/agents/dsh/web/test_fixture_web.py) · [Relaunch integration](../../../../tests/integration/agents/dsh/web/test_gateway_native.py)

## Checks

| Check | Result |
| --- | --- |
| Full Pixi unit suite | 5,123 passed, 14 skipped |
| Focused gateway, passive, CLI, login, plugin, mailbox, and registry tests | 166 passed |
| Gateway HTTPS and passive admission batch | 17 passed, including four HTTPS integration cases |
| DSH Web browser and exact-relaunch integrations | Three passed |
| Pixi lint and strict mypy | Passed |
| Strict MkDocs build | Passed |
| OpenSpec validation | Passed with one inherited requirement-length warning |
| Strict OpenSpec validation | Reports the same warning for the existing shared mailbox facade requirement |

Verification used the installed frozen Pixi environment after normal environment preparation stalled. An early unit run collected the previous Web test fixture while it was being updated. The final run used explicit signed proof in that fixture and passed.

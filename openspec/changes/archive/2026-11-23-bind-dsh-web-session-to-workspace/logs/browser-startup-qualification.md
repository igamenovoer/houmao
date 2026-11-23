# Browser Startup Qualification

## Native Builds and Fixtures

Qualified DSH `0.2.2-rc.1`, the managed Web floor, and `0.2.2-rc.5` with fresh Playwright Chromium `159.0.8154.6` contexts. The maintained `native_web_factory` and `controlled_messages_server` fixtures selected the local synthetic Messages case and its `controlled` model. The floor package came from the local Bun cache into an isolated scratch install. Each test used a separate native process group, a private home, and an ephemeral loopback listener. The direct native fixture does not use tmux. Browser descriptors and native credentials stayed in owner-private temporary directories outside the checkout.

The exploratory tests live in ignored `tmp/issue92-browser-qualification/test_browser_qualification.py`. Each run selected the resolved executable for its build through `HOUMAO_DSH_EXECUTABLE` and used `pixi run pytest -q -s -p tests.integration.agents.dsh.conftest -p tests.integration.agents.dsh.web.conftest` with the scratch test path and an owner-private `--basetemp`. The floor run passed 6 cases in 22.24 seconds. The newer-build run passed 6 cases in 26.88 seconds.

## Stock Startup and Managed Ordering

The fixture attached the exact managed session to the native Workspace before browser entry. It introduced no browser selection. With one historical turn already in that session, stock startup issued one `POST /api/session/create`, added one unrelated blank session to the Workspace, and selected that blank. Both builds did so whether the browser received the Workspace baseline or the Session catalog first.

The candidate used the DSH owner index injection and the typed browser socket factory. The owner index carried the fixture target and installed the factory before boot. The factory buffered only frames for the Workspace follow stream on a marked entry page. A `dsh.client` extension waited for the exact target to appear in the Session catalog, selected it through `uiWorkspace.openSession`, then released the buffered Workspace stream. DSH's stock restoration waits for both catalogs and checks for an existing main selection before it can initiate a create call. [Index injection](../../../../extern/orphan/deepseek-harness/packages/host/webserver/src/injections.ts) · [Socket factory](../../../../extern/orphan/deepseek-harness/packages/client/connection/src/client/index.ts) · [Client modules](../../../../extern/orphan/deepseek-harness/docs/subsystems/client-modules.md) · [Native startup](../../../../extern/orphan/deepseek-harness/packages/client/ui-workspace/src/client/navigation.ts)

| DSH | Counts | Session At Entry | Browser Catalog Order |
| --- | --- | --- | --- |
| `0.2.2-rc.1` | 2 stock controls, 4 managed cases | Blank and populated | Workspace first and Session first |
| `0.2.2-rc.5` | 2 stock controls, 4 managed cases | Blank and populated | Workspace first and Session first |

The managed runs delayed extension activation for 750 ms after both baselines reached the browser instrumentation. The Workspace model remained pending when the extension selected the exact native session. The recorded order was extension activation, exact selection, then Workspace release. Each managed entry issued zero `/api/session/create`, `/api/workspace/create`, and `/api/workspace/initializeDefault` calls. All eight managed cases preserved the full native Workspace and session inventory and displayed the exact native session without a test-side click.

Chromium retained the noncredential fragment across native token authentication and its `303` redirect to the clean root. The extension consumed the fragment and removed it from the URL. An ordinary reload then restored the same exact session without the managed startup gate. [Native cookie exchange](../../../../extern/orphan/deepseek-harness/packages/host/authentication-token/src/browser-auth.ts)

## Packaged Browser Assets

Loaded the product companion and browser addon through the maintained native fixture. On each build, four Chromium cases passed. Fresh blank and populated sessions opened exactly, kept the same native inventory, and survived an ordinary reload. A stale incarnation showed the managed-entry error and left the native inventory intact. Each entry issued zero session or Workspace mutation calls. The floor run took 12.00 seconds, and the newer-build run took 15.48 seconds.

For the reset case, Playwright held the browser's read-only native state request after authentication and index rendering. The fixture reset the Agent while the request waited. The prior conversation remained in the Workspace alongside the replacement. When the read resumed, the browser detected the new binding, showed the managed-entry error, and selected no session. The reset inventory remained unchanged after entry.

The scratch harness `tmp/issue92-browser-qualification/test_product_entry.py` exercised native token entry directly. A separate `node --test tmp/issue92-browser-qualification/gate-fault-cases.mjs` run passed six cases with controlled sockets. It checked untouched ordinary and off-origin connections, unrelated stream delivery, cancellation before selection, discarded frames from a closed socket, a replacement socket, stale markers, lost membership, frame overflow, and the 15-second timeout. The gate cancels a verified pending Workspace stream when refusing the entry and drops its late messages. The gateway's admission and credential flows use their own integration tests.

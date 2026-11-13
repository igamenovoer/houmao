# Independent Gateway Plugin Fixtures

These CI distributions are installed into the source-isolated qualification environment. They are excluded from Houmao's wheel and do not carry provider credentials.

`fixture-package` advertises independently selectable route-conflict, reserved-route, startup-failure, worker-failure, unsupported-SDK, import-failure, and unselected-import implementations. `duplicate-package` advertises one duplicate name. Discovery must reject that selected name before loading either implementation.

The installed `houmao-fixture-codex` executable emits deterministic headless protocol events. It needs an explicitly selected local control file, makes no network calls, and has no authentication fallback. It counts invocations to detect unintended replay; it does not save notification bodies.

Use the [qualification utility](../../../scripts/qualification/gateway-plugins/README.md) to build and install wheels, launch the actual gateway in both process modes, and clean up the synthetic sessions.

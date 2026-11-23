# Tasks

## 1. Dashboard Route and Summary

- [x] 1.1 Add the public `GET /` route and packaged HTML template to the gateway. Verify HTTP 200 HTML under open and keyed policy, escaped display values, and the browser cache and referrer headers.
- [x] 1.2 Read the agent name or ID, backend, and mode from the verified runtime binding. Verify the summary distinguishes gateway health from Web availability and renders unavailable evidence without writing runtime status or publishing private fields.
- [x] 1.3 Document the root response in the gateway protocol reference. Check that the route inventory and API admission tests still cover the existing health, endpoint, and private status behavior.

## 2. Native Web Entry

- [x] 2.1 Show the bare `/v1/web/enter` link only with a verified available Web surface, an eligible owner-local request, and available roster policy. Test busy Web agents, all non-Web modes, stale or unavailable native bindings, unavailable policy, and proxy requests.
- [x] 2.2 Exercise the link against the existing Web entry routes. Verify the empty-roster redirect and keyed sign-in, rechecks after the roster or binding changes, and the absence of tickets, credentials, and a native sign-in lookup during rendering.
- [x] 2.3 Update the gateway operator reference with a dashboard URL example, the two roster outcomes, and owner-local or forwarded access guidance. Verify the gateway reference links to the instructions.

## 3. Integration Verification

- [x] 3.1 Run the focused dashboard, admission, and Web entry suites through Pixi. Verify the page template is included in the packaged gateway.
- [x] 3.2 Exercise the dashboard-to-native-browser flow with the maintained managed-agent fixture on supported DSH and Kimi Web builds. Use an explicit case and model, an isolated tmux server, and a clean browser context. Record the outcomes and any unavailable fixture prerequisites.

# Design

## Context

The gateway declares an access class for each route before startup. Existing public routes report liveness and endpoint policy. The private status handler refreshes persisted runtime state. The implemented `open-gateway-with-empty-admin-roster` change already selects the redirect or sign-in outcome for the bare Web entry URL. Its spec delta records the contract this dashboard uses. [Gateway admission](../../../src/houmao/agents/realm_controller/gateway_admission.py) · [Web entry](../../../src/houmao/agents/realm_controller/gateway_web_entry.py)

## Goals / Non-Goals

**Goals**

- Let a browser identify the gateway's agent and distinguish gateway health from current Web availability.
- Use the existing owner-local entry path for the first dashboard action.

**Non-Goals**

- Prompting, interruption, refresh, relaunch, and stop are later dashboard increments.

## Decisions

### Serve the Page at the Gateway Root

Register `GET /` on the existing gateway app as a public operation. Direct rendering gives the base URL a useful response without an intermediate route. Package the HTML alongside the existing login resources and render escaped values server-side. Use the existing browser response protections for caching and referrers. [Gateway app](../../../src/houmao/agents/realm_controller/gateway_service.py) · [Packaged login renderer](../../../src/houmao/gateway/_web_login.py)

### Read Only the Fields the Page Displays

Build a small dashboard view from gateway liveness, the verified runtime manifest, and Web availability. Read the agent's name with its ID as a fallback, plus backend and run mode, from the current verified owner. Keep the runtime manifest and private status response inside the gateway. This projection avoids writing the status and current-instance records that the private status refresh produces. [Manifest fields](../../../src/houmao/agents/realm_controller/boundary_models.py) · [Status refresh](../../../src/houmao/agents/realm_controller/gateway_service.py)

For a Web agent, match the current owner binding to a bounded read-only native observation. Use its availability field for the link. Busy activity closes prompt admission independently of browser access. A missing, stale, or failed observation produces an unavailable summary and keeps the page readable. [Web observation](../../../src/houmao/agents/realm_controller/web_observation.py)

### Let the Existing Route Admit Browser Entry

Reuse the origin check and current roster availability to decide whether to display the fixed relative `/v1/web/enter` link. A proxied or advertised request receives guidance for reaching the owner-local listener or its private TCP forward. Page rendering performs only the checks needed to display the link. The entry handler resolves the native destination when the operator clicks, using the then-current policy and binding. [Entry origin and handler](../../../src/houmao/agents/realm_controller/gateway_web_entry.py)

## Risks / Trade-offs

- The native process or roster can change after the page renders. The existing entry handler verifies both again when the link is followed.
- Native observation can fail while the gateway still serves HTTP. Display those states independently and show a brief reason when entry is unavailable.
- A public page can disclose any field passed to its template. Limit the renderer to the declared summary fields and escape values before inserting them into HTML.

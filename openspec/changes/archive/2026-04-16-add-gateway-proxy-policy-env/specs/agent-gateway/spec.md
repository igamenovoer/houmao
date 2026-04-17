## ADDED Requirements

### Requirement: Live gateway HTTP clients bypass ambient proxies by default
The live gateway HTTP client SHALL connect directly to the resolved gateway listener by default and SHALL NOT use ambient proxy environment variables such as `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, or their lowercase variants for gateway requests.

This direct-by-default policy SHALL apply consistently to all requests made through the shared gateway client, including health, status, request submission, prompt control, TUI control, reminder, mail, mail-notifier, and memory calls.

The direct-by-default policy SHALL NOT require mutating process-wide `NO_PROXY` or `no_proxy` values.

When the gateway endpoint host is `0.0.0.0`, the client SHALL continue connecting through `127.0.0.1` while applying the same proxy policy.

#### Scenario: Gateway health bypasses proxy-contaminated environments by default
- **WHEN** a live gateway listener is reachable on `127.0.0.1:<port>`
- **AND WHEN** the caller environment defines `HTTP_PROXY`, `HTTPS_PROXY`, or `ALL_PROXY`
- **AND WHEN** the caller environment does not define loopback `NO_PROXY` or `no_proxy`
- **THEN** a gateway client health request reaches the live gateway listener directly
- **AND THEN** the request does not fail solely because the configured proxy cannot reach or forward the loopback listener

#### Scenario: Gateway proxy bypass is shared across gateway client calls
- **WHEN** a caller uses the shared gateway client for status, request submission, control, reminder, mail, notifier, or memory operations
- **AND WHEN** the caller environment contains ambient proxy variables
- **THEN** those gateway client requests use the same direct-by-default proxy policy as health checks
- **AND THEN** each operation's behavior is not dependent on process-wide `NO_PROXY` mutation

### Requirement: Gateway client proxy use requires an explicit environment opt-in
The live gateway HTTP client SHALL respect ambient proxy environment variables only when `HOUMAO_GATEWAY_RESPECT_PROXY_ENV=1` is present in the process environment at gateway client construction time.

When `HOUMAO_GATEWAY_RESPECT_PROXY_ENV` is absent or has any value other than `1`, the gateway client SHALL use direct-by-default behavior.

When proxy-respecting mode is enabled, the gateway client SHALL use the standard Python HTTP proxy handling for the caller environment, including any caller-provided `NO_PROXY` or `no_proxy` values.

The gateway client SHALL NOT persist this proxy policy decision in gateway manifests, gateway status, runtime session manifests, registry records, or durable gateway state.

#### Scenario: Explicit opt-in respects caller proxy settings
- **WHEN** the caller constructs a gateway client with `HOUMAO_GATEWAY_RESPECT_PROXY_ENV=1`
- **AND WHEN** the caller environment defines proxy variables
- **THEN** gateway client requests use normal environment proxy handling
- **AND THEN** caller-provided `NO_PROXY` or `no_proxy` values influence proxy bypass according to the standard HTTP client behavior

#### Scenario: Non-one values keep direct gateway behavior
- **WHEN** the caller constructs a gateway client with `HOUMAO_GATEWAY_RESPECT_PROXY_ENV` absent, empty, or set to a value other than `1`
- **THEN** gateway client requests bypass ambient proxy variables
- **AND THEN** the gateway client does not mutate `NO_PROXY` or `no_proxy`

### Requirement: Gateway attach readiness timeouts include the last health probe diagnostic
When gateway attach observes a published listener but health readiness does not succeed before the attach deadline, the attach error SHALL include the target listener host and port.

If at least one health probe failed with a gateway HTTP error before the deadline, the attach error SHALL also include the last observed health probe error detail.

The attach flow SHALL continue using the gateway health endpoint as the authoritative readiness signal; diagnostic files and last-probe details SHALL NOT replace successful health readiness.

#### Scenario: Timeout reports the last health probe error
- **WHEN** gateway attach starts a gateway instance and discovers its listener
- **AND WHEN** every health probe fails until the readiness deadline
- **THEN** the attach result reports that health readiness timed out for the listener host and port
- **AND THEN** the attach result includes the last health probe error detail

#### Scenario: Health success remains the readiness authority
- **WHEN** gateway attach starts a gateway instance and discovers its listener
- **AND WHEN** a health probe returns the expected gateway protocol version before the readiness deadline
- **THEN** gateway attach treats the gateway as ready
- **AND THEN** it does not require separate file-state diagnostics to prove readiness

## 1. Gateway Contracts

- [x] 1.1 Add gateway wakeup HTTP models and client methods for create, list, inspect, and cancel operations.
- [x] 1.2 Register the `/v1/wakeups` route family in the live gateway app with structured validation and explicit unknown-job errors.

## 2. In-Memory Wakeup Runtime

- [x] 2.1 Add an in-memory wakeup job registry and scheduler loop to the `GatewayService` startup and shutdown lifecycle.
- [x] 2.2 Implement one-off and repeating wakeup scheduling, anchored repeat cadence, and explicit cancellation semantics.
- [x] 2.3 Refactor prompt execution so due wakeups can share one execution helper with existing prompt paths without entering the durable queue before delivery.

## 3. Runtime Semantics And Observability

- [x] 3.1 Enforce low-priority wakeup delivery so due wakeups only run when admission is open, no execution is active, and durable public queue depth is zero.
- [x] 3.2 Expose live wakeup inspection state for scheduled, overdue, and executing jobs through the new gateway routes.
- [x] 3.3 Emit clear gateway log or event evidence for wakeup registration, deferral, execution, cancellation, and loss on restart without adding durable recovery artifacts.

## 4. Verification And Docs

- [x] 4.1 Add unit coverage for wakeup request validation, repeat rescheduling, busy deferral, cancellation, and the active-execution cancellation boundary.
- [x] 4.2 Add integration coverage for the live `/v1/wakeups` HTTP contract and the guarantee that wakeups do not expand the public `/v1/requests` request-kind set.
- [x] 4.3 Update gateway reference docs to describe the wakeup routes, in-memory lifetime, repeating behavior, and cancellation semantics.

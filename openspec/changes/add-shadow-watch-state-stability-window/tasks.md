## 1. Narrow Scope To Demo Consumption

- [ ] 1.1 Update the demo change artifacts to state explicitly that `houmao-server` owns the authoritative live tracking contract
- [ ] 1.2 Remove or supersede any task text that would define competing tracker semantics in the demo layer

## 2. Consume Server-Owned Tracker State

- [ ] 2.1 Update the demo monitor or follow-on demo tooling to read explicit transport/process/parse/operator/stability fields from `houmao-server`
- [ ] 2.2 Keep any optional smoothing or stability-window behavior presentation-only and derived from the server-owned contract

## 3. Demo Documentation

- [ ] 3.1 Document that demo-local visualization is a consumer of server-owned live tracking rather than the source of truth

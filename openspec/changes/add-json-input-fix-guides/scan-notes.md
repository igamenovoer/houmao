## JSON Input Surface Scan

### Covered in this change

| Surface | Input | Classification | Action |
|---|---|---|---|
| `houmao-mgr internals config-drafts generate --intent` | Inline JSON object, `-` for stdin, or JSON file path | Agent-facing internal authoring utility with compact selected-draft schema | Add draft-specific fix guide for invalid JSON, wrong top-level shape, non-object `fields`, unsupported fields, invalid field values, and missing required fields. |

### Deferred

| Surface | Input | Classification | Rationale |
|---|---|---|---|
| `houmao-mgr internals graph high analyze|packet-expectations|slice|render-mermaid --input` | Node-link JSON file or stdin | File/stdin-only graph internals | Existing docs already define the node-link shape. A useful fix guide would need graph-specific examples and is larger than the reported inline JSON failure. |
| `houmao-mgr internals graph high validate-packets --graph --packets` | Node-link graph JSON file and packet JSON file | File-only graph internals | Packet schemas are topology-sensitive and better handled by a follow-up graph helper diagnostic change. |
| `houmao-mgr internals graph low mutate --input --ops` | Node-link graph JSON file and mutation-ops JSON file | File-only graph internals | The ops shape is documented, but compact schema generation belongs with graph helper validation rather than config-draft diagnostics. |
| `houmao-mgr internals graph low relabel --input --mapping` | Node-link graph JSON file and mapping JSON file | File-only graph internals | Deferred with other graph helper JSON file inputs. |
| `houmao-mgr internals graph low subgraph --input --nodes` | Node-link graph JSON file and node-list JSON file | File-only graph internals | Deferred with other graph helper JSON file inputs. |
| `houmao-mgr internals graph low alg * --input` | Node-link graph JSON file or stdin | File/stdin-only graph internals | Deferred with other graph helper JSON file inputs. |
| Runtime artifact and mailbox support JSON parsing inside command modules | Internal stored state or encoded helper detail | Not direct user JSON option for this change | These paths parse stored artifacts or helper payloads, not the reported class of caller-supplied JSON command input. |

### Scope confirmation

The initial implementation covers all registered config-draft ids:

- `project.specialist`
- `project.profile`
- `internals.native-agent.launch-dossier`

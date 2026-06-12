## REMOVED Requirements

### Requirement: Workbench template renderer override is separate from payload renderer selection
**Reason**: Layer 1 template graphics now have one supported renderer, Plotly, and the workbench is retiring Recharts completely. The previous override requirement depended on multiple renderer choices and payload fallback behavior that no longer exists.

**Migration**: Render completed `houmao.graphic.template` tool calls through Plotly without a local renderer override. Raw diagnostics SHALL still preserve the original tool-call arguments, but the workbench SHALL NOT expose or honor `vega-lite` or `recharts` template renderer overrides.

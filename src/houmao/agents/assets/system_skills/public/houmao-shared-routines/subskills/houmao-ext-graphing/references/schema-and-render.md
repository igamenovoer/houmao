# Schema Discovery, Validation, Rendering, and Examples

## CLI Discovery, Validation, and Rendering

Reuse one resolved `houmao-mgr` launcher across the turn:

```bash
# 1. Discover built-in graphing schemas and supported 2D Plotly trace types
houmao-mgr ag-ui impl templated-graphics list
houmao-mgr ag-ui impl freeform-graphics list
houmao-mgr ag-ui impl schema houmao.graphic.template
houmao-mgr ag-ui impl schema houmao.graphic.vegalite
houmao-mgr ag-ui impl catalog houmao.graphic.template traces

# 2. Validate implementation payload JSON
houmao-mgr ag-ui impl validate houmao.graphic.template --input payload.json
houmao-mgr ag-ui impl validate houmao.graphic.vegalite --input payload.json

# 3. Render standard AG-UI events (--format json|jsonl|sse; default json) and validate
houmao-mgr ag-ui impl render houmao.graphic.template --input payload.json --format json > events.json
houmao-mgr ag-ui impl render houmao.graphic.vegalite --input payload.json --format json > events.json
houmao-mgr ag-ui protocol events validate --input events.json
houmao-mgr ag-ui protocol events frame --input events.json --format sse
```

## Layer 1 Example (`houmao.graphic.template` v3)

```json
{
  "schemaVersion": 3,
  "figureType": "plotly2d",
  "renderer": { "preferred": "plotly" },
  "title": "Build Results",
  "traces": [
    {
      "type": "bar",
      "name": "Jobs",
      "data": { "x": ["passed", "failed"], "y": [42, 2] },
      "style": {
        "marker": { "color": ["#1f7a4d", "#c2410c"] },
        "hovertemplate": "%{x}: %{y}<extra></extra>"
      }
    }
  ],
  "layout": {
    "xaxis": { "title": "Status" },
    "yaxis": { "title": "Count" },
    "bargap": 0.28
  },
  "extra": {
    "plotly": { "layout": { "margin": { "l": 48, "r": 16, "t": 48, "b": 44 } } }
  }
}
```

## Layer 2 Example (`houmao.graphic.vegalite` v1)

```json
{
  "schemaVersion": 1,
  "library": "vega-lite",
  "specVersion": "6",
  "title": "Queue Status",
  "spec": {
    "$schema": "https://vega.github.io/schema/vega-lite/v6.4.1.json",
    "data": {
      "values": [
        { "status": "ready", "count": 58 },
        { "status": "queued", "count": 23 }
      ]
    },
    "mark": "bar",
    "encoding": {
      "x": { "field": "status", "type": "nominal" },
      "y": { "field": "count", "type": "quantitative" }
    }
  },
  "display": { "height": 360, "caption": "Current queue status." }
}
```

Optional local Python Altair helper to produce `spec` JSON (never send the Python code itself):

```python
import altair as alt

chart = alt.Chart(
    alt.Data(values=[{"status": "ready", "count": 58}, {"status": "queued", "count": 23}])
).mark_bar().encode(x="status:N", y="count:Q")
spec = chart.to_dict()
```

## Common Repair Map

| Symptom | Repair |
| --- | --- |
| Unknown schema name | Run `ag-ui impl templated-graphics list` or `freeform-graphics list`; never use a Plotly trace name (`bar`, `heatmap`) as the schema ID. |
| Rejected Plotly trace | Inspect `ag-ui impl catalog houmao.graphic.template traces` and pick an allowed 2D trace (3D scene traces are excluded). |
| Legacy `chartType` or `houmao.chart.*` | Rewrite as `houmao.graphic.template` with `schemaVersion: 3`, `figureType: "plotly2d"`, and `traces[].type`. |
| Vega-Lite inside `template.extra` | Move the Vega-Lite grammar to a `houmao.graphic.vegalite` (`schemaVersion: 1`) payload. |

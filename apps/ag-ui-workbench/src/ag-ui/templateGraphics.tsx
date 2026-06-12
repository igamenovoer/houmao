import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import PlotlyBundle from "plotly.js-cartesian-dist-min";

export interface TemplateRendererContext {
  paneId: string;
  toolCallId: string;
}

type ChartType = "bar" | "line" | "scatter" | "pie" | "histogram";
type TraceType = "bar" | "scatter" | "pie" | "histogram";
type ValidationResult<T> = { ok: true; value: T } | { ok: false; error: string };
type PlainObject = Record<string, unknown>;
type TraceArray = Array<string | number | boolean | null>;
type PlotlyTrace = PlainObject;
type PlotlyLayout = PlainObject;
type PlotlyConfig = PlainObject;

interface PlotlyApi {
  react: (
    element: HTMLElement,
    data: PlotlyTrace[],
    layout: PlotlyLayout,
    config: PlotlyConfig,
  ) => Promise<unknown>;
  purge: (element: HTMLElement) => void;
}

interface RendererSelection {
  preferred: "plotly";
}

interface DataRef {
  id: string;
}

interface ColumnBinding {
  column: string;
}

interface MarkerSource {
  color?: ColumnBinding;
  size?: ColumnBinding;
}

interface TraceSource {
  dataRef: string;
  x?: ColumnBinding;
  y?: ColumnBinding;
  z?: ColumnBinding;
  labels?: ColumnBinding;
  values?: ColumnBinding;
  text?: ColumnBinding;
  marker?: MarkerSource;
}

interface TemplateTrace {
  type?: TraceType;
  name?: string;
  x?: TraceArray;
  y?: TraceArray;
  z?: TraceArray;
  labels?: TraceArray;
  values?: number[];
  text?: string | TraceArray;
  hovertemplate?: string;
  mode?: string;
  orientation?: "v" | "h";
  marker?: PlainObject;
  line?: PlainObject;
  source?: TraceSource;
  opacity?: number;
  showLegend?: boolean;
}

interface TemplatePayload {
  schemaVersion: 2;
  chartType: ChartType;
  renderer: RendererSelection;
  title: string;
  subtitle?: string;
  traces: TemplateTrace[];
  dataRefs?: DataRef[];
  layout?: PlainObject;
  config: PlainObject;
  display?: PlainObject;
  extra?: { plotly?: PlainObject };
}

interface CompiledFigure {
  data: PlotlyTrace[];
  layout: PlotlyLayout;
  config: PlotlyConfig;
}

const Plotly = PlotlyBundle as PlotlyApi;
const CHART_TYPES: readonly ChartType[] = ["bar", "line", "scatter", "pie", "histogram"];
const TRACE_TYPES_BY_CHART: Record<ChartType, readonly TraceType[]> = {
  bar: ["bar"],
  line: ["scatter"],
  scatter: ["scatter"],
  pie: ["pie"],
  histogram: ["histogram"],
};
const REMOTE_URL_PATTERN = /^https?:\/\//i;
const UNSAFE_TEXT_PATTERNS = [/<\s*script\b/i, /\son[a-z0-9_-]+\s*=/i, /javascript\s*:/i, /<\s*iframe\b/i, /<\s*svg\b/i];
const PLOTLY_EXTRA_DISALLOWED_KEYS = new Set([
  "$schema",
  "data",
  "datasets",
  "encoding",
  "figure",
  "frames",
  "html",
  "iframe",
  "javascript",
  "layer",
  "params",
  "script",
  "signals",
  "spec",
  "svg",
  "template",
  "templates",
  "transform",
  "transforms",
  "traces",
  "vega",
  "vegaLite",
]);

export function renderTemplateGraphic(payload: unknown, context: TemplateRendererContext): ReactNode {
  const validated = validateTemplatePayload(payload);
  if (!validated.ok) {
    return (
      <TemplateFallback
        paneId={context.paneId}
        title="houmao.graphic.template"
        detail={validated.error}
        raw={safeJson(payload)}
      />
    );
  }
  const datasourceDiagnostic = datasourceBindingDiagnostic(validated.value);
  if (datasourceDiagnostic) {
    return (
      <TemplateFallback
        paneId={context.paneId}
        title={validated.value.title}
        detail={datasourceDiagnostic}
        raw={safeJson(payload)}
      />
    );
  }
  const compiled = compileTemplatePayload(validated.value);
  if (!compiled.ok) {
    return (
      <TemplateFallback
        paneId={context.paneId}
        title={validated.value.title}
        detail={compiled.error}
        raw={safeJson(payload)}
      />
    );
  }
  return (
    <TemplateFrame paneId={context.paneId} title={validated.value.title} subtitle={validated.value.subtitle}>
      <PlotlyTemplateView paneId={context.paneId} figure={compiled.value} />
    </TemplateFrame>
  );
}

function PlotlyTemplateView({ paneId, figure }: { paneId: string; figure: CompiledFigure }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [error, setError] = useState<string | null>(null);
  const figureKey = useMemo(() => JSON.stringify(figure), [figure]);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) {
      return undefined;
    }
    let cancelled = false;
    setError(null);
    void Plotly.react(element, figure.data, figure.layout, figure.config).catch((err: unknown) => {
      if (!cancelled) {
        setError(err instanceof Error ? err.message : "Plotly render failed.");
      }
    });
    return () => {
      cancelled = true;
      Plotly.purge(element);
    };
  }, [figureKey, figure]);

  if (error) {
    return (
      <div className="component-fallback" data-testid={`invalid-component-${paneId}`}>
        <p>{error}</p>
      </div>
    );
  }
  return (
    <div
      ref={containerRef}
      className="component-chart template-plotly-chart"
      data-testid={`template-chart-plotly-${paneId}`}
    />
  );
}

function compileTemplatePayload(payload: TemplatePayload): ValidationResult<CompiledFigure> {
  const data: PlotlyTrace[] = [];
  for (const [index, trace] of payload.traces.entries()) {
    const compiled = compileTrace(trace, payload.chartType, index);
    if (!compiled.ok) {
      return compiled;
    }
    data.push(compiled.value);
  }
  return {
    ok: true,
    value: {
      data,
      layout: compileLayout(payload),
      config: compileConfig(payload),
    },
  };
}

function compileTrace(
  trace: TemplateTrace,
  chartType: ChartType,
  index: number,
): ValidationResult<PlotlyTrace> {
  const expectedType = TRACE_TYPES_BY_CHART[chartType][0];
  const compiled: PlotlyTrace = {
    type: chartType === "line" ? "scatter" : expectedType,
    name: trace.name ?? `${chartType} ${index + 1}`,
  };
  copyArray(compiled, trace, "x");
  copyArray(compiled, trace, "y");
  copyArray(compiled, trace, "labels");
  copyNumberArray(compiled, trace, "values");
  copyString(compiled, trace, "hovertemplate");
  copyStringOrArray(compiled, trace, "text");
  copyNumber(compiled, trace, "opacity");
  copyString(compiled, trace, "orientation");
  if (typeof trace.showLegend === "boolean") {
    compiled.showlegend = trace.showLegend;
  }
  const marker = compileMarker(trace.marker);
  if (!marker.ok) {
    return invalid(`traces.${index}.${marker.error}`);
  }
  if (marker.value) {
    compiled.marker = marker.value;
  }
  const line = compileLine(trace.line);
  if (!line.ok) {
    return invalid(`traces.${index}.${line.error}`);
  }
  if (line.value) {
    compiled.line = line.value;
  }
  if (chartType === "line") {
    compiled.mode = trace.mode ?? "lines";
  } else if (chartType === "scatter") {
    compiled.mode = trace.mode ?? "markers";
  } else if (trace.mode) {
    return invalid(`traces.${index}.mode is only supported for line and scatter charts.`);
  }
  return { ok: true, value: compiled };
}

function compileLayout(payload: TemplatePayload): PlotlyLayout {
  const layout = isRecord(payload.layout) ? payload.layout : {};
  const extraPlotly = isRecord(payload.extra?.plotly) ? payload.extra.plotly : {};
  const extraLayout = isRecord(extraPlotly.layout) ? extraPlotly.layout : {};
  return stripUndefined({
    autosize: true,
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { color: "#f3efe5" },
    margin: mergeObjects({ l: 48, r: 18, t: 16, b: 44, pad: 0 }, readObject(layout.margin), readObject(extraLayout.margin)),
    xaxis: compileAxis(readObject(layout.xaxis), readObject(extraLayout.xaxis)),
    yaxis: compileAxis(readObject(layout.yaxis), readObject(extraLayout.yaxis)),
    legend: mergeObjects(readObject(layout.legend), readObject(extraLayout.legend)),
    showlegend: booleanValue(layout.showLegend ?? extraLayout.showLegend),
    hovermode: stringValue(layout.hovermode ?? extraLayout.hovermode),
    bargap: numberValue(layout.bargap ?? extraLayout.bargap),
    barmode: stringValue(layout.barmode ?? extraLayout.barmode),
  });
}

function compileAxis(primary: PlainObject, extra: PlainObject): PlainObject {
  return stripUndefined({
    title: stringValue(primary.title ?? extra.title),
    tickformat: stringValue(primary.tickformat ?? extra.tickformat),
    type: stringValue(primary.type ?? extra.type),
    range: numberArrayValue(primary.range ?? extra.range),
    gridcolor: "rgba(148, 163, 184, 0.26)",
    zerolinecolor: "rgba(148, 163, 184, 0.35)",
  });
}

function compileConfig(payload: TemplatePayload): PlotlyConfig {
  const extraPlotly = isRecord(payload.extra?.plotly) ? payload.extra.plotly : {};
  const extraConfig = isRecord(extraPlotly.config) ? extraPlotly.config : {};
  return stripUndefined({
    responsive: booleanValue(payload.config.responsive ?? extraConfig.responsive) ?? true,
    displayModeBar: payload.config.displayModeBar ?? extraConfig.displayModeBar ?? false,
    scrollZoom: booleanValue(payload.config.scrollZoom ?? extraConfig.scrollZoom),
    staticPlot: booleanValue(payload.config.staticPlot ?? extraConfig.staticPlot),
  });
}

function validateTemplatePayload(payload: unknown): ValidationResult<TemplatePayload> {
  if (!isRecord(payload)) {
    return invalid("payload must be an object.");
  }
  const unsafe = rejectUnsafeText(payload, "$");
  if (!unsafe.ok) {
    return unsafe;
  }
  const remote = rejectRemoteUrls(payload, "$");
  if (!remote.ok) {
    return remote;
  }
  if (payload.schemaVersion !== 2) {
    return invalid("schemaVersion must be 2 for Plotly template graphics.");
  }
  if ("data" in payload || "encoding" in payload) {
    return invalid("Legacy data.values plus encoding payloads are retired; use traces.");
  }
  const chartType = enumValue(payload.chartType, CHART_TYPES, "chartType");
  if (!chartType.ok) {
    return chartType;
  }
  const renderer = validateRenderer(payload.renderer);
  if (!renderer.ok) {
    return renderer;
  }
  const title = nonBlankString(payload.title, "title");
  if (!title.ok) {
    return title;
  }
  const traces = validateTraces(payload.traces, chartType.value);
  if (!traces.ok) {
    return traces;
  }
  const dataRefs = validateDataRefs(payload.dataRefs);
  if (!dataRefs.ok) {
    return dataRefs;
  }
  const sourceRefs = validateSourceRefs(traces.value, dataRefs.value);
  if (!sourceRefs.ok) {
    return sourceRefs;
  }
  const extra = validateExtra(payload.extra);
  if (!extra.ok) {
    return extra;
  }
  return {
    ok: true,
    value: {
      schemaVersion: 2,
      chartType: chartType.value,
      renderer: renderer.value,
      title: title.value,
      subtitle: optionalString(payload.subtitle),
      traces: traces.value,
      dataRefs: dataRefs.value.length > 0 ? dataRefs.value : undefined,
      layout: recordOrUndefined(payload.layout),
      config: recordOrUndefined(payload.config) ?? { responsive: true },
      display: recordOrUndefined(payload.display),
      extra: extra.value,
    },
  };
}

function validateRenderer(value: unknown): ValidationResult<RendererSelection> {
  if (typeof value === "undefined" || value === null) {
    return { ok: true, value: { preferred: "plotly" } };
  }
  if (!isRecord(value)) {
    return invalid("renderer must be an object.");
  }
  if ("fallback" in value) {
    return invalid("renderer.fallback is retired; Plotly is the only Layer 1 renderer.");
  }
  if (typeof value.preferred !== "undefined" && value.preferred !== "plotly") {
    return invalid("renderer.preferred must be plotly.");
  }
  return { ok: true, value: { preferred: "plotly" } };
}

function validateTraces(value: unknown, chartType: ChartType): ValidationResult<TemplateTrace[]> {
  if (!Array.isArray(value) || value.length === 0) {
    return invalid("traces must be a non-empty array.");
  }
  const traces: TemplateTrace[] = [];
  for (const [index, item] of value.entries()) {
    const trace = validateTrace(item, chartType, index);
    if (!trace.ok) {
      return trace;
    }
    traces.push(trace.value);
  }
  return { ok: true, value: traces };
}

function validateTrace(
  value: unknown,
  chartType: ChartType,
  index: number,
): ValidationResult<TemplateTrace> {
  if (!isRecord(value)) {
    return invalid(`traces.${index} must be an object.`);
  }
  const traceType = optionalEnum(value.type, TRACE_TYPES_BY_CHART[chartType], `traces.${index}.type`);
  if (!traceType.ok) {
    return traceType;
  }
  const source = validateSource(value.source, `traces.${index}.source`);
  if (!source.ok) {
    return source;
  }
  const trace: TemplateTrace = {
    type: traceType.value,
    name: optionalString(value.name),
    x: arrayValue(value.x),
    y: arrayValue(value.y),
    z: arrayValue(value.z),
    labels: arrayValue(value.labels),
    values: numberArrayValue(value.values),
    text: stringOrArrayValue(value.text),
    hovertemplate: optionalString(value.hovertemplate),
    mode: optionalString(value.mode),
    orientation: orientationValue(value.orientation),
    marker: recordOrUndefined(value.marker),
    line: recordOrUndefined(value.line),
    source: source.value,
    opacity: numberValue(value.opacity),
    showLegend: booleanValue(value.showLegend),
  };
  const channelValidation = validateTraceChannels(trace, chartType, index);
  if (!channelValidation.ok) {
    return channelValidation;
  }
  return { ok: true, value: trace };
}

function validateTraceChannels(
  trace: TemplateTrace,
  chartType: ChartType,
  index: number,
): ValidationResult<void> {
  for (const channel of ["x", "y", "z", "labels", "values", "text"] as const) {
    if (trace.source?.[channel] && typeof trace[channel] !== "undefined") {
      return invalid(`traces.${index}.${channel} cannot be combined with source.${channel}.`);
    }
  }
  if (trace.source?.marker?.color && trace.marker && "color" in trace.marker) {
    return invalid(`traces.${index}.marker.color cannot be combined with source.marker.color.`);
  }
  if (trace.source?.marker?.size && trace.marker && "size" in trace.marker) {
    return invalid(`traces.${index}.marker.size cannot be combined with source.marker.size.`);
  }
  if (chartType === "pie") {
    return requireChannels(trace, index, ["labels", "values"]);
  }
  if (chartType === "histogram") {
    return hasChannel(trace, "x") || hasChannel(trace, "y")
      ? { ok: true, value: undefined }
      : invalid(`traces.${index} for histogram charts requires x or y.`);
  }
  const required = requireChannels(trace, index, ["x", "y"]);
  if (!required.ok) {
    return required;
  }
  return validateEqualLengths(trace, index, "x", "y");
}

function requireChannels(
  trace: TemplateTrace,
  index: number,
  channels: Array<"x" | "y" | "labels" | "values">,
): ValidationResult<void> {
  for (const channel of channels) {
    if (!hasChannel(trace, channel)) {
      return invalid(`traces.${index} requires ${channel}.`);
    }
  }
  return { ok: true, value: undefined };
}

function validateEqualLengths(
  trace: TemplateTrace,
  index: number,
  first: "x" | "labels",
  second: "y" | "values",
): ValidationResult<void> {
  const firstValue = trace[first];
  const secondValue = trace[second];
  if (Array.isArray(firstValue) && Array.isArray(secondValue) && firstValue.length !== secondValue.length) {
    return invalid(`traces.${index}.${first} and traces.${index}.${second} must have equal lengths.`);
  }
  return { ok: true, value: undefined };
}

function hasChannel(trace: TemplateTrace, channel: "x" | "y" | "labels" | "values"): boolean {
  return typeof trace[channel] !== "undefined" || typeof trace.source?.[channel] !== "undefined";
}

function validateDataRefs(value: unknown): ValidationResult<DataRef[]> {
  if (typeof value === "undefined") {
    return { ok: true, value: [] };
  }
  if (!Array.isArray(value)) {
    return invalid("dataRefs must be an array.");
  }
  const refs: DataRef[] = [];
  const seen = new Set<string>();
  for (const [index, item] of value.entries()) {
    if (!isRecord(item)) {
      return invalid(`dataRefs.${index} must be an object.`);
    }
    const id = nonBlankString(item.id, `dataRefs.${index}.id`);
    if (!id.ok) {
      return id;
    }
    if (seen.has(id.value)) {
      return invalid(`dataRefs.${index}.id duplicates ${id.value}.`);
    }
    seen.add(id.value);
    refs.push({ id: id.value });
  }
  return { ok: true, value: refs };
}

function validateSourceRefs(traces: TemplateTrace[], dataRefs: DataRef[]): ValidationResult<void> {
  const ids = new Set(dataRefs.map((item) => item.id));
  for (const [index, trace] of traces.entries()) {
    if (!trace.source) {
      continue;
    }
    if (!ids.has(trace.source.dataRef)) {
      return invalid(`traces.${index}.source.dataRef is not declared in dataRefs.`);
    }
  }
  return { ok: true, value: undefined };
}

function validateSource(value: unknown, path: string): ValidationResult<TraceSource | undefined> {
  if (typeof value === "undefined" || value === null) {
    return { ok: true, value: undefined };
  }
  if (!isRecord(value)) {
    return invalid(`${path} must be an object.`);
  }
  const dataRef = nonBlankString(value.dataRef, `${path}.dataRef`);
  if (!dataRef.ok) {
    return dataRef;
  }
  const marker = validateMarkerSource(value.marker, `${path}.marker`);
  if (!marker.ok) {
    return marker;
  }
  return {
    ok: true,
    value: {
      dataRef: dataRef.value,
      x: columnBinding(value.x, `${path}.x`),
      y: columnBinding(value.y, `${path}.y`),
      z: columnBinding(value.z, `${path}.z`),
      labels: columnBinding(value.labels, `${path}.labels`),
      values: columnBinding(value.values, `${path}.values`),
      text: columnBinding(value.text, `${path}.text`),
      marker: marker.value,
    },
  };
}

function validateMarkerSource(value: unknown, path: string): ValidationResult<MarkerSource | undefined> {
  if (typeof value === "undefined" || value === null) {
    return { ok: true, value: undefined };
  }
  if (!isRecord(value)) {
    return invalid(`${path} must be an object.`);
  }
  return {
    ok: true,
    value: {
      color: columnBinding(value.color, `${path}.color`),
      size: columnBinding(value.size, `${path}.size`),
    },
  };
}

function columnBinding(value: unknown, path: string): ColumnBinding | undefined {
  if (!isRecord(value)) {
    return undefined;
  }
  const column = typeof value.column === "string" ? value.column.trim() : "";
  return column ? { column } : undefined;
}

function validateExtra(value: unknown): ValidationResult<TemplatePayload["extra"]> {
  if (typeof value === "undefined") {
    return { ok: true, value: undefined };
  }
  if (!isRecord(value)) {
    return invalid("extra must be an object.");
  }
  for (const key of Object.keys(value)) {
    if (key !== "plotly") {
      return invalid(`extra.${key} is not supported. Only extra.plotly is allowed.`);
    }
  }
  const plotly = value.plotly;
  if (typeof plotly === "undefined") {
    return { ok: true, value: undefined };
  }
  if (!isRecord(plotly)) {
    return invalid("extra.plotly must be an object.");
  }
  const extraKeys = rejectDisallowedPlotlyExtra(plotly, "extra.plotly");
  if (!extraKeys.ok) {
    return extraKeys;
  }
  return { ok: true, value: { plotly } };
}

function datasourceBindingDiagnostic(payload: TemplatePayload): string | null {
  if (!payload.traces.some((trace) => trace.source)) {
    return null;
  }
  return "Datasource materialization is not supported yet. Inline trace arrays are required for rendering in this workbench.";
}

function compileMarker(value: PlainObject | undefined): ValidationResult<PlainObject | undefined> {
  if (!value) {
    return { ok: true, value: undefined };
  }
  return {
    ok: true,
    value: stripUndefined({
      color: value.color,
      colors: value.colors,
      size: value.size,
      opacity: numberValue(value.opacity),
      line: readObject(value.line),
    }),
  };
}

function compileLine(value: PlainObject | undefined): ValidationResult<PlainObject | undefined> {
  if (!value) {
    return { ok: true, value: undefined };
  }
  return {
    ok: true,
    value: stripUndefined({
      color: stringValue(value.color),
      width: numberValue(value.width),
      dash: stringValue(value.dash),
      shape: stringValue(value.shape),
    }),
  };
}

function copyArray(target: PlainObject, source: TemplateTrace, key: "x" | "y" | "labels"): void {
  const value = source[key];
  if (Array.isArray(value)) {
    target[key] = value;
  }
}

function copyNumberArray(target: PlainObject, source: TemplateTrace, key: "values"): void {
  const value = source[key];
  if (Array.isArray(value)) {
    target[key] = value;
  }
}

function copyString(target: PlainObject, source: TemplateTrace, key: "hovertemplate" | "orientation"): void {
  const value = source[key];
  if (typeof value === "string") {
    target[key] = value;
  }
}

function copyStringOrArray(target: PlainObject, source: TemplateTrace, key: "text"): void {
  const value = source[key];
  if (typeof value === "string" || Array.isArray(value)) {
    target[key] = value;
  }
}

function copyNumber(target: PlainObject, source: TemplateTrace, key: "opacity"): void {
  const value = source[key];
  if (typeof value === "number" && Number.isFinite(value)) {
    target[key] = value;
  }
}

function TemplateFrame({
  paneId,
  title,
  subtitle,
  children,
}: {
  paneId: string;
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <section className="component-frame" data-testid={`component-${paneId}`}>
      <header>
        <strong>{title}</strong>
        {subtitle ? <span>{subtitle}</span> : null}
      </header>
      {children}
    </section>
  );
}

function TemplateFallback({
  paneId,
  title,
  detail,
  raw,
}: {
  paneId: string;
  title: string;
  detail: string;
  raw: string;
}) {
  return (
    <details className="component-fallback" data-testid={`invalid-component-${paneId}`} open>
      <summary>Invalid component: {title}</summary>
      <p>{detail}</p>
      <pre>{raw}</pre>
    </details>
  );
}

function rejectDisallowedPlotlyExtra(value: unknown, path: string): ValidationResult<void> {
  if (Array.isArray(value)) {
    for (const [index, item] of value.entries()) {
      const result = rejectDisallowedPlotlyExtra(item, `${path}.${index}`);
      if (!result.ok) {
        return result;
      }
    }
    return { ok: true, value: undefined };
  }
  if (!isRecord(value)) {
    return { ok: true, value: undefined };
  }
  for (const [key, item] of Object.entries(value)) {
    const nextPath = `${path}.${key}`;
    if (PLOTLY_EXTRA_DISALLOWED_KEYS.has(key)) {
      return invalid(`${nextPath} is not allowed in Layer 1 Plotly extra.`);
    }
    const result = rejectDisallowedPlotlyExtra(item, nextPath);
    if (!result.ok) {
      return result;
    }
  }
  return { ok: true, value: undefined };
}

function rejectUnsafeText(value: unknown, path: string): ValidationResult<void> {
  if (typeof value === "string") {
    return UNSAFE_TEXT_PATTERNS.some((pattern) => pattern.test(value))
      ? invalid(`${path} contains unsafe inline content.`)
      : { ok: true, value: undefined };
  }
  if (Array.isArray(value)) {
    for (const [index, item] of value.entries()) {
      const result = rejectUnsafeText(item, `${path}.${index}`);
      if (!result.ok) {
        return result;
      }
    }
    return { ok: true, value: undefined };
  }
  if (!isRecord(value)) {
    return { ok: true, value: undefined };
  }
  for (const [key, item] of Object.entries(value)) {
    const result = rejectUnsafeText(item, `${path}.${key}`);
    if (!result.ok) {
      return result;
    }
  }
  return { ok: true, value: undefined };
}

function rejectRemoteUrls(value: unknown, path: string): ValidationResult<void> {
  if (typeof value === "string") {
    return REMOTE_URL_PATTERN.test(value)
      ? invalid(`${path} must not contain remote URLs.`)
      : { ok: true, value: undefined };
  }
  if (Array.isArray(value)) {
    for (const [index, item] of value.entries()) {
      const result = rejectRemoteUrls(item, `${path}.${index}`);
      if (!result.ok) {
        return result;
      }
    }
    return { ok: true, value: undefined };
  }
  if (!isRecord(value)) {
    return { ok: true, value: undefined };
  }
  for (const [key, item] of Object.entries(value)) {
    const result = rejectRemoteUrls(item, `${path}.${key}`);
    if (!result.ok) {
      return result;
    }
  }
  return { ok: true, value: undefined };
}

function enumValue<T extends string>(
  value: unknown,
  values: readonly T[],
  label: string,
): ValidationResult<T> {
  if (typeof value !== "string" || !values.includes(value as T)) {
    return invalid(`${label} must be one of ${values.join(", ")}.`);
  }
  return { ok: true, value: value as T };
}

function optionalEnum<T extends string>(
  value: unknown,
  values: readonly T[],
  label: string,
): ValidationResult<T | undefined> {
  if (typeof value === "undefined") {
    return { ok: true, value: undefined };
  }
  return enumValue(value, values, label);
}

function nonBlankString(value: unknown, field: string): ValidationResult<string> {
  if (typeof value !== "string" || value.trim() === "") {
    return invalid(`${field} must be a non-empty string.`);
  }
  return { ok: true, value: value.trim() };
}

function optionalString(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

function stringValue(value: unknown): string | undefined {
  return typeof value === "string" ? value : undefined;
}

function numberValue(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function booleanValue(value: unknown): boolean | undefined {
  return typeof value === "boolean" ? value : undefined;
}

function arrayValue(value: unknown): TraceArray | undefined {
  if (!Array.isArray(value) || value.length === 0) {
    return undefined;
  }
  return value.filter((item): item is string | number | boolean | null => isTraceScalar(item));
}

function numberArrayValue(value: unknown): number[] | undefined {
  if (!Array.isArray(value) || value.length === 0) {
    return undefined;
  }
  const numbers = value.filter((item): item is number => typeof item === "number" && Number.isFinite(item));
  return numbers.length === value.length ? numbers : undefined;
}

function stringOrArrayValue(value: unknown): string | TraceArray | undefined {
  if (typeof value === "string") {
    return value;
  }
  return arrayValue(value);
}

function orientationValue(value: unknown): "v" | "h" | undefined {
  return value === "v" || value === "h" ? value : undefined;
}

function isTraceScalar(value: unknown): value is string | number | boolean | null {
  return value === null || ["string", "number", "boolean"].includes(typeof value);
}

function recordOrUndefined(value: unknown): PlainObject | undefined {
  return isRecord(value) ? value : undefined;
}

function readObject(value: unknown): PlainObject {
  return isRecord(value) ? value : {};
}

function mergeObjects(...objects: PlainObject[]): PlainObject {
  return objects.reduce<PlainObject>((merged, item) => ({ ...merged, ...item }), {});
}

function stripUndefined(value: PlainObject): PlainObject {
  return Object.fromEntries(Object.entries(value).filter(([, item]) => typeof item !== "undefined"));
}

function invalid(error: string): ValidationResult<never> {
  return { ok: false, error };
}

function isRecord(value: unknown): value is PlainObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function safeJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

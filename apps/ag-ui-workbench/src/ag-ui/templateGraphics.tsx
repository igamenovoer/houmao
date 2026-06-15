import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import PlotlyBundle from "plotly.js-dist-min";

import {
  PLOTLY_2D_TRACE_CATALOG,
  PLOTLY_2D_TRACE_TYPES,
  PLOTLY_EXCLUDED_TRACE_TYPES,
  PLOTLY_TRACE_CATALOG_POLICY,
  type PlotlyTraceCatalogEntry,
} from "./plotlyTraceCatalog";

export interface TemplateRendererContext {
  paneId: string;
  toolCallId: string;
}

type TraceType = (typeof PLOTLY_2D_TRACE_TYPES)[number];
type ValidationResult<T> = { ok: true; value: T } | { ok: false; error: string };
type PlainObject = Record<string, unknown>;
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

interface TraceSource {
  dataRef: string;
  bindings: Record<string, ColumnBinding>;
}

interface TemplateTrace {
  type: TraceType;
  name?: string;
  data: PlainObject;
  style: PlainObject;
  source?: TraceSource;
}

interface TemplatePayload {
  schemaVersion: 3;
  figureType: "plotly2d";
  renderer: RendererSelection;
  title: string;
  subtitle?: string;
  traces: TemplateTrace[];
  dataRefs?: DataRef[];
  layout?: PlainObject;
  config: PlainObject;
  display?: PlainObject;
  extra?: { plotly?: PlotlyExtra };
}

interface PlotlyExtra {
  layout?: PlainObject;
  config?: PlainObject;
  style?: PlainObject;
  display?: PlainObject;
}

interface CompiledFigure {
  data: PlotlyTrace[];
  layout: PlotlyLayout;
  config: PlotlyConfig;
  height?: number;
}

const Plotly = PlotlyBundle as PlotlyApi;
const SUPPORTED_TRACE_TYPES = new Set<string>(PLOTLY_2D_TRACE_TYPES);
const REGISTERED_TRACE_TYPES = new Set<string>(PLOTLY_2D_TRACE_TYPES);
const EXCLUDED_TRACE_TYPES: Record<string, string> = PLOTLY_EXCLUDED_TRACE_TYPES;
const REMOTE_URL_PATTERN = /^https?:\/\//i;
const UNSAFE_TEXT_PATTERNS = [
  /<\s*script\b/i,
  /\son[a-z0-9_-]+\s*=/i,
  /javascript\s*:/i,
  /<\s*iframe\b/i,
  /<\s*svg\b/i,
  /image\/svg\+xml/i,
];
const SECRET_FIELD_PATTERN = /(token|key|secret|password|credential|authorization|cookie)/i;
const PLOTLY_POLICY_REJECTED_EXACT_KEYS = new Set(
  PLOTLY_TRACE_CATALOG_POLICY.globalRejectedFields
    .filter((key) => !key.includes("*"))
    .map((key) => key.toLowerCase()),
);
const PLOTLY_EXTRA_KEYS = new Set(["layout", "config", "style", "display"]);
const DEFAULT_HEIGHT = 320;
const MIN_HEIGHT = 160;
const MAX_HEIGHT = 900;

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
      style={typeof figure.height === "number" ? { height: figure.height } : undefined}
    />
  );
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
  const policy = rejectPlotlyPolicyKeys(payload, "$");
  if (!policy.ok) {
    return policy;
  }
  if (payload.schemaVersion !== 3) {
    return invalid(
      "schemaVersion must be 3 for Plotly 2D template graphics; schemaVersion 2 chartType payloads are retired.",
    );
  }
  if ("chartType" in payload) {
    return invalid("chartType is retired; use figureType plotly2d and traces[].type.");
  }
  if ("data" in payload || "encoding" in payload) {
    return invalid("Legacy data.values plus encoding payloads are retired; use traces[].data.");
  }
  if (payload.figureType !== "plotly2d") {
    return invalid("figureType must be plotly2d.");
  }
  const renderer = validateRenderer(payload.renderer);
  if (!renderer.ok) {
    return renderer;
  }
  const title = nonBlankString(payload.title, "title");
  if (!title.ok) {
    return title;
  }
  const dataRefs = validateDataRefs(payload.dataRefs);
  if (!dataRefs.ok) {
    return dataRefs;
  }
  const traces = validateTraces(payload.traces);
  if (!traces.ok) {
    return traces;
  }
  const sourceRefs = validateSourceRefs(traces.value, dataRefs.value);
  if (!sourceRefs.ok) {
    return sourceRefs;
  }
  const layout = validatePlotlyObject(payload.layout, "layout");
  if (!layout.ok) {
    return layout;
  }
  const config = validatePlotlyObject(payload.config, "config");
  if (!config.ok) {
    return config;
  }
  const display = validatePlotlyObject(payload.display, "display");
  if (!display.ok) {
    return display;
  }
  const extra = validateExtra(payload.extra);
  if (!extra.ok) {
    return extra;
  }
  return {
    ok: true,
    value: {
      schemaVersion: 3,
      figureType: "plotly2d",
      renderer: renderer.value,
      title: title.value,
      subtitle: optionalString(payload.subtitle),
      traces: traces.value,
      dataRefs: dataRefs.value.length > 0 ? dataRefs.value : undefined,
      layout: layout.value,
      config: config.value ?? { responsive: true },
      display: display.value,
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

function validateTraces(value: unknown): ValidationResult<TemplateTrace[]> {
  if (!Array.isArray(value) || value.length === 0) {
    return invalid("traces must be a non-empty array.");
  }
  const traces: TemplateTrace[] = [];
  for (const [index, item] of value.entries()) {
    const trace = validateTrace(item, index);
    if (!trace.ok) {
      return trace;
    }
    traces.push(trace.value);
  }
  return { ok: true, value: traces };
}

function validateTrace(value: unknown, index: number): ValidationResult<TemplateTrace> {
  if (!isRecord(value)) {
    return invalid(`traces.${index} must be an object.`);
  }
  const traceType = traceTypeValue(value.type, `traces.${index}.type`);
  if (!traceType.ok) {
    return traceType;
  }
  const catalogEntry = PLOTLY_2D_TRACE_CATALOG[traceType.value];
  const data = validateTraceObject(
    value.data,
    `traces.${index}.data`,
    new Set(catalogEntry.dataPaths),
  );
  if (!data.ok) {
    return data;
  }
  const style = validateTraceObject(
    value.style,
    `traces.${index}.style`,
    new Set(catalogEntry.stylePaths),
  );
  if (!style.ok) {
    return style;
  }
  const source = validateSource(value.source, `traces.${index}.source`, catalogEntry);
  if (!source.ok) {
    return source;
  }
  if (Object.keys(data.value).length === 0 && !source.value) {
    return invalid(`traces.${index} requires data or source bindings.`);
  }
  const conflict = validateInlineAndSourceDisjoint(data.value, source.value, index);
  if (!conflict.ok) {
    return conflict;
  }
  return {
    ok: true,
    value: {
      type: traceType.value,
      name: optionalString(value.name),
      data: data.value,
      style: style.value,
      source: source.value,
    },
  };
}

function traceTypeValue(value: unknown, path: string): ValidationResult<TraceType> {
  if (typeof value !== "string" || value.trim() === "") {
    return invalid(`${path} must be a non-empty Plotly 2D trace type.`);
  }
  const traceType = value.trim();
  const excludedReason = EXCLUDED_TRACE_TYPES[traceType];
  if (excludedReason) {
    return invalid(`${path} ${traceType} is excluded from Layer 1 template graphics: ${excludedReason}.`);
  }
  if (!SUPPORTED_TRACE_TYPES.has(traceType)) {
    return invalid(`${path} must be one of ${PLOTLY_2D_TRACE_TYPES.join(", ")}.`);
  }
  return { ok: true, value: traceType as TraceType };
}

function validateTraceObject(
  value: unknown,
  path: string,
  allowedPaths: ReadonlySet<string>,
): ValidationResult<PlainObject> {
  if (typeof value === "undefined" || value === null) {
    return { ok: true, value: {} };
  }
  if (!isRecord(value)) {
    return invalid(`${path} must be an object.`);
  }
  const policy = rejectPlotlyPolicyKeys(value, path);
  if (!policy.ok) {
    return policy;
  }
  for (const leafPath of objectLeafPaths(value)) {
    if (!allowedPaths.has(leafPath)) {
      return invalid(`${path}.${leafPath} is not supported by the Plotly 2D trace catalog.`);
    }
  }
  return { ok: true, value };
}

function validateSource(
  value: unknown,
  path: string,
  catalogEntry: PlotlyTraceCatalogEntry,
): ValidationResult<TraceSource | undefined> {
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
  if (!isRecord(value.bindings)) {
    return invalid(`${path}.bindings must be a non-empty object.`);
  }
  const allowedBindings = new Set(catalogEntry.bindingPaths);
  const bindings: Record<string, ColumnBinding> = {};
  for (const [rawPath, rawBinding] of Object.entries(value.bindings)) {
    const bindingPath = normalizeBindingPath(rawPath);
    if (!bindingPath) {
      return invalid(`${path}.bindings contains an empty field path.`);
    }
    if (!allowedBindings.has(bindingPath)) {
      return invalid(`${path}.bindings.${rawPath} is not supported by the Plotly 2D trace catalog.`);
    }
    const binding = columnBinding(rawBinding, `${path}.bindings.${rawPath}`);
    if (!binding.ok) {
      return binding;
    }
    bindings[rawPath.trim()] = binding.value;
  }
  if (Object.keys(bindings).length === 0) {
    return invalid(`${path}.bindings must be a non-empty object.`);
  }
  return { ok: true, value: { dataRef: dataRef.value, bindings } };
}

function columnBinding(value: unknown, path: string): ValidationResult<ColumnBinding> {
  if (!isRecord(value)) {
    return invalid(`${path} must be an object.`);
  }
  const column = nonBlankString(value.column, `${path}.column`);
  if (!column.ok) {
    return column;
  }
  return { ok: true, value: { column: column.value } };
}

function validateInlineAndSourceDisjoint(
  data: PlainObject,
  source: TraceSource | undefined,
  index: number,
): ValidationResult<void> {
  if (!source) {
    return { ok: true, value: undefined };
  }
  const inlinePaths = new Set(objectLeafPaths(data));
  for (const rawPath of Object.keys(source.bindings)) {
    const bindingPath = normalizeBindingPath(rawPath);
    if (inlinePaths.has(bindingPath)) {
      return invalid(`traces.${index}.data.${bindingPath} cannot be combined with source.bindings.${rawPath}.`);
    }
  }
  return { ok: true, value: undefined };
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

function validatePlotlyObject(value: unknown, path: string): ValidationResult<PlainObject | undefined> {
  if (typeof value === "undefined" || value === null) {
    return { ok: true, value: undefined };
  }
  if (!isRecord(value)) {
    return invalid(`${path} must be an object.`);
  }
  const policy = rejectPlotlyPolicyKeys(value, path);
  if (!policy.ok) {
    return policy;
  }
  return { ok: true, value };
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
  for (const key of Object.keys(plotly)) {
    if (!PLOTLY_EXTRA_KEYS.has(key)) {
      return invalid(`extra.plotly.${key} is not allowed in Layer 1 template graphics.`);
    }
  }
  const layout = validatePlotlyObject(plotly.layout, "extra.plotly.layout");
  if (!layout.ok) {
    return layout;
  }
  const config = validatePlotlyObject(plotly.config, "extra.plotly.config");
  if (!config.ok) {
    return config;
  }
  const style = validatePlotlyObject(plotly.style, "extra.plotly.style");
  if (!style.ok) {
    return style;
  }
  const display = validatePlotlyObject(plotly.display, "extra.plotly.display");
  if (!display.ok) {
    return display;
  }
  return {
    ok: true,
    value: {
      plotly: {
        layout: layout.value,
        config: config.value,
        style: style.value,
        display: display.value,
      },
    },
  };
}

function datasourceBindingDiagnostic(payload: TemplatePayload): string | null {
  if (!payload.traces.some((trace) => trace.source)) {
    return null;
  }
  return "Datasource materialization is not supported yet. Inline trace arrays are required for rendering in this workbench.";
}

function compileTemplatePayload(payload: TemplatePayload): ValidationResult<CompiledFigure> {
  const bundleCoverage = validateBundleCoverage(payload.traces);
  if (!bundleCoverage.ok) {
    return bundleCoverage;
  }
  return {
    ok: true,
    value: {
      data: payload.traces.map((trace) => compileTrace(trace)),
      layout: compileLayout(payload),
      config: compileConfig(payload),
      height: displayHeight(payload),
    },
  };
}

function validateBundleCoverage(traces: TemplateTrace[]): ValidationResult<void> {
  for (const trace of traces) {
    if (!REGISTERED_TRACE_TYPES.has(trace.type)) {
      return invalid(`Plotly bundle plotly.js-dist-min does not include trace type ${trace.type}.`);
    }
  }
  return { ok: true, value: undefined };
}

function compileTrace(trace: TemplateTrace): PlotlyTrace {
  return deepMergeObjects(
    { type: trace.type },
    typeof trace.name === "string" ? { name: trace.name } : {},
    trace.data,
    trace.style,
  );
}

function compileLayout(payload: TemplatePayload): PlotlyLayout {
  return deepMergeObjects(
    {
      autosize: true,
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      font: { color: "#f3efe5" },
      margin: { l: 48, r: 18, t: 16, b: 44, pad: 0 },
      xaxis: {
        gridcolor: "rgba(148, 163, 184, 0.26)",
        zerolinecolor: "rgba(148, 163, 184, 0.35)",
      },
      yaxis: {
        gridcolor: "rgba(148, 163, 184, 0.26)",
        zerolinecolor: "rgba(148, 163, 184, 0.35)",
      },
    },
    payload.layout ?? {},
    payload.extra?.plotly?.layout ?? {},
  );
}

function compileConfig(payload: TemplatePayload): PlotlyConfig {
  return deepMergeObjects(
    { responsive: true, displayModeBar: false },
    payload.config,
    payload.extra?.plotly?.config ?? {},
  );
}

function displayHeight(payload: TemplatePayload): number | undefined {
  const displayHeightValue =
    numberValue(payload.display?.height) ?? numberValue(payload.extra?.plotly?.display?.height);
  if (typeof displayHeightValue !== "number") {
    return undefined;
  }
  return Math.min(MAX_HEIGHT, Math.max(MIN_HEIGHT, displayHeightValue));
}

function objectLeafPaths(value: unknown): string[] {
  const paths = new Set<string>();
  collectObjectLeafPaths(value, [], paths);
  return Array.from(paths).sort();
}

function collectObjectLeafPaths(value: unknown, path: string[], paths: Set<string>): void {
  if (Array.isArray(value)) {
    if (value.length === 0 && path.length > 0) {
      paths.add(path.join("."));
      return;
    }
    let hasScalar = false;
    for (const item of value) {
      if (isRecord(item) || Array.isArray(item)) {
        collectObjectLeafPaths(item, path, paths);
      } else {
        hasScalar = true;
      }
    }
    if (hasScalar && path.length > 0) {
      paths.add(path.join("."));
    }
    return;
  }
  if (isRecord(value)) {
    const entries = Object.entries(value);
    if (entries.length === 0 && path.length > 0) {
      paths.add(path.join("."));
      return;
    }
    for (const [key, item] of entries) {
      collectObjectLeafPaths(item, [...path, key], paths);
    }
    return;
  }
  if (path.length > 0) {
    paths.add(path.join("."));
  }
}

function normalizeBindingPath(path: string): string {
  const stripped = path.trim();
  return stripped.startsWith("data.") ? stripped.slice("data.".length) : stripped;
}

function rejectPlotlyPolicyKeys(value: unknown, path: string): ValidationResult<void> {
  if (Array.isArray(value)) {
    for (const [index, item] of value.entries()) {
      const result = rejectPlotlyPolicyKeys(item, `${path}.${index}`);
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
    const lowerKey = key.toLowerCase();
    const nextPath = `${path}.${key}`;
    if (
      lowerKey.endsWith("src") ||
      PLOTLY_POLICY_REJECTED_EXACT_KEYS.has(lowerKey) ||
      SECRET_FIELD_PATTERN.test(key)
    ) {
      return invalid(`${nextPath} is not allowed in Layer 1 Plotly template graphics.`);
    }
    const result = rejectPlotlyPolicyKeys(item, nextPath);
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

function nonBlankString(value: unknown, field: string): ValidationResult<string> {
  if (typeof value !== "string" || value.trim() === "") {
    return invalid(`${field} must be a non-empty string.`);
  }
  return { ok: true, value: value.trim() };
}

function optionalString(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

function numberValue(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function deepMergeObjects(...objects: PlainObject[]): PlainObject {
  const merged: PlainObject = {};
  for (const object of objects) {
    for (const [key, value] of Object.entries(object)) {
      const current = merged[key];
      if (isRecord(current) && isRecord(value)) {
        merged[key] = deepMergeObjects(current, value);
      } else {
        merged[key] = cloneJsonValue(value);
      }
    }
  }
  return stripUndefined(merged);
}

function cloneJsonValue(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => cloneJsonValue(item));
  }
  if (isRecord(value)) {
    return deepMergeObjects(value);
  }
  return value;
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

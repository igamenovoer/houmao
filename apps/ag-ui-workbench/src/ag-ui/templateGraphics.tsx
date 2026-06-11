import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import vegaEmbed, { type Result as VegaEmbedResult, type VisualizationSpec } from "vega-embed";

import type { JsonObject, JsonScalar, JsonValue } from "./types";

export interface TemplateRendererContext {
  paneId: string;
  toolCallId: string;
}

type ChartType = "bar" | "line" | "scatter" | "area" | "pie";
type FieldType = "nominal" | "ordinal" | "quantitative" | "temporal" | "boolean";
type RendererId = "recharts" | "vega-lite";
type ValidationResult<T> = { ok: true; value: T } | { ok: false; error: string };
type DataRow = Record<string, JsonValue>;
type TemplateRenderer = (payload: TemplateGraphicPayload, context: TemplateRendererContext) => ReactNode;

interface RendererSelection {
  preferred: string;
  fallback: string[];
}

interface TemplateGraphicData {
  values: DataRow[];
}

interface TemplateGraphicChannel {
  field: string;
  type: FieldType;
  title?: string;
  aggregate?: "count" | "sum" | "mean" | "median" | "min" | "max";
  sort?: "ascending" | "descending";
}

interface TemplateGraphicEncoding {
  x?: TemplateGraphicChannel;
  y?: TemplateGraphicChannel;
  color?: TemplateGraphicChannel;
  size?: TemplateGraphicChannel;
  theta?: TemplateGraphicChannel;
  tooltip: boolean | TemplateGraphicChannel[];
}

interface TemplateGraphicInteractions {
  tooltip: boolean;
  legend: boolean;
}

interface TemplateGraphicStyle {
  colorScheme?: string;
  width?: number;
  height?: number;
}

interface TemplateGraphicPayload {
  schemaVersion: 1;
  chartType: ChartType;
  renderer: RendererSelection;
  title: string;
  subtitle?: string;
  data: TemplateGraphicData;
  encoding: TemplateGraphicEncoding;
  interactions: TemplateGraphicInteractions;
  style?: TemplateGraphicStyle;
  extra: Record<string, JsonObject>;
}

const CHART_TYPES: readonly ChartType[] = ["bar", "line", "scatter", "area", "pie"];
const FIELD_TYPES: readonly FieldType[] = ["nominal", "ordinal", "quantitative", "temporal", "boolean"];
const RENDERERS: readonly RendererId[] = ["vega-lite", "recharts"];
const TEMPLATE_COLORS = ["#79a35d", "#d3a749", "#6aa6b8", "#c86f5a", "#9a82c8", "#d88a42"];
const REMOTE_URL_PATTERN = /^https?:\/\//i;
const VEGA_LITE_EXTRA_ALLOWED_KEYS = new Set(["axis", "config", "height", "legend", "mark", "view", "width"]);
const VEGA_LITE_EXTRA_DISALLOWED_KEYS = new Set([
  "$schema",
  "autosize",
  "concat",
  "data",
  "datasets",
  "encoding",
  "facet",
  "hconcat",
  "layer",
  "params",
  "projection",
  "repeat",
  "resolve",
  "signals",
  "spec",
  "transform",
  "usermeta",
  "vconcat",
]);

const TEMPLATE_RENDERERS: Record<RendererId, { supports: (payload: TemplateGraphicPayload) => boolean; render: TemplateRenderer }> = {
  "vega-lite": {
    supports: () => true,
    render: renderVegaLiteTemplate,
  },
  recharts: {
    supports: () => true,
    render: renderRechartsTemplate,
  },
};

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
  const rendererId = selectRenderer(validated.value);
  if (!rendererId) {
    return (
      <TemplateFallback
        paneId={context.paneId}
        title={validated.value.title}
        detail="No supported template graphic renderer is available."
        raw={safeJson(payload)}
      />
    );
  }
  return <>{TEMPLATE_RENDERERS[rendererId].render(validated.value, context)}</>;
}

function renderRechartsTemplate(payload: TemplateGraphicPayload, context: TemplateRendererContext): ReactNode {
  switch (payload.chartType) {
    case "bar":
      return renderRechartsBar(payload, context);
    case "line":
      return renderRechartsLine(payload, context);
    case "scatter":
      return renderRechartsScatter(payload, context);
    case "area":
      return renderRechartsArea(payload, context);
    case "pie":
      return renderRechartsPie(payload, context);
  }
}

function renderRechartsBar(payload: TemplateGraphicPayload, context: TemplateRendererContext): ReactNode {
  const x = payload.encoding.x!;
  const y = payload.encoding.y!;
  return (
    <TemplateFrame paneId={context.paneId} title={payload.title} subtitle={payload.subtitle}>
      <div className="component-chart" data-testid={`component-chart-${context.paneId}`}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={payload.data.values} margin={{ top: 8, right: 18, bottom: 18, left: 4 }}>
            <CartesianGrid stroke="#44483d" vertical={false} />
            <XAxis dataKey={x.field} stroke="#c9c0af" label={axisLabel(x.title, "bottom")} />
            <YAxis stroke="#c9c0af" label={axisLabel(y.title, "left")} />
            {payload.interactions.tooltip ? <Tooltip contentStyle={tooltipStyle} /> : null}
            {payload.interactions.legend && payload.encoding.color ? <Legend /> : null}
            <Bar dataKey={y.field} radius={[3, 3, 0, 0]}>
              {payload.data.values.map((row, index) => (
                <Cell
                  key={`bar-${index}`}
                  fill={colorForRow(row, payload.encoding.color, index)}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </TemplateFrame>
  );
}

function renderRechartsLine(payload: TemplateGraphicPayload, context: TemplateRendererContext): ReactNode {
  const x = payload.encoding.x!;
  const y = payload.encoding.y!;
  return (
    <TemplateFrame paneId={context.paneId} title={payload.title} subtitle={payload.subtitle}>
      <div className="component-chart" data-testid={`component-chart-${context.paneId}`}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={payload.data.values} margin={{ top: 8, right: 20, bottom: 18, left: 4 }}>
            <CartesianGrid stroke="#44483d" vertical={false} />
            <XAxis dataKey={x.field} stroke="#c9c0af" label={axisLabel(x.title, "bottom")} />
            <YAxis stroke="#c9c0af" label={axisLabel(y.title, "left")} />
            {payload.interactions.tooltip ? <Tooltip contentStyle={tooltipStyle} /> : null}
            {payload.interactions.legend ? <Legend /> : null}
            <Line
              type="monotone"
              dataKey={y.field}
              stroke={TEMPLATE_COLORS[0]}
              strokeWidth={2}
              dot={{ r: 3 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </TemplateFrame>
  );
}

function renderRechartsScatter(payload: TemplateGraphicPayload, context: TemplateRendererContext): ReactNode {
  const x = payload.encoding.x!;
  const y = payload.encoding.y!;
  return (
    <TemplateFrame paneId={context.paneId} title={payload.title} subtitle={payload.subtitle}>
      <div className="component-chart" data-testid={`component-chart-${context.paneId}`}>
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 8, right: 20, bottom: 18, left: 4 }}>
            <CartesianGrid stroke="#44483d" />
            <XAxis dataKey={x.field} stroke="#c9c0af" name={x.title ?? x.field} />
            <YAxis dataKey={y.field} stroke="#c9c0af" name={y.title ?? y.field} />
            {payload.interactions.tooltip ? <Tooltip contentStyle={tooltipStyle} /> : null}
            <Scatter data={payload.data.values} fill={TEMPLATE_COLORS[0]} />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </TemplateFrame>
  );
}

function renderRechartsArea(payload: TemplateGraphicPayload, context: TemplateRendererContext): ReactNode {
  const x = payload.encoding.x!;
  const y = payload.encoding.y!;
  return (
    <TemplateFrame paneId={context.paneId} title={payload.title} subtitle={payload.subtitle}>
      <div className="component-chart" data-testid={`component-chart-${context.paneId}`}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={payload.data.values} margin={{ top: 8, right: 20, bottom: 18, left: 4 }}>
            <CartesianGrid stroke="#44483d" vertical={false} />
            <XAxis dataKey={x.field} stroke="#c9c0af" label={axisLabel(x.title, "bottom")} />
            <YAxis stroke="#c9c0af" label={axisLabel(y.title, "left")} />
            {payload.interactions.tooltip ? <Tooltip contentStyle={tooltipStyle} /> : null}
            <Area
              type="monotone"
              dataKey={y.field}
              stroke={TEMPLATE_COLORS[0]}
              fill={TEMPLATE_COLORS[0]}
              fillOpacity={0.28}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </TemplateFrame>
  );
}

function renderRechartsPie(payload: TemplateGraphicPayload, context: TemplateRendererContext): ReactNode {
  const color = payload.encoding.color!;
  const theta = payload.encoding.theta!;
  const data = payload.data.values.map((row, index) => ({
    label: formatValue(row[color.field]),
    value: numberValue(row[theta.field]),
    color: colorForRow(row, color, index),
  }));
  return (
    <TemplateFrame paneId={context.paneId} title={payload.title} subtitle={payload.subtitle}>
      <div className="component-chart component-chart-pie" data-testid={`component-chart-${context.paneId}`}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            {payload.interactions.tooltip ? <Tooltip contentStyle={tooltipStyle} /> : null}
            {payload.interactions.legend ? <Legend /> : null}
            <Pie data={data} dataKey="value" nameKey="label" outerRadius="78%" label>
              {data.map((row, index) => (
                <Cell key={`${row.label}-${index}`} fill={row.color} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      </div>
    </TemplateFrame>
  );
}

function renderVegaLiteTemplate(payload: TemplateGraphicPayload, context: TemplateRendererContext): ReactNode {
  return (
    <TemplateFrame paneId={context.paneId} title={payload.title} subtitle={payload.subtitle}>
      <VegaLiteTemplateView
        paneId={context.paneId}
        spec={templatePayloadToVegaLiteSpec(payload)}
      />
    </TemplateFrame>
  );
}

function VegaLiteTemplateView({ paneId, spec }: { paneId: string; spec: VisualizationSpec }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [error, setError] = useState<string | null>(null);
  const specText = useMemo(() => JSON.stringify(spec), [spec]);

  useEffect(() => {
    let result: VegaEmbedResult | null = null;
    let cancelled = false;
    setError(null);
    if (!containerRef.current) {
      return undefined;
    }
    containerRef.current.replaceChildren();
    void vegaEmbed(containerRef.current, JSON.parse(specText) as VisualizationSpec, {
      actions: false,
      renderer: "svg",
      tooltip: true,
    })
      .then((nextResult) => {
        if (cancelled) {
          nextResult.finalize();
          return;
        }
        result = nextResult;
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Vega-Lite render failed.");
        }
      });
    return () => {
      cancelled = true;
      result?.finalize();
    };
  }, [specText]);

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
      className="component-chart template-vega-lite-chart"
      data-testid={`template-chart-vega-lite-${paneId}`}
    />
  );
}

function templatePayloadToVegaLiteSpec(payload: TemplateGraphicPayload): VisualizationSpec {
  const extra = isRecord(payload.extra["vega-lite"]) ? payload.extra["vega-lite"] : {};
  const markExtra = isRecord(extra.mark) ? extra.mark : {};
  const configExtra = isRecord(extra.config) ? extra.config : {};
  const config: JsonObject = { ...configExtra };
  if (isRecord(extra.axis)) {
    config.axis = extra.axis;
  }
  if (isRecord(extra.legend)) {
    config.legend = extra.legend;
  }
  if (isRecord(extra.view)) {
    config.view = extra.view;
  }
  const spec: JsonObject = {
    $schema: "https://vega.github.io/schema/vega-lite/v6.json",
    title: payload.title,
    data: { values: payload.data.values },
    mark: { type: vegaLiteMarkType(payload.chartType), tooltip: payload.interactions.tooltip, ...markExtra },
    encoding: vegaLiteEncoding(payload),
    config,
  };
  const width = numberValue(extra.width) ?? payload.style?.width;
  const height = numberValue(extra.height) ?? payload.style?.height;
  if (width) {
    spec.width = width;
  }
  if (height) {
    spec.height = height;
  }
  return spec as VisualizationSpec;
}

function vegaLiteEncoding(payload: TemplateGraphicPayload): JsonObject {
  const encoding: JsonObject = {};
  for (const key of ["x", "y", "color", "size", "theta"] as const) {
    const channel = payload.encoding[key];
    if (channel) {
      encoding[key] = vegaLiteChannel(channel);
    }
  }
  if (payload.encoding.tooltip === true) {
    const channels = [payload.encoding.x, payload.encoding.y, payload.encoding.color, payload.encoding.size, payload.encoding.theta]
      .filter((item): item is TemplateGraphicChannel => item !== undefined);
    encoding.tooltip = channels.map(vegaLiteChannel);
  } else if (Array.isArray(payload.encoding.tooltip)) {
    encoding.tooltip = payload.encoding.tooltip.map(vegaLiteChannel);
  }
  return encoding;
}

function vegaLiteChannel(channel: TemplateGraphicChannel): JsonObject {
  const value: JsonObject = {
    field: channel.field,
    type: vegaLiteFieldType(channel.type),
  };
  if (channel.title) {
    value.title = channel.title;
  }
  if (channel.aggregate) {
    value.aggregate = channel.aggregate;
  }
  if (channel.sort) {
    value.sort = channel.sort;
  }
  return value;
}

function vegaLiteFieldType(fieldType: FieldType): string {
  return fieldType === "boolean" ? "nominal" : fieldType;
}

function vegaLiteMarkType(chartType: ChartType): string {
  if (chartType === "area") {
    return "area";
  }
  if (chartType === "scatter") {
    return "point";
  }
  if (chartType === "pie") {
    return "arc";
  }
  return chartType;
}

function selectRenderer(payload: TemplateGraphicPayload): RendererId | null {
  const requested = uniqueValues([
    payload.renderer.preferred,
    ...payload.renderer.fallback,
    "vega-lite",
    "recharts",
  ]);
  for (const candidate of requested) {
    if (!isRendererId(candidate)) {
      continue;
    }
    const renderer = TEMPLATE_RENDERERS[candidate];
    if (renderer.supports(payload)) {
      return candidate;
    }
  }
  return null;
}

function validateTemplatePayload(payload: unknown): ValidationResult<TemplateGraphicPayload> {
  const record = versionedRecord(payload);
  if (!record.ok) {
    return record;
  }
  const chartType = enumValue(record.value.chartType, CHART_TYPES, "chartType");
  if (!chartType.ok) {
    return chartType;
  }
  const title = nonBlankString(record.value.title, "title");
  if (!title.ok) {
    return title;
  }
  const renderer = validateRendererSelection(record.value.renderer);
  if (!renderer.ok) {
    return renderer;
  }
  const data = validateTemplateData(record.value.data);
  if (!data.ok) {
    return data;
  }
  const encoding = validateTemplateEncoding(record.value.encoding, chartType.value, data.value.values);
  if (!encoding.ok) {
    return encoding;
  }
  const interactions = validateInteractions(record.value.interactions);
  if (!interactions.ok) {
    return interactions;
  }
  const style = validateStyle(record.value.style);
  if (!style.ok) {
    return style;
  }
  const extra = validateExtra(record.value.extra);
  if (!extra.ok) {
    return extra;
  }
  return {
    ok: true,
    value: {
      schemaVersion: 1,
      chartType: chartType.value,
      renderer: renderer.value,
      title: title.value,
      subtitle: optionalString(record.value.subtitle),
      data: data.value,
      encoding: encoding.value,
      interactions: interactions.value,
      style: style.value,
      extra: extra.value,
    },
  };
}

function validateRendererSelection(value: unknown): ValidationResult<RendererSelection> {
  const record = isRecord(value) ? value : {};
  const preferred = typeof record.preferred === "undefined" ? "vega-lite" : nonBlankString(record.preferred, "renderer.preferred");
  if (typeof preferred !== "string" && !preferred.ok) {
    return preferred;
  }
  const fallbackValue = typeof record.fallback === "undefined" ? ["recharts"] : record.fallback;
  if (!Array.isArray(fallbackValue)) {
    return invalid("renderer.fallback must be an array.");
  }
  const fallback: string[] = [];
  for (const [index, item] of fallbackValue.entries()) {
    const rendererId = nonBlankString(item, `renderer.fallback.${index}`);
    if (!rendererId.ok) {
      return rendererId;
    }
    fallback.push(rendererId.value);
  }
  return {
    ok: true,
    value: {
      preferred: typeof preferred === "string" ? preferred : preferred.value,
      fallback,
    },
  };
}

function validateTemplateData(value: unknown): ValidationResult<TemplateGraphicData> {
  if (!isRecord(value)) {
    return invalid("data must be an object.");
  }
  if (!Array.isArray(value.values) || value.values.length === 0) {
    return invalid("data.values must be a non-empty array.");
  }
  const rows: DataRow[] = [];
  for (const [index, row] of value.values.entries()) {
    if (!isRecord(row)) {
      return invalid(`data.values.${index} must be an object.`);
    }
    rows.push(row);
  }
  return { ok: true, value: { values: rows } };
}

function validateTemplateEncoding(
  value: unknown,
  chartType: ChartType,
  rows: DataRow[],
): ValidationResult<TemplateGraphicEncoding> {
  if (!isRecord(value)) {
    return invalid("encoding must be an object.");
  }
  const x = validateOptionalChannel(value.x, "encoding.x");
  if (isValidationFailure(x)) {
    return x;
  }
  const y = validateOptionalChannel(value.y, "encoding.y");
  if (isValidationFailure(y)) {
    return y;
  }
  const color = validateOptionalChannel(value.color, "encoding.color");
  if (isValidationFailure(color)) {
    return color;
  }
  const size = validateOptionalChannel(value.size, "encoding.size");
  if (isValidationFailure(size)) {
    return size;
  }
  const theta = validateOptionalChannel(value.theta, "encoding.theta");
  if (isValidationFailure(theta)) {
    return theta;
  }
  const tooltip = validateTooltip(value.tooltip);
  if (isValidationFailure(tooltip)) {
    return tooltip;
  }
  const encoding: TemplateGraphicEncoding = {
    x,
    y,
    color,
    size,
    theta,
    tooltip,
  };
  const normalized = encoding;
  if (chartType === "pie") {
    if (!normalized.theta || !normalized.color) {
      return invalid("pie charts require encoding.theta and encoding.color.");
    }
  } else if (!normalized.x || !normalized.y) {
    return invalid(`${chartType} charts require encoding.x and encoding.y.`);
  }
  for (const fieldName of requiredFieldNames(normalized)) {
    for (const [rowIndex, row] of rows.entries()) {
      if (!(fieldName in row)) {
        return invalid(`data.values.${rowIndex}.${fieldName} is missing.`);
      }
    }
  }
  return { ok: true, value: normalized };
}

function validateOptionalChannel(value: unknown, path: string): TemplateGraphicChannel | ValidationResult<never> | undefined {
  if (typeof value === "undefined" || value === null) {
    return undefined;
  }
  return validateChannel(value, path);
}

function validateChannel(value: unknown, path: string): TemplateGraphicChannel | ValidationResult<never> {
  if (!isRecord(value)) {
    return invalid(`${path} must be an object.`);
  }
  const field = nonBlankString(value.field, `${path}.field`);
  if (!field.ok) {
    return field;
  }
  const type = enumValue(value.type, FIELD_TYPES, `${path}.type`);
  if (!type.ok) {
    return type;
  }
  const aggregate = enumOptional(value.aggregate, ["count", "sum", "mean", "median", "min", "max"], `${path}.aggregate`);
  if (isValidationFailure(aggregate)) {
    return aggregate;
  }
  const sort = enumOptional(value.sort, ["ascending", "descending"], `${path}.sort`);
  if (isValidationFailure(sort)) {
    return sort;
  }
  return {
    field: field.value,
    type: type.value,
    title: optionalString(value.title),
    aggregate,
    sort,
  };
}

function validateTooltip(value: unknown): boolean | TemplateGraphicChannel[] | ValidationResult<never> {
  if (typeof value === "undefined") {
    return true;
  }
  if (typeof value === "boolean") {
    return value;
  }
  if (!Array.isArray(value) || value.length === 0) {
    return invalid("encoding.tooltip must be a boolean or non-empty array.");
  }
  const channels: TemplateGraphicChannel[] = [];
  for (const [index, item] of value.entries()) {
    const channel = validateChannel(item, `encoding.tooltip.${index}`);
    if (isValidationFailure(channel)) {
      return channel;
    }
    channels.push(channel);
  }
  return channels;
}

function validateInteractions(value: unknown): ValidationResult<TemplateGraphicInteractions> {
  if (typeof value === "undefined") {
    return { ok: true, value: { tooltip: true, legend: true } };
  }
  if (!isRecord(value)) {
    return invalid("interactions must be an object.");
  }
  return {
    ok: true,
    value: {
      tooltip: typeof value.tooltip === "boolean" ? value.tooltip : true,
      legend: typeof value.legend === "boolean" ? value.legend : true,
    },
  };
}

function validateStyle(value: unknown): ValidationResult<TemplateGraphicStyle | undefined> {
  if (typeof value === "undefined" || value === null) {
    return { ok: true, value: undefined };
  }
  if (!isRecord(value)) {
    return invalid("style must be an object.");
  }
  return {
    ok: true,
    value: {
      colorScheme: optionalString(value.colorScheme),
      width: boundedNumber(value.width, 120, 2400),
      height: boundedNumber(value.height, 120, 1800),
    },
  };
}

function validateExtra(value: unknown): ValidationResult<Record<string, JsonObject>> {
  if (typeof value === "undefined") {
    return { ok: true, value: {} };
  }
  if (!isRecord(value)) {
    return invalid("extra must be an object.");
  }
  const extra: Record<string, JsonObject> = {};
  for (const [key, block] of Object.entries(value)) {
    if (!isRecord(block)) {
      return invalid(`extra.${key} must be an object.`);
    }
    const remoteUrlValidation = rejectRemoteUrls(block, `extra.${key}`);
    if (!remoteUrlValidation.ok) {
      return remoteUrlValidation;
    }
    if (key === "vega-lite") {
      const vegaLiteValidation = validateVegaLiteExtra(block, `extra.${key}`);
      if (!vegaLiteValidation.ok) {
        return vegaLiteValidation;
      }
    }
    extra[key] = block;
  }
  return { ok: true, value: extra };
}

function validateVegaLiteExtra(value: JsonObject, path: string): ValidationResult<void> {
  const rawSpecValidation = rejectVegaLiteSpecKeys(value, path);
  if (!rawSpecValidation.ok) {
    return rawSpecValidation;
  }
  for (const key of Object.keys(value)) {
    if (!VEGA_LITE_EXTRA_ALLOWED_KEYS.has(key)) {
      return invalid(`${path}.${key} is not allowed in Layer 1 Vega-Lite extra.`);
    }
  }
  return { ok: true, value: undefined };
}

function rejectVegaLiteSpecKeys(value: unknown, path: string): ValidationResult<void> {
  if (Array.isArray(value)) {
    for (const [index, item] of value.entries()) {
      const result = rejectVegaLiteSpecKeys(item, `${path}.${index}`);
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
    if (VEGA_LITE_EXTRA_DISALLOWED_KEYS.has(key)) {
      return invalid(`${nextPath} is not allowed in Layer 1 Vega-Lite extra.`);
    }
    const result = rejectVegaLiteSpecKeys(item, nextPath);
    if (!result.ok) {
      return result;
    }
  }
  return { ok: true, value: undefined };
}

function rejectRemoteUrls(value: unknown, path: string): ValidationResult<void> {
  if (typeof value === "string") {
    return REMOTE_URL_PATTERN.test(value)
      ? invalid(`${path} must not contain remote URLs in Layer 1 extra.`)
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

function requiredFieldNames(encoding: TemplateGraphicEncoding): string[] {
  const names = new Set<string>();
  for (const channel of [encoding.x, encoding.y, encoding.color, encoding.size, encoding.theta]) {
    if (channel) {
      names.add(channel.field);
    }
  }
  if (Array.isArray(encoding.tooltip)) {
    for (const channel of encoding.tooltip) {
      names.add(channel.field);
    }
  }
  return [...names];
}

function isValidationFailure<T>(value: T | ValidationResult<never>): value is ValidationResult<never> {
  return isRecord(value) && value.ok === false && typeof value.error === "string";
}

function enumOptional<T extends string>(
  value: unknown,
  values: readonly T[],
  label: string,
): T | ValidationResult<never> | undefined {
  if (typeof value === "undefined" || value === null) {
    return undefined;
  }
  const result = enumValue(value, values, label);
  return result.ok ? result.value : result;
}

function boundedNumber(value: unknown, min: number, max: number): number | undefined {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return undefined;
  }
  return Math.min(max, Math.max(min, value));
}

function versionedRecord(value: unknown): ValidationResult<JsonObject> {
  if (!isRecord(value)) {
    return invalid("payload must be an object.");
  }
  if (value.schemaVersion !== 1) {
    return invalid("schemaVersion must be 1.");
  }
  return { ok: true, value };
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

function enumValue<T extends string>(value: unknown, values: readonly T[], label: string): ValidationResult<T> {
  if (typeof value !== "string" || !values.includes(value as T)) {
    return invalid(`${label} must be one of ${values.join(", ")}.`);
  }
  return { ok: true, value: value as T };
}

function invalid(error: string): ValidationResult<never> {
  return { ok: false, error };
}

function uniqueValues(values: string[]): string[] {
  return [...new Set(values)];
}

function isRendererId(value: string): value is RendererId {
  return RENDERERS.includes(value as RendererId);
}

function isRecord(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function safeJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function colorForRow(row: DataRow, channel: TemplateGraphicChannel | undefined, index: number): string {
  if (channel) {
    const value = row[channel.field];
    if (typeof value === "string" && /^#[0-9a-f]{6}$/i.test(value)) {
      return value;
    }
  }
  return TEMPLATE_COLORS[index % TEMPLATE_COLORS.length];
}

function formatValue(value: JsonValue | undefined): string {
  if (typeof value === "undefined") {
    return "";
  }
  if (typeof value === "object" && value !== null) {
    return JSON.stringify(value);
  }
  return String(value as JsonScalar);
}

function numberValue(value: JsonValue | undefined): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function axisLabel(value: string | undefined, position: "bottom" | "left") {
  if (!value) {
    return undefined;
  }
  return position === "bottom"
    ? { value, position: "insideBottom", offset: -8, fill: "#c9c0af" }
    : { value, angle: -90, position: "insideLeft", fill: "#c9c0af" };
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

const tooltipStyle = {
  background: "#24241f",
  border: "1px solid #55584f",
  borderRadius: "5px",
  color: "#f3efe5",
};

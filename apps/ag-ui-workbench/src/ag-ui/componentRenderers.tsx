import type { ReactNode } from "react";

import type { ToolCallRecord } from "./reducer";
import type { GraphicArtifact, JsonObject, JsonScalar, JsonValue } from "./types";
import { GraphicView } from "./graphics";
import { renderTemplateGraphic } from "./templateGraphics";

interface ToolCallRendererProps {
  toolCall: ToolCallRecord;
  paneId: string;
}

interface TableColumn {
  key: string;
  label: string;
  kind: "text" | "number" | "boolean";
  align?: "left" | "right" | "center";
}

interface TablePayload {
  schemaVersion: 1;
  title?: string;
  columns: TableColumn[];
  rows: JsonObject[];
}

interface MetricItem {
  label: string;
  value: string | number;
  unit?: string;
  delta?: string;
  trend?: "up" | "down" | "neutral";
}

interface MetricGridPayload {
  schemaVersion: 1;
  title?: string;
  metrics: MetricItem[];
}

interface DashboardChild {
  component: string;
  props: JsonObject;
  width: "full" | "half" | "third";
}

interface DashboardPayload {
  schemaVersion: 1;
  title: string;
  children: DashboardChild[];
}

type ValidationResult<T> = { ok: true; value: T } | { ok: false; error: string };
type ComponentRenderer = (payload: unknown, context: RendererContext) => ReactNode;

interface RendererContext {
  paneId: string;
  toolCallId: string;
  depth: number;
}

const MAX_DASHBOARD_DEPTH = 3;

const COMPONENT_RENDERERS: Record<string, ComponentRenderer> = {
  "houmao.graphic.template": renderTemplateGraphic,
  "houmao.table": renderTable,
  "houmao.metric_grid": renderMetricGrid,
  "houmao.dashboard": renderDashboard,
};

export function ToolCallRenderer({ toolCall, paneId }: ToolCallRendererProps) {
  if (!toolCall.complete) {
    return null;
  }
  const parsed = parseToolArgs(toolCall.argsText);
  if (!parsed.ok) {
    return (
      <ComponentFallback
        paneId={paneId}
        kind="invalid"
        title={toolCall.name}
        detail={parsed.error}
        raw={toolCall.argsText}
      />
    );
  }
  if (toolCall.name === "houmao_render_graphic") {
    return renderGraphicCompatibility(parsed.value, {
      paneId,
      toolCallId: toolCall.id,
      depth: 0,
    });
  }
  const renderer = COMPONENT_RENDERERS[toolCall.name];
  if (renderer) {
    return (
      <>
        {renderer(parsed.value, {
          paneId,
          toolCallId: toolCall.id,
          depth: 0,
        })}
      </>
    );
  }
  if (toolCall.name.startsWith("houmao.")) {
    return (
      <ComponentFallback
        paneId={paneId}
        kind="unknown"
        title={toolCall.name}
        detail="Unknown or retired Houmao component."
        raw={toolCall.argsText}
      />
    );
  }
  return null;
}

function renderTable(payload: unknown, context: RendererContext): ReactNode {
  const validated = validateTable(payload);
  if (!validated.ok) {
    return invalidComponent(context, "houmao.table", validated.error, payload);
  }
  return (
    <ComponentFrame paneId={context.paneId} title={validated.value.title ?? "Table"}>
      <div className="component-table-wrap">
        <table className="component-table" data-testid={`component-table-${context.paneId}`}>
          <thead>
            <tr>
              {validated.value.columns.map((column) => (
                <th key={column.key} className={column.align ? `align-${column.align}` : undefined}>
                  {column.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {validated.value.rows.map((row, rowIndex) => (
              <tr key={`row-${rowIndex}`}>
                {validated.value.columns.map((column) => (
                  <td key={column.key} className={column.align ? `align-${column.align}` : undefined}>
                    {formatCell(row[column.key])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </ComponentFrame>
  );
}

function renderMetricGrid(payload: unknown, context: RendererContext): ReactNode {
  const validated = validateMetricGrid(payload);
  if (!validated.ok) {
    return invalidComponent(context, "houmao.metric_grid", validated.error, payload);
  }
  return (
    <ComponentFrame paneId={context.paneId} title={validated.value.title ?? "Metrics"}>
      <div className="metric-grid" data-testid={`component-metric-grid-${context.paneId}`}>
        {validated.value.metrics.map((metric) => (
          <div className="metric-tile" key={metric.label}>
            <span>{metric.label}</span>
            <strong>
              {metric.value}
              {metric.unit ? <small>{metric.unit}</small> : null}
            </strong>
            {metric.delta ? <em className={metric.trend ?? "neutral"}>{metric.delta}</em> : null}
          </div>
        ))}
      </div>
    </ComponentFrame>
  );
}

function renderDashboard(payload: unknown, context: RendererContext): ReactNode {
  if (context.depth >= MAX_DASHBOARD_DEPTH) {
    return invalidComponent(context, "houmao.dashboard", "Dashboard nesting is too deep.", payload);
  }
  const validated = validateDashboard(payload);
  if (!validated.ok) {
    return invalidComponent(context, "houmao.dashboard", validated.error, payload);
  }
  return (
    <ComponentFrame paneId={context.paneId} title={validated.value.title}>
      <div className="component-dashboard" data-testid={`component-dashboard-${context.paneId}`}>
        {validated.value.children.map((child, index) => (
          <div className={`dashboard-cell ${child.width}`} key={`${child.component}-${index}`}>
            {renderNestedComponent(child.component, child.props, {
              paneId: context.paneId,
              toolCallId: `${context.toolCallId}-${index}`,
              depth: context.depth + 1,
            })}
          </div>
        ))}
      </div>
    </ComponentFrame>
  );
}

function renderNestedComponent(component: string, payload: unknown, context: RendererContext): ReactNode {
  const renderer = COMPONENT_RENDERERS[component];
  if (!renderer) {
    return (
      <ComponentFallback
        paneId={context.paneId}
        kind="unknown"
        title={component}
        detail="Unknown or retired dashboard child component."
        raw={safeJson(payload)}
      />
    );
  }
  return renderer(payload, context);
}

function renderGraphicCompatibility(payload: unknown, context: RendererContext): ReactNode {
  if (!isRecord(payload)) {
    return invalidComponent(context, "houmao_render_graphic", "Graphic payload must be an object.", payload);
  }
  return <GraphicView artifact={payload as unknown as GraphicArtifact} paneId={context.paneId} />;
}

function ComponentFrame({
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

function ComponentFallback({
  paneId,
  kind,
  title,
  detail,
  raw,
}: {
  paneId: string;
  kind: "invalid" | "unknown";
  title: string;
  detail: string;
  raw: string;
}) {
  return (
    <details className="component-fallback" data-testid={`${kind}-component-${paneId}`} open>
      <summary>
        {kind === "unknown" ? "Unknown component" : "Invalid component"}: {title}
      </summary>
      <p>{detail}</p>
      <pre>{raw}</pre>
    </details>
  );
}

function invalidComponent(
  context: RendererContext,
  title: string,
  detail: string,
  payload: unknown,
): ReactNode {
  return (
    <ComponentFallback
      paneId={context.paneId}
      kind="invalid"
      title={title}
      detail={detail}
      raw={safeJson(payload)}
    />
  );
}

function validateTable(payload: unknown): ValidationResult<TablePayload> {
  const record = versionedRecord(payload);
  if (!record.ok) {
    return record;
  }
  if (!Array.isArray(record.value.columns) || record.value.columns.length === 0) {
    return invalid("columns must be a non-empty array.");
  }
  if (!Array.isArray(record.value.rows) || record.value.rows.length === 0) {
    return invalid("rows must be a non-empty array.");
  }
  const columns = record.value.columns.map(validateColumn);
  const failedColumn = columns.find((item) => !item.ok);
  if (failedColumn && !failedColumn.ok) {
    return failedColumn;
  }
  const normalizedColumns = columns.map((item) => (item as { ok: true; value: TableColumn }).value);
  const rows: JsonObject[] = [];
  for (const [index, row] of record.value.rows.entries()) {
    if (!isRecord(row)) {
      return invalid(`rows.${index} must be an object.`);
    }
    for (const column of normalizedColumns) {
      if (!(column.key in row)) {
        return invalid(`rows.${index}.${column.key} is missing.`);
      }
    }
    rows.push(row);
  }
  return {
    ok: true,
    value: {
      schemaVersion: 1,
      title: optionalString(record.value.title),
      columns: normalizedColumns,
      rows,
    },
  };
}

function validateMetricGrid(payload: unknown): ValidationResult<MetricGridPayload> {
  const record = versionedRecord(payload);
  if (!record.ok) {
    return record;
  }
  if (!Array.isArray(record.value.metrics) || record.value.metrics.length === 0) {
    return invalid("metrics must be a non-empty array.");
  }
  const metrics = record.value.metrics.map(validateMetric);
  const failed = metrics.find((item) => !item.ok);
  if (failed && !failed.ok) {
    return failed;
  }
  return {
    ok: true,
    value: {
      schemaVersion: 1,
      title: optionalString(record.value.title),
      metrics: metrics.map((item) => (item as { ok: true; value: MetricItem }).value),
    },
  };
}

function validateDashboard(payload: unknown): ValidationResult<DashboardPayload> {
  const record = versionedRecord(payload);
  if (!record.ok) {
    return record;
  }
  const title = nonBlankString(record.value.title, "title");
  if (!title.ok) {
    return title;
  }
  if (!Array.isArray(record.value.children) || record.value.children.length === 0) {
    return invalid("children must be a non-empty array.");
  }
  const children = record.value.children.map(validateDashboardChild);
  const failed = children.find((item) => !item.ok);
  if (failed && !failed.ok) {
    return failed;
  }
  return {
    ok: true,
    value: {
      schemaVersion: 1,
      title: title.value,
      children: children.map((item) => (item as { ok: true; value: DashboardChild }).value),
    },
  };
}

function validateColumn(value: unknown, index: number): ValidationResult<TableColumn> {
  if (!isRecord(value)) {
    return invalid(`columns.${index} must be an object.`);
  }
  const key = nonBlankString(value.key, `columns.${index}.key`);
  const label = nonBlankString(value.label, `columns.${index}.label`);
  if (!key.ok) {
    return key;
  }
  if (!label.ok) {
    return label;
  }
  const kind = enumValue(value.kind ?? "text", ["text", "number", "boolean"], "column kind");
  if (!kind.ok) {
    return kind;
  }
  const align =
    typeof value.align === "undefined"
      ? undefined
      : enumValue(value.align, ["left", "right", "center"], "column align");
  if (align && !align.ok) {
    return align;
  }
  return {
    ok: true,
    value: {
      key: key.value,
      label: label.value,
      kind: kind.value,
      align: align?.value,
    },
  };
}

function validateMetric(value: unknown, index: number): ValidationResult<MetricItem> {
  if (!isRecord(value)) {
    return invalid(`metrics.${index} must be an object.`);
  }
  const label = nonBlankString(value.label, `metrics.${index}.label`);
  if (!label.ok) {
    return label;
  }
  if (typeof value.value !== "string" && typeof value.value !== "number") {
    return invalid(`metrics.${index}.value must be a string or number.`);
  }
  const trend =
    typeof value.trend === "undefined"
      ? undefined
      : enumValue(value.trend, ["up", "down", "neutral"], "trend");
  if (trend && !trend.ok) {
    return trend;
  }
  return {
    ok: true,
    value: {
      label: label.value,
      value: value.value,
      unit: optionalString(value.unit),
      delta: optionalString(value.delta),
      trend: trend?.value,
    },
  };
}

function validateDashboardChild(value: unknown, index: number): ValidationResult<DashboardChild> {
  if (!isRecord(value)) {
    return invalid(`children.${index} must be an object.`);
  }
  const component = nonBlankString(value.component, `children.${index}.component`);
  if (!component.ok) {
    return component;
  }
  if (!isRecord(value.props)) {
    return invalid(`children.${index}.props must be an object.`);
  }
  const width =
    typeof value.width === "undefined"
      ? { ok: true as const, value: "full" as const }
      : enumValue(value.width, ["full", "half", "third"], "child width");
  if (!width.ok) {
    return width;
  }
  return {
    ok: true,
    value: {
      component: component.value,
      props: value.props,
      width: width.value,
    },
  };
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

function invalid(error: string): ValidationResult<never> {
  return { ok: false, error };
}

function parseToolArgs(argsText: string): ValidationResult<unknown> {
  try {
    return { ok: true, value: JSON.parse(argsText) as unknown };
  } catch {
    return invalid("Tool-call arguments are not valid JSON.");
  }
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

function formatCell(value: JsonValue | undefined): string {
  if (typeof value === "undefined") {
    return "";
  }
  if (typeof value === "object" && value !== null) {
    return JSON.stringify(value);
  }
  return String(value as JsonScalar);
}

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import vegaEmbed, {
  type Result as VegaEmbedResult,
  type VisualizationSpec,
} from "vega-embed";

export interface VegaDslRendererContext {
  paneId: string;
  toolCallId: string;
}

type ValidationResult<T> = { ok: true; value: T } | { ok: false; error: string };
type PlainObject = Record<string, unknown>;
type VegaLiteDisplay = {
  width?: number;
  height?: number;
  aspectRatio?: number;
  caption?: string;
  description?: string;
};

interface VegaLitePayload {
  schemaVersion: 1;
  library: "vega-lite";
  specVersion: "6";
  title: string;
  description?: string;
  spec: PlainObject;
  display?: VegaLiteDisplay;
}

interface DisabledVegaLoader {
  load: (uri: string) => Promise<string>;
  sanitize: (uri: string) => Promise<{ href: string }>;
  http: (uri: string) => Promise<string>;
  file: (filename: string) => Promise<string>;
}

const REMOTE_URL_PATTERN = /^https?:\/\//i;
const VEGALITE_SCHEMA_URL_PATTERN =
  /^https:\/\/vega\.github\.io\/schema\/vega-lite\/v6(?:\.\d+)*\.json$/i;
const UNSAFE_TEXT_PATTERNS = [
  /<\s*script\b/i,
  /\son[a-z0-9_-]+\s*=/i,
  /javascript\s*:/i,
  /<\s*iframe\b/i,
  /<\s*svg\b/i,
  /image\/svg\+xml/i,
];
const MAX_PAYLOAD_BYTES = 128 * 1024;
const DEFAULT_HEIGHT = 320;
const MIN_HEIGHT = 160;
const MAX_HEIGHT = 720;
const DISABLED_LOADER: DisabledVegaLoader = {
  load: blockExternalLoad,
  sanitize: async (uri: string) => {
    throw new Error(`External Vega-Lite loading is disabled for ${safeUri(uri)}.`);
  },
  http: blockExternalLoad,
  file: blockExternalLoad,
};

export function renderVegaDslGraphic(payload: unknown, context: VegaDslRendererContext): ReactNode {
  const validated = validateVegaLitePayload(payload);
  if (!validated.ok) {
    return (
      <VegaFallback
        paneId={context.paneId}
        title="houmao.graphic.vegalite"
        detail={validated.error}
        raw={safeJson(payload)}
      />
    );
  }
  return (
    <VegaFrame
      paneId={context.paneId}
      title={validated.value.title}
      subtitle={validated.value.description}
    >
      <VegaLiteView paneId={context.paneId} payload={validated.value} />
    </VegaFrame>
  );
}

function VegaLiteView({ paneId, payload }: { paneId: string; payload: VegaLitePayload }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [error, setError] = useState<string | null>(null);
  const height = boundedHeight(payload.display?.height);
  const specKey = useMemo(() => JSON.stringify({ spec: payload.spec, height }), [payload.spec, height]);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) {
      return undefined;
    }
    let cancelled = false;
    let result: VegaEmbedResult | null = null;
    setError(null);
    element.replaceChildren();
    const spec = responsiveSpec(payload.spec, height);
    void vegaEmbed(element, spec as VisualizationSpec, {
      actions: false,
      defaultStyle: false,
      loader: DISABLED_LOADER,
      mode: "vega-lite",
      renderer: "svg",
      tooltip: false,
      config: {
        background: null,
        view: { stroke: null },
      },
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
          element.replaceChildren();
          setError(err instanceof Error ? err.message : "Vega-Lite render failed.");
        }
      });
    return () => {
      cancelled = true;
      result?.finalize();
      element.replaceChildren();
    };
  }, [specKey, height, payload.spec]);

  if (error) {
    return (
      <div className="component-fallback" data-testid={`invalid-component-${paneId}`}>
        <p>{error}</p>
      </div>
    );
  }
  return (
    <>
      <div
        ref={containerRef}
        className="component-chart vega-lite-chart"
        data-testid={`vega-lite-chart-${paneId}`}
        style={{ height }}
      />
      {payload.display?.caption ? (
        <p className="component-caption">{payload.display.caption}</p>
      ) : null}
    </>
  );
}

function validateVegaLitePayload(payload: unknown): ValidationResult<VegaLitePayload> {
  if (!isRecord(payload)) {
    return invalid("payload must be an object.");
  }
  const encodedSize = encodedJsonSize(payload);
  if (encodedSize > MAX_PAYLOAD_BYTES) {
    return invalid(`payload is ${encodedSize} bytes, above the limit of ${MAX_PAYLOAD_BYTES}.`);
  }
  if (payload.schemaVersion !== 1) {
    return invalid("schemaVersion must be 1.");
  }
  if (payload.library !== "vega-lite") {
    return invalid("library must be vega-lite.");
  }
  if (payload.specVersion !== "6") {
    return invalid("specVersion must be 6.");
  }
  const title = nonBlankString(payload.title, "title");
  if (!title.ok) {
    return title;
  }
  if (!isRecord(payload.spec)) {
    return invalid("spec must be a Vega-Lite JSON object.");
  }
  const unsafe = rejectUnsafeText(payload, "$");
  if (!unsafe.ok) {
    return unsafe;
  }
  const remote = rejectVegaLiteRemoteLoading(payload.spec, "spec");
  if (!remote.ok) {
    return remote;
  }
  const display = displayValue(payload.display);
  if (!display.ok) {
    return display;
  }
  return {
    ok: true,
    value: {
      schemaVersion: 1,
      library: "vega-lite",
      specVersion: "6",
      title: title.value,
      description: optionalString(payload.description),
      spec: payload.spec,
      display: display.value,
    },
  };
}

function responsiveSpec(spec: PlainObject, height: number): PlainObject {
  return {
    ...spec,
    autosize: isRecord(spec.autosize) ? spec.autosize : { type: "fit", contains: "padding" },
    width: typeof spec.width === "undefined" ? "container" : spec.width,
    height: typeof spec.height === "undefined" ? height : spec.height,
  };
}

function displayValue(value: unknown): ValidationResult<VegaLiteDisplay | undefined> {
  if (typeof value === "undefined" || value === null) {
    return { ok: true, value: undefined };
  }
  if (!isRecord(value)) {
    return invalid("display must be an object.");
  }
  return {
    ok: true,
    value: {
      width: numberOrUndefined(value.width),
      height: numberOrUndefined(value.height),
      aspectRatio: numberOrUndefined(value.aspectRatio),
      caption: optionalString(value.caption),
      description: optionalString(value.description),
    },
  };
}

function rejectVegaLiteRemoteLoading(value: unknown, path: string): ValidationResult<void> {
  if (typeof value === "string") {
    const stripped = value.trim();
    if (REMOTE_URL_PATTERN.test(stripped) && !allowedVegaLiteSchemaUrl(stripped, path)) {
      return invalid(`${path} contains remote URL content; use inline data.values.`);
    }
    return { ok: true, value: undefined };
  }
  if (Array.isArray(value)) {
    for (const [index, item] of value.entries()) {
      const result = rejectVegaLiteRemoteLoading(item, `${path}.${index}`);
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
    if (key === "url" && typeof item !== "undefined" && item !== null) {
      return invalid(`${nextPath} is disabled; use inline data.values.`);
    }
    const result = rejectVegaLiteRemoteLoading(item, nextPath);
    if (!result.ok) {
      return result;
    }
  }
  return { ok: true, value: undefined };
}

function rejectUnsafeText(value: unknown, path: string): ValidationResult<void> {
  if (typeof value === "string") {
    if (UNSAFE_TEXT_PATTERNS.some((pattern) => pattern.test(value))) {
      return invalid(`${path} contains unsafe inline content.`);
    }
    return { ok: true, value: undefined };
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

function allowedVegaLiteSchemaUrl(value: string, path: string): boolean {
  return path.endsWith(".$schema") && VEGALITE_SCHEMA_URL_PATTERN.test(value);
}

function boundedHeight(value: number | undefined): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return DEFAULT_HEIGHT;
  }
  return Math.min(MAX_HEIGHT, Math.max(MIN_HEIGHT, Math.round(value)));
}

async function blockExternalLoad(uri: string): Promise<string> {
  throw new Error(`External Vega-Lite loading is disabled for ${safeUri(uri)}.`);
}

function safeUri(uri: string): string {
  return uri.length > 80 ? `${uri.slice(0, 77)}...` : uri;
}

function encodedJsonSize(value: unknown): number {
  try {
    return new TextEncoder().encode(JSON.stringify(value)).length;
  } catch {
    return Number.POSITIVE_INFINITY;
  }
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

function numberOrUndefined(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function isRecord(value: unknown): value is PlainObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function invalid(error: string): ValidationResult<never> {
  return { ok: false, error };
}

function safeJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function VegaFrame({
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

function VegaFallback({
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

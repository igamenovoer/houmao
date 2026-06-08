import type { NormalizedAgUiTarget, TargetConfig } from "./types";

const ROUTE_NAMES = new Set(["capabilities", "connect", "runs"]);
const DIRECT_AG_UI_PREFIX = "/v1/ag-ui";

export function normalizeAgUiTarget(config: TargetConfig): NormalizedAgUiTarget {
  const trimmed = config.url.trim();
  if (!trimmed) {
    throw new Error("AG-UI target URL is required.");
  }
  const inputUrl = new URL(trimmed);
  const routeBase = normalizeRouteBase(inputUrl);
  return {
    inputUrl: inputUrl.toString(),
    baseUrl: routeBase.toString(),
    capabilitiesUrl: routeUrl(routeBase, "capabilities"),
    connectUrl: routeUrl(routeBase, "connect"),
    runsUrl: routeUrl(routeBase, "runs"),
    detachUrlTemplate: routeUrl(routeBase, "connections/{connection_id}"),
  };
}

export function proxiedTargetUrl(targetUrl: string): string {
  return `/__houmao_ag_ui_proxy?target=${encodeURIComponent(targetUrl)}`;
}

export function detachUrl(target: NormalizedAgUiTarget, connectionId: string): string {
  return target.detachUrlTemplate
    .replace("{connection_id}", encodeURIComponent(connectionId))
    .replace("%7Bconnection_id%7D", encodeURIComponent(connectionId));
}

function normalizeRouteBase(url: URL): URL {
  const segments = url.pathname.split("/").filter(Boolean);
  if (segments.length > 0 && ROUTE_NAMES.has(segments[segments.length - 1])) {
    segments.pop();
  } else if (segments.length > 1 && segments[segments.length - 2] === "connections") {
    segments.splice(segments.length - 2, 2);
  }

  const v1Index = firstSubsequenceIndex(segments, ["v1", "ag-ui"]);
  if (v1Index >= 0) {
    url.pathname = `/${segments.slice(0, v1Index + 2).join("/")}`;
    url.search = "";
    url.hash = "";
    return url;
  }

  const passiveIndex = segments.lastIndexOf("ag-ui");
  if (passiveIndex >= 0) {
    url.pathname = `/${segments.slice(0, passiveIndex + 1).join("/")}`;
    url.search = "";
    url.hash = "";
    return url;
  }

  const prefix = url.pathname.replace(/\/+$/, "");
  url.pathname = `${prefix}${DIRECT_AG_UI_PREFIX}`;
  url.search = "";
  url.hash = "";
  return url;
}

function firstSubsequenceIndex(values: string[], subsequence: string[]): number {
  for (let index = 0; index <= values.length - subsequence.length; index += 1) {
    if (subsequence.every((value, offset) => values[index + offset] === value)) {
      return index;
    }
  }
  return -1;
}

function routeUrl(base: URL, route: string): string {
  const url = new URL(base.toString());
  url.pathname = `${url.pathname.replace(/\/+$/, "")}/${route}`;
  return url.toString();
}

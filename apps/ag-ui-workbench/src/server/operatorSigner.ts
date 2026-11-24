import { spawn } from "node:child_process";
import { constants } from "node:fs";
import { open } from "node:fs/promises";
import path from "node:path";

import type { OperatorSignerSelection } from "../shared/workbenchProtocol";
import { isRecord } from "../shared/workbenchProtocol";
import { resolveAllowedTarget } from "./agUiProxy";

const MAX_DOCUMENT_BYTES = 64 * 1024;
const PROOF_TIMEOUT_MS = 8_000;
const AG_UI_PATH = "/v1/ag-ui";

export interface OperatorSignerConfig {
  clientBindingPath: string;
  agentId: string;
  gatewayBaseUrl: string;
  passiveServerUrl?: string;
}

export interface ProofRequest {
  clientBindingPath: string;
  agentId: string;
  baseUrl: string;
  discovered: boolean;
  generationId?: string;
  method: string;
  path: string;
  bodyBase64: string;
}

export type ProofHelper = (
  request: ProofRequest,
  signal: AbortSignal,
) => Promise<Record<string, string>>;

export class OperatorSignerError extends Error {
  constructor(readonly status: number, readonly code: string, detail: string) {
    super(detail);
  }
}

export class OperatorSigner {
  private readonly gatewayBase: URL;
  private readonly passiveBase?: URL;

  constructor(config: OperatorSignerConfig, private readonly helper: ProofHelper) {
    this.gatewayBase = trustedBaseUrl(config.gatewayBaseUrl);
    this.passiveBase = config.passiveServerUrl ? trustedBaseUrl(config.passiveServerUrl) : undefined;
    this.config = config;
  }

  private readonly config: OperatorSignerConfig;

  async prepare(
    selection: OperatorSignerSelection,
    targetUrl: string,
    method: string,
    body: string,
    signal: AbortSignal,
  ): Promise<{ url: string; headers: Record<string, string> }> {
    const operation = new URL(targetUrl);
    let base = this.gatewayBase;
    let generationId: string | undefined;
    if (selection.kind === "discovered") {
      if (
        this.passiveBase === undefined ||
        selection.agentId !== this.config.agentId ||
        !sameBaseUrl(selection.passiveServerUrl, this.passiveBase)
      ) {
        throw targetRejected();
      }
      const live = await this.resolveDiscoveredGateway(signal);
      generationId = live.generationId;
      base = live.base;
    } else if (this.passiveBase !== undefined) {
      throw targetRejected();
    }
    if (operation.username || operation.password || operation.hash) {
      throw targetRejected();
    }
    const prefix = stripTrailingSlash(base.pathname);
    const routeBase = selection.kind === "discovered"
      ? operation.pathname.indexOf(`${AG_UI_PATH}/`)
      : operation.pathname.startsWith(`${prefix}${AG_UI_PATH}/`) && operation.origin === base.origin
        ? prefix.length
        : -1;
    const route = operation.pathname.slice(routeBase);
    if (routeBase < 0 || !approvedOperation(method, route, operation.search)) {
      throw targetRejected();
    }
    const baseUrl = stripTrailingSlash(base.href);
    const requestPath = `${route}${operation.search}`;
    const headers = await this.helper(
      {
        clientBindingPath: this.config.clientBindingPath,
        agentId: this.config.agentId,
        baseUrl,
        discovered: selection.kind === "discovered",
        generationId,
        method,
        path: requestPath,
        bodyBase64: Buffer.from(body).toString("base64"),
      },
      signal,
    );
    return { url: `${baseUrl}${requestPath}`, headers };
  }

  private async resolveDiscoveredGateway(signal: AbortSignal): Promise<{ base: URL; generationId: string }> {
    const passive = this.passiveBase!;
    const route = `${stripTrailingSlash(passive.href)}/houmao/agents/${encodeURIComponent(this.config.agentId)}/resolve`;
    try {
      const response = await fetch(route, {
        redirect: "manual",
        signal: AbortSignal.any([signal, AbortSignal.timeout(PROOF_TIMEOUT_MS)]),
      });
      if (response.status >= 300 && response.status < 400) {
        await response.body?.cancel();
        throw targetRejected();
      }
      if (!response.ok) {
        await response.body?.cancel();
        throw new Error("Target address unavailable");
      }
      const value: unknown = JSON.parse(await readBoundedResponse(response));
      if (!isRecord(value) || value.agentId !== this.config.agentId) {
        throw targetRejected();
      }
      if (value.status !== "live_with_gateway") {
        throw new Error("Target gateway unavailable");
      }
      if (
        !isRecord(value.gateway) ||
        typeof value.gateway.host !== "string" ||
        !advertisedHostMatches(value.gateway.host, this.gatewayBase, passive) ||
        typeof value.gateway.port !== "number" ||
        !Number.isInteger(value.gateway.port) ||
        value.gateway.port < 1 ||
        value.gateway.port > 65535 ||
        typeof value.generationId !== "string" ||
        value.generationId.length === 0
      ) {
        throw targetRejected();
      }
      const base = new URL(this.gatewayBase);
      base.port = String(value.gateway.port);
      trustedBaseUrl(base.href);
      return { base, generationId: value.generationId };
    } catch (error) {
      if (error instanceof OperatorSignerError) {
        throw error;
      }
      throw new OperatorSignerError(502, "target_unavailable", "The approved discovery source has no reachable gateway.");
    }
  }
}

export async function readOperatorConfig(filename: string): Promise<OperatorSignerConfig> {
  if (!path.isAbsolute(filename)) {
    throw new Error("The operator configuration requires an absolute path.");
  }
  const file = await open(filename, constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
  try {
    const info = await file.stat();
    if (!info.isFile() || info.uid !== process.getuid?.() || (info.mode & 0o077) || info.size > MAX_DOCUMENT_BYTES) {
      throw new Error("The operator configuration must be a small owner-private file.");
    }
    const input = Buffer.alloc(MAX_DOCUMENT_BYTES + 1);
    let length = 0;
    while (length < input.length) {
      const { bytesRead } = await file.read(input, length, input.length - length);
      if (!bytesRead) break;
      length += bytesRead;
    }
    if (length > MAX_DOCUMENT_BYTES) {
      throw new Error("The operator configuration exceeds its size limit.");
    }
    const value: unknown = JSON.parse(input.toString("utf8", 0, length));
    if (
      !isRecord(value) ||
      typeof value.clientBindingPath !== "string" ||
      !path.isAbsolute(value.clientBindingPath) ||
      typeof value.agentId !== "string" ||
      !value.agentId || value.agentId.length > 256 ||
      typeof value.gatewayBaseUrl !== "string" ||
      (value.passiveServerUrl !== undefined && typeof value.passiveServerUrl !== "string")
    ) {
      throw new Error("The operator configuration is invalid.");
    }
    return {
      clientBindingPath: value.clientBindingPath,
      agentId: value.agentId,
      gatewayBaseUrl: value.gatewayBaseUrl,
      passiveServerUrl: value.passiveServerUrl,
    };
  } finally {
    await file.close();
  }
}

export function createProofHelper(script: string): ProofHelper {
  return (request, signal) =>
    new Promise((resolve, reject) => {
      const child = spawn(process.env.HOUMAO_AG_UI_WORKBENCH_PYTHON ?? "python3", [script], {
        stdio: ["pipe", "pipe", "ignore"],
        signal: AbortSignal.any([signal, AbortSignal.timeout(PROOF_TIMEOUT_MS)]),
        killSignal: "SIGKILL",
      });
      const chunks: Buffer[] = [];
      let bytes = 0;
      child.on("error", () => reject(helperUnavailable()));
      child.stdin.on("error", () => reject(helperUnavailable()));
      child.stdout.on("data", (chunk: Buffer) => {
        bytes += chunk.length;
        if (bytes > MAX_DOCUMENT_BYTES) {
          child.kill("SIGKILL");
          reject(helperUnavailable());
        } else {
          chunks.push(chunk);
        }
      });
      child.on("close", (code) => {
        if (code !== 0) {
          reject(helperUnavailable());
          return;
        }
        try {
          const response: unknown = JSON.parse(Buffer.concat(chunks).toString("utf8"));
          if (!isRecord(response)) throw new Error("Invalid proof response");
          if (response.status === 401 || response.status === 403) {
            reject(new OperatorSignerError(response.status, "operator_proof_refused", "The gateway refused the selected operator proof."));
            return;
          }
          if (response.status === 409) {
            reject(new OperatorSignerError(409, "target_moved", "The approved gateway changed before proof. Resolve it again."));
            return;
          }
          if (response.status === 503) {
            reject(new OperatorSignerError(503, "operator_target_unavailable", "The approved gateway's policy is unavailable."));
            return;
          }
          if (response.status !== 200 || !isRecord(response.headers)) {
            throw new Error("Proof unavailable");
          }
          const headers = Object.entries(response.headers);
          const names = new Set(headers.map(([name]) => name.toLowerCase()));
          if (
            headers.length !== 2 ||
            !names.has("houmao-challenge") ||
            !names.has("houmao-signature") ||
            !headers.every(([, value]) => typeof value === "string" && /^[\x21-\x7e]{1,16384}$/.test(value))
          ) {
            throw new Error("Invalid proof headers");
          }
          resolve(Object.fromEntries(headers) as Record<string, string>);
        } catch {
          reject(helperUnavailable());
        }
      });
      child.stdin.end(JSON.stringify(request));
    });
}

function approvedOperation(method: string, route: string, query: string): boolean {
  if (route === `${AG_UI_PATH}/active-thread`) {
    if (method === "DELETE") {
      return !query || /^\?threadId=[^&]*$/.test(query);
    }
    return !query && (method === "GET" || method === "PUT");
  }
  if (query) return false;
  if (method === "GET") {
    return route === `${AG_UI_PATH}/capabilities` || route === `${AG_UI_PATH}/destination`;
  }
  if (method === "POST") {
    return route === `${AG_UI_PATH}/connect` || route === `${AG_UI_PATH}/runs`;
  }
  return method === "DELETE" && /^\/v1\/ag-ui\/connections\/[A-Za-z0-9_.:-]{1,256}$/.test(route);
}

function advertisedHostMatches(advertisedHost: string, gateway: URL, passive: URL): boolean {
  const host = advertisedHost.toLowerCase();
  return host === gateway.hostname ||
    (["0.0.0.0", "127.0.0.1", "localhost", "::1", "[::1]"].includes(host) &&
      (gateway.hostname === passive.hostname || gateway.hostname === "127.0.0.1" && passive.hostname === "localhost"));
}

function trustedBaseUrl(value: string): URL {
  const url = new URL(value);
  if (
    !resolveAllowedTarget(url.href).allowed ||
    url.username || url.password || url.search || url.hash ||
    (url.protocol === "http:" && !["127.0.0.1", "[::1]", "localhost"].includes(url.hostname))
  ) {
    throw targetRejected();
  }
  return url;
}

function stripTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
}

function sameBaseUrl(value: string, approved: URL): boolean {
  try {
    return stripTrailingSlash(trustedBaseUrl(value).href) === stripTrailingSlash(approved.href);
  } catch {
    return false;
  }
}

async function readBoundedResponse(response: Response): Promise<string> {
  const reader = response.body?.getReader();
  if (!reader) throw new Error("Empty target response");
  const chunks: Buffer[] = [];
  let length = 0;
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      length += value.byteLength;
      if (length > MAX_DOCUMENT_BYTES) throw new Error("Target response is too large");
      chunks.push(Buffer.from(value));
    }
    return Buffer.concat(chunks).toString("utf8");
  } finally {
    await reader.cancel();
  }
}

function targetRejected(): OperatorSignerError {
  return new OperatorSignerError(403, "operator_target_rejected", "The request does not match the approved operator target.");
}

function helperUnavailable(): OperatorSignerError {
  return new OperatorSignerError(502, "operator_proof_unavailable", "The configured operator proof is unavailable.");
}

import { randomBytes, timingSafeEqual } from "node:crypto";
import type { IncomingMessage } from "node:http";

import type { FastifyInstance } from "fastify";

import {
  OPERATOR_BOOTSTRAP_PATH,
  OPERATOR_SESSION_HEADER,
  OPERATOR_SOCKET_PREFIX,
  isRecord,
} from "../shared/workbenchProtocol";

const BOOTSTRAP_TTL_MS = 2 * 60 * 1000;
const SESSION_TTL_MS = 8 * 60 * 60 * 1000;
const SECRET_PATTERN = /^[A-Za-z0-9_-]{43}$/;

/**
 * A workbench process serves one operator on one precise loopback origin.
 * Use a request header rather than cookies, whose scope ignores the local port.
 */
export class OperatorSession {
  private origin: URL | null = null;
  private bootstrap: { token: string; expires: number } | null = null;
  private session: { token: string; expires: number } | null = null;

  setOrigin(address: string): string {
    this.origin = new URL(address);
    const token = newSecret();
    this.bootstrap = { token, expires: Date.now() + BOOTSTRAP_TTL_MS };
    const launchUrl = new URL(this.origin);
    launchUrl.hash = `operator=${token}`;
    return launchUrl.toString();
  }

  register(app: FastifyInstance, protectedPrefixes: string[]): void {
    app.addHook("onRequest", async (request, reply) => {
      reply.raw.setHeader("X-Content-Type-Options", "nosniff");
      reply.raw.setHeader("Referrer-Policy", "no-referrer");
      reply.raw.setHeader(
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; " +
          "img-src 'self' data: blob: https:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
      );
      if (!this.isLocalRequest(request.raw)) {
        return reply.code(403).send({ code: "operator_origin_rejected", detail: "Use the workbench's local origin." });
      }
      const path = request.routeOptions.url ?? request.url.split("?", 1)[0];
      if (
        path !== OPERATOR_BOOTSTRAP_PATH &&
        protectedPrefixes.some((prefix) => path === prefix || path.startsWith(`${prefix}/`)) &&
        !this.authorizesHttp(request.raw)
      ) {
        return reply.code(401).send({ code: "operator_session_required", detail: "Open the local operator session." });
      }
    });
    app.post(OPERATOR_BOOTSTRAP_PATH, async (request, reply) => {
      const token = isRecord(request.body) ? request.body.token : undefined;
      if (!this.isLocalRequest(request.raw, true) || !matchesSecret(token, this.bootstrap)) {
        return reply.code(403).send({ code: "operator_bootstrap_denied", detail: "The operator launch URL is invalid or expired." });
      }
      this.bootstrap = null;
      const session = newSecret();
      this.session = { token: session, expires: Date.now() + SESSION_TTL_MS };
      return reply.header("Cache-Control", "no-store").send({ session });
    });
  }

  authorizesUpgrade(request: IncomingMessage): boolean {
    const protocol = request.headers["sec-websocket-protocol"];
    return (
      this.isLocalRequest(request, true) &&
      typeof protocol === "string" &&
      protocol.startsWith(OPERATOR_SOCKET_PREFIX) &&
      matchesSecret(protocol.slice(OPERATOR_SOCKET_PREFIX.length), this.session)
    );
  }

  remainingSessionMs(): number {
    return Math.max(0, (this.session?.expires ?? 0) - Date.now());
  }

  private authorizesHttp(request: IncomingMessage): boolean {
    const requiresOrigin = request.method !== "GET" && request.method !== "HEAD";
    return this.isLocalRequest(request, requiresOrigin) &&
      matchesSecret(request.headers[OPERATOR_SESSION_HEADER], this.session);
  }

  private isLocalRequest(request: IncomingMessage, requireOrigin = false): boolean {
    const origin = request.headers.origin;
    const site = request.headers["sec-fetch-site"];
    return (
      this.origin !== null &&
      request.headers.host === this.origin.host &&
      (origin === this.origin.origin || (!requireOrigin && origin === undefined)) &&
      (site === undefined || site === "same-origin" || site === "none")
    );
  }
}

export function isOperatorLoopbackHost(host: string): boolean {
  return host === "127.0.0.1" || host === "::1";
}

function newSecret(): string {
  return randomBytes(32).toString("base64url");
}

function matchesSecret(
  presented: unknown,
  stored: { token: string; expires: number } | null,
): boolean {
  return (
    stored !== null &&
    Date.now() < stored.expires &&
    typeof presented === "string" &&
    SECRET_PATTERN.test(presented) &&
    timingSafeEqual(Buffer.from(presented), Buffer.from(stored.token))
  );
}

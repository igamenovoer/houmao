import {
  OPERATOR_BOOTSTRAP_PATH,
  OPERATOR_SESSION_HEADER,
  OPERATOR_SOCKET_PREFIX,
} from "./shared/workbenchProtocol";

const STORAGE_KEY = "houmao-workbench-operator-session";
let operatorSession: string | undefined;

export async function initializeOperatorSession(): Promise<void> {
  try {
    operatorSession = sessionStorage.getItem(STORAGE_KEY) ?? undefined;
  } catch {
    // The local session can still live in memory when tab storage is unavailable.
  }
  const launch = new URL(location.href);
  const token = new URLSearchParams(launch.hash.slice(1)).get("operator");
  if (!token) return;

  launch.hash = "";
  history.replaceState(history.state, "", launch.toString());
  const response = await fetch(OPERATOR_BOOTSTRAP_PATH, {
    method: "POST",
    credentials: "omit",
    redirect: "error",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ token }),
  });
  if (!response.ok) throw new Error("This operator launch URL is invalid or expired.");
  const result = (await response.json()) as { session: string };
  operatorSession = result.session;
  try {
    sessionStorage.setItem(STORAGE_KEY, operatorSession);
  } catch {
    // Proceed with the in-memory session.
  }
}

export function hasOperatorSession(): boolean {
  return operatorSession !== undefined;
}

export function fetchWorkbench(input: string, request: RequestInit = {}): Promise<Response> {
  if (!operatorSession) return fetch(input, request);
  const url = new URL(input, location.origin);
  if (url.origin !== location.origin) {
    return Promise.reject(new Error("The workbench session is local to this origin."));
  }
  const headers = new Headers(request.headers);
  headers.set(OPERATOR_SESSION_HEADER, operatorSession);
  return fetch(url, { ...request, headers, redirect: "error" });
}

export function operatorSocketProtocol(): string | undefined {
  return operatorSession === undefined ? undefined : `${OPERATOR_SOCKET_PREFIX}${operatorSession}`;
}

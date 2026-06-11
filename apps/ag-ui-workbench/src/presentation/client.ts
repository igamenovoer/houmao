import {
  WORKBENCH_API_PREFIX,
  type PresentationSessionCreateRequest,
  type PresentationSessionView,
} from "../shared/workbenchProtocol";

export interface PresentationSessionListResponse {
  sessions: PresentationSessionView[];
  diagnostics: {
    owner: "workbench-local-server";
    sessionCount: number;
    paneCount: number;
    datasourceContentsStoredInBrowser: false;
  };
}

export async function listPresentationSessions(
  signal?: AbortSignal,
): Promise<PresentationSessionListResponse> {
  const response = await fetch(`${WORKBENCH_API_PREFIX}/presentation-sessions`, {
    method: "GET",
    signal,
    headers: { accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return (await response.json()) as PresentationSessionListResponse;
}

export async function createPresentationSession(
  request: PresentationSessionCreateRequest,
  signal?: AbortSignal,
): Promise<PresentationSessionView> {
  const response = await fetch(`${WORKBENCH_API_PREFIX}/presentation-sessions`, {
    method: "POST",
    signal,
    headers: {
      accept: "application/json",
      "content-type": "application/json",
    },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  const payload = (await response.json()) as { session: PresentationSessionView };
  return payload.session;
}

export async function disposePresentationSession(
  sessionId: string,
  signal?: AbortSignal,
): Promise<boolean> {
  const response = await fetch(
    `${WORKBENCH_API_PREFIX}/presentation-sessions/${encodeURIComponent(sessionId)}`,
    {
      method: "DELETE",
      signal,
      headers: { accept: "application/json" },
    },
  );
  if (!response.ok) {
    throw new Error(await response.text());
  }
  const payload = (await response.json()) as { disposed: boolean };
  return payload.disposed;
}

export type TmuxAttachMode = "read-write" | "read-only";

export interface TmuxBridgeStatus {
  status: "ready" | "unavailable";
  tmuxAvailable: boolean;
  detail?: string;
  routes?: string[];
}

export interface TmuxSessionRow {
  sessionName: string;
  windowCount: number;
  attached: boolean;
  createdAtUtc: string;
}

export interface TmuxSessionsResponse {
  status: "ready" | "unavailable" | "error";
  tmuxAvailable: boolean;
  sessions: TmuxSessionRow[];
  detail?: string;
}

export async function fetchTmuxStatus(signal?: AbortSignal): Promise<TmuxBridgeStatus> {
  const response = await fetch("/__houmao_tmux/status", {
    method: "GET",
    signal,
    headers: {
      accept: "application/json",
    },
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return (await response.json()) as TmuxBridgeStatus;
}

export async function fetchTmuxSessions(signal?: AbortSignal): Promise<TmuxSessionsResponse> {
  const response = await fetch("/__houmao_tmux/sessions", {
    method: "GET",
    signal,
    headers: {
      accept: "application/json",
    },
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return (await response.json()) as TmuxSessionsResponse;
}

export function openTmuxAttachSocket(): WebSocket {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return new WebSocket(`${protocol}//${window.location.host}/__houmao_tmux/attach`);
}

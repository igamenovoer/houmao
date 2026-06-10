import { useEffect, useMemo, useRef, useState } from "react";
import type { IDockviewPanelProps } from "dockview-react";
import Fuse from "fuse.js";
import { CircleStop, Monitor, RefreshCw, Search, TerminalSquare, Trash2, X } from "lucide-react";
import { FitAddon } from "@xterm/addon-fit";
import { Terminal } from "@xterm/xterm";
import "@xterm/xterm/css/xterm.css";

import { fetchDiscoveredAgents } from "../ag-ui/discovery";
import type { DiscoveredAgentSummary } from "../ag-ui/types";
import { defaultTmuxTabConfig, type TmuxTabConfig } from "../storage";
import {
  fetchTmuxSessions,
  fetchTmuxStatus,
  openTmuxAttachSocket,
  type TmuxAttachMode,
  type TmuxBridgeStatus,
  type TmuxSessionRow,
  type TmuxSessionsResponse,
} from "../tmux/client";
import { paneRecordOrDefault, useWorkbench } from "../workbenchContext";

interface PanelParams {
  paneId: string;
}

interface JoinedTmuxSession {
  session: TmuxSessionRow;
  houmao?: DiscoveredAgentSummary;
}

type AttachState = "unattached" | "attaching" | "attached" | "disconnected" | "error";

export function TmuxTabPanel(props: IDockviewPanelProps<PanelParams>) {
  const { paneId } = props.params;
  const { storage, updateTmuxTab, removePaneRecord } = useWorkbench();
  const record = paneRecordOrDefault(storage, paneId, "tmux");
  const tmux = record.tmux ?? defaultTmuxTabConfig();
  const terminalHostRef = useRef<HTMLDivElement | null>(null);
  const terminalRef = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const resizeObserverRef = useRef<ResizeObserver | null>(null);
  const [status, setStatus] = useState<TmuxBridgeStatus | null>(null);
  const [sessions, setSessions] = useState<TmuxSessionRow[]>([]);
  const [agents, setAgents] = useState<DiscoveredAgentSummary[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [discoveryError, setDiscoveryError] = useState<string | null>(null);
  const [tmuxError, setTmuxError] = useState<string | null>(null);
  const [attachState, setAttachState] = useState<AttachState>("unattached");
  const [activeSession, setActiveSession] = useState<string | null>(tmux.sessionName ?? null);

  useEffect(() => {
    props.api.setTitle(activeSession ? `tmux ${activeSession}` : "tmux");
  }, [activeSession, props.api]);

  useEffect(() => {
    void refreshSessions();
    return () => {
      closeAttachment();
    };
    // The teardown must close the live socket exactly once for this pane.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const joinedSessions = useMemo(() => joinSessions(sessions, agents), [agents, sessions]);
  const visibleSessions = useMemo(() => {
    const scoped = tmux.houmaoOnly
      ? joinedSessions.filter((session) => session.houmao)
      : joinedSessions;
    const trimmed = query.trim();
    if (!trimmed) {
      return scoped;
    }
    return new Fuse(scoped, {
      threshold: 0.35,
      keys: [
        "session.sessionName",
        "houmao.agent_name",
        "houmao.agent_id",
        "houmao.tool",
        "houmao.backend",
        "houmao.generation_id",
      ],
    })
      .search(trimmed)
      .map((result) => result.item);
  }, [joinedSessions, query, tmux.houmaoOnly]);

  const setTmuxConfig = (next: TmuxTabConfig) => {
    updateTmuxTab(paneId, next);
  };

  const refreshSessions = async () => {
    const controller = new AbortController();
    setLoading(true);
    setTmuxError(null);
    setDiscoveryError(null);
    try {
      const [bridgeStatus, tmuxSessions] = await Promise.all([
        fetchTmuxStatus(controller.signal),
        fetchTmuxSessions(controller.signal),
      ]);
      setStatus(bridgeStatus);
      setSessions(tmuxSessions.sessions);
      if (tmuxSessions.status === "error" || tmuxSessions.status === "unavailable") {
        setTmuxError(tmuxSessions.detail ?? "tmux sessions are unavailable.");
      }
    } catch (error) {
      setTmuxError(errorMessage(error));
      setStatus(null);
      setSessions([]);
    }
    try {
      setAgents(await fetchDiscoveredAgents(storage.discovery.passiveServerUrl, controller.signal));
    } catch (error) {
      setAgents([]);
      setDiscoveryError(errorMessage(error));
    } finally {
      setLoading(false);
    }
  };

  const attach = (sessionName: string, mode: TmuxAttachMode) => {
    const host = terminalHostRef.current;
    if (!host) {
      return;
    }
    closeAttachment();
    setAttachState("attaching");
    setActiveSession(sessionName);
    setTmuxConfig({
      ...tmux,
      sessionName,
      mode,
    });
    host.replaceChildren();

    const terminal = new Terminal({
      convertEol: true,
      cursorBlink: mode === "read-write",
      disableStdin: mode === "read-only",
      fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
      fontSize: 12,
      theme: {
        background: "#11110f",
        foreground: "#eee8d8",
        cursor: "#c8b15e",
        selectionBackground: "#4c5d32",
      },
    });
    const fitAddon = new FitAddon();
    terminal.loadAddon(fitAddon);
    terminal.open(host);
    fitAddon.fit();
    terminalRef.current = terminal;
    fitAddonRef.current = fitAddon;

    const socket = openTmuxAttachSocket();
    socketRef.current = socket;
    socket.addEventListener("open", () => {
      socket.send(
        JSON.stringify({
          type: "attach",
          sessionName,
          mode,
          cols: terminal.cols,
          rows: terminal.rows,
        }),
      );
    });
    socket.addEventListener("message", (event) => {
      const message = parseSocketMessage(event.data);
      if (message.type === "attached") {
        setAttachState("attached");
        terminal.focus();
        return;
      }
      if (message.type === "output" && typeof message.data === "string") {
        terminal.write(message.data);
        return;
      }
      if (message.type === "error") {
        setAttachState("error");
        terminal.writeln(`\r\n[tmux] ${String(message.detail ?? message.code ?? "error")}`);
        return;
      }
      if (message.type === "exit") {
        setAttachState("disconnected");
        terminal.writeln("\r\n[tmux] attachment ended");
      }
    });
    socket.addEventListener("close", () => {
      if (attachState !== "error") {
        setAttachState((current) => (current === "attached" ? "disconnected" : current));
      }
    });
    socket.addEventListener("error", () => {
      setAttachState("error");
      terminal.writeln("\r\n[tmux] WebSocket error");
    });
    if (mode === "read-write") {
      terminal.onData((data) => {
        if (socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: "input", data }));
        }
      });
    }
    resizeObserverRef.current = new ResizeObserver(() => {
      fitAddon.fit();
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "resize", cols: terminal.cols, rows: terminal.rows }));
      }
    });
    resizeObserverRef.current.observe(host);
  };

  const closeAttachment = () => {
    resizeObserverRef.current?.disconnect();
    resizeObserverRef.current = null;
    const socket = socketRef.current;
    socketRef.current = null;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "close" }));
      socket.close(1000, "client detach");
    } else {
      socket?.close();
    }
    terminalRef.current?.dispose();
    terminalRef.current = null;
    fitAddonRef.current?.dispose();
    fitAddonRef.current = null;
    setAttachState((current) => (current === "attached" || current === "attaching" ? "disconnected" : current));
  };

  const closePane = () => {
    closeAttachment();
    removePaneRecord(paneId);
    props.api.close();
  };

  const emptyMessage = tmux.houmaoOnly
    ? discoveryError
      ? "Houmao discovery unavailable for the current filter."
      : "No tmux sessions match discovered Houmao agents."
    : "No local tmux sessions are available.";

  return (
    <section className="tmux-panel" data-testid={`panel-${paneId}`}>
      <header className="pane-header">
        <div>
          <span className={`status-dot ${attachState}`} />
          <strong>{activeSession ? `tmux ${activeSession}` : "tmux"}</strong>
          <span data-testid={`tmux-status-${paneId}`}>
            {loading ? "loading" : status?.status ?? attachState}
          </span>
        </div>
        <div className="icon-row">
          <button title="Refresh tmux sessions" data-testid={`tmux-refresh-${paneId}`} onClick={() => void refreshSessions()}>
            <RefreshCw size={15} />
          </button>
          <button title="Detach tmux tab" data-testid={`tmux-detach-${paneId}`} onClick={closeAttachment}>
            <CircleStop size={15} />
          </button>
          <button title="Close tmux tab" data-testid={`close-${paneId}`} onClick={closePane}>
            <X size={15} />
          </button>
        </div>
      </header>

      <div className="tmux-controls">
        <label>
          <span>Search</span>
          <div className="input-with-icon">
            <Search size={14} />
            <input
              data-testid={`tmux-search-${paneId}`}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="session, agent, backend"
            />
          </div>
        </label>
        <label className="checkbox-row">
          <input
            data-testid={`tmux-houmao-only-${paneId}`}
            type="checkbox"
            checked={tmux.houmaoOnly}
            onChange={(event) => setTmuxConfig({ ...tmux, houmaoOnly: event.target.checked })}
          />
          Houmao agents
        </label>
        <label className="checkbox-row">
          <input
            data-testid={`tmux-read-only-${paneId}`}
            type="checkbox"
            checked={tmux.mode === "read-only"}
            onChange={(event) =>
              setTmuxConfig({ ...tmux, mode: event.target.checked ? "read-only" : "read-write" })
            }
          />
          Read only
        </label>
      </div>

      {(tmuxError || discoveryError) && (
        <div className="tmux-errors" data-testid={`tmux-errors-${paneId}`}>
          {tmuxError ? <span>{tmuxError}</span> : null}
          {discoveryError ? <span>{discoveryError}</span> : null}
        </div>
      )}

      <div className="tmux-body">
        <div className="tmux-session-list" data-testid={`tmux-session-list-${paneId}`}>
          {visibleSessions.length === 0 ? (
            <div className="empty" data-testid={`tmux-empty-${paneId}`}>
              {emptyMessage}
            </div>
          ) : (
            visibleSessions.map((row) => (
              <button
                key={row.session.sessionName}
                className="tmux-session-row"
                data-testid={`tmux-session-${safeTestToken(row.session.sessionName)}`}
                onClick={() => attach(row.session.sessionName, tmux.mode)}
              >
                <TerminalSquare size={16} />
                <span>
                  <strong>{row.session.sessionName}</strong>
                  <small>
                    {row.session.windowCount} windows
                    {row.session.attached ? " attached" : " detached"}
                    {row.houmao ? ` ${row.houmao.agent_name}` : ""}
                  </small>
                </span>
                {row.houmao ? <Monitor size={15} /> : null}
              </button>
            ))
          )}
        </div>
        <div className="tmux-terminal-wrap">
          {attachState === "unattached" ? (
            <div className="tmux-placeholder">
              <TerminalSquare size={24} />
              <span>Select a tmux session</span>
            </div>
          ) : null}
          {tmux.mode === "read-only" && attachState === "attached" ? (
            <span className="read-only-badge" data-testid={`tmux-read-only-state-${paneId}`}>
              read only
            </span>
          ) : null}
          <div ref={terminalHostRef} className="tmux-terminal" data-testid={`tmux-terminal-${paneId}`} />
        </div>
      </div>

      <button className="danger-link" title="Remove tmux tab" onClick={closePane}>
        <Trash2 size={13} />
        Remove
      </button>
    </section>
  );
}

function joinSessions(
  sessions: TmuxSessionRow[],
  agents: DiscoveredAgentSummary[],
): JoinedTmuxSession[] {
  const agentsBySession = new Map(
    agents
      .filter((agent) => agent.tmux_session_name)
      .map((agent) => [agent.tmux_session_name, agent]),
  );
  return sessions.map((session) => ({
    session,
    houmao: agentsBySession.get(session.sessionName),
  }));
}

function parseSocketMessage(value: unknown): Record<string, unknown> {
  if (typeof value !== "string") {
    return {};
  }
  try {
    const parsed = JSON.parse(value) as unknown;
    return parsed && typeof parsed === "object" ? (parsed as Record<string, unknown>) : {};
  } catch {
    return {};
  }
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "tmux request failed.";
}

function safeTestToken(value: string): string {
  return (
    value
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9_.-]+/g, "-")
      .replace(/^-+|-+$/g, "") || "session"
  );
}

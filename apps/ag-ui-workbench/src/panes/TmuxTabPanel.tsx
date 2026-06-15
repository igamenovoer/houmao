import { useEffect, useMemo, useRef, useState } from "react";
import type { IDockviewPanelProps } from "dockview-react";
import Fuse from "fuse.js";
import { ChevronDown, CircleStop, Monitor, RefreshCw, Search, TerminalSquare, X } from "lucide-react";
import { FitAddon } from "@xterm/addon-fit";
import { Terminal } from "@xterm/xterm";
import "@xterm/xterm/css/xterm.css";

import type { DiscoveredAgentSummary } from "../ag-ui/types";
import { useRuntimeDispatch, useRuntimeSelector } from "../runtime/react";
import { selectTmuxPaneRuntime } from "../runtime/selectors";
import { defaultTmuxTabConfig, type TmuxTabConfig } from "../storage";
import { type TmuxAttachMode, type TmuxSessionRow } from "../tmux/client";
import { paneRecordOrDefault, useWorkbench } from "../workbenchContext";

interface PanelParams {
  paneId: string;
}

interface JoinedTmuxSession {
  session: TmuxSessionRow;
  houmao?: DiscoveredAgentSummary;
}

interface Disposable {
  dispose(): void;
}

interface TerminalSize {
  cols: number;
  rows: number;
}

const FIT_SETTLE_DELAYS_MS = [40, 140, 320] as const;

export function TmuxTabPanel(props: IDockviewPanelProps<PanelParams>) {
  const { paneId } = props.params;
  const { storage, updateTmuxTab, removePaneRecord } = useWorkbench();
  const runtimeDispatch = useRuntimeDispatch();
  const runtime = useRuntimeSelector((state) => selectTmuxPaneRuntime(state, paneId));
  const record = paneRecordOrDefault(storage, paneId, "tmux");
  const tmux = record.tmux ?? defaultTmuxTabConfig();
  const terminalHostRef = useRef<HTMLDivElement | null>(null);
  const terminalRef = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const resizeObserverRef = useRef<ResizeObserver | null>(null);
  const fitFrameRef = useRef<number | null>(null);
  const fitTimerRefs = useRef<number[]>([]);
  const refreshFrameRef = useRef<number | null>(null);
  const refreshAgainRef = useRef(false);
  const refreshTextureAtlasRef = useRef(false);
  const terminalDisposablesRef = useRef<Disposable[]>([]);
  const pickerRef = useRef<HTMLDivElement | null>(null);
  const pickerOpenRef = useRef(false);
  const attachStateRef = useRef("unattached");
  const lastMeasuredTerminalSizeRef = useRef<TerminalSize | null>(null);
  const deliveredAttachmentSizeRef = useRef<TerminalSize | null>(null);
  const [query, setQuery] = useState("");
  const [pickerOpen, setPickerOpen] = useState(false);
  const status = runtime?.bridgeStatus ?? null;
  const sessions = runtime?.sessions ?? [];
  const agents = runtime?.agents ?? [];
  const loading = runtime?.loading ?? false;
  const discoveryError = runtime?.discoveryError ?? null;
  const tmuxError = runtime?.tmuxError ?? null;
  const attachState = runtime?.attachState ?? "unattached";
  const activeSession = runtime?.activeSession ?? tmux.sessionName ?? null;

  useEffect(() => {
    attachStateRef.current = attachState;
    if (attachState === "attached") {
      scheduleFit({ settle: true });
      deliverMeasuredSizeToAttachment();
      scheduleTerminalRefresh({ followUpWhenPending: true, resetTextureAtlas: true });
    }
  }, [attachState]);

  useEffect(() => {
    props.api.setTitle(activeSession ? `tmux ${activeSession}` : "tmux");
  }, [activeSession, props.api]);

  useEffect(() => {
    return () => {
      closeAttachment();
      runtimeDispatch({
        type: "pane/disposed",
        paneId,
      });
    };
  }, []);

  useEffect(() => {
    const disposables = [
      props.api.onDidDimensionsChange(() => scheduleFit({ settle: true })),
      props.api.onDidVisibilityChange((event) => {
        if (event.isVisible) {
          scheduleFit({ settle: true });
        }
      }),
    ];
    return () => {
      disposeAll(disposables);
    };
  }, [props.api]);

  useEffect(() => {
    if (!pickerOpen) {
      return;
    }
    const closeOnOutsidePointer = (event: PointerEvent) => {
      const target = event.target;
      if (target instanceof Node && pickerRef.current?.contains(target)) {
        return;
      }
      pickerOpenRef.current = false;
      setPickerOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        pickerOpenRef.current = false;
        setPickerOpen(false);
      }
    };
    document.addEventListener("pointerdown", closeOnOutsidePointer);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsidePointer);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [pickerOpen]);

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

  const refreshSessions = () => {
    runtimeDispatch({
      type: "tmux/refreshRequested",
      paneId,
      passiveServerUrl: storage.discovery.passiveServerUrl,
    });
  };

  const openSessionPicker = () => {
    if (!pickerOpenRef.current) {
      pickerOpenRef.current = true;
      refreshSessions();
    }
    setPickerOpen(true);
  };

  const closeSessionPicker = () => {
    pickerOpenRef.current = false;
    setPickerOpen(false);
  };

  const toggleSessionPicker = () => {
    if (pickerOpenRef.current) {
      closeSessionPicker();
      return;
    }
    openSessionPicker();
  };

  const attach = (sessionName: string, mode: TmuxAttachMode) => {
    const host = terminalHostRef.current;
    if (!host) {
      return;
    }
    closeAttachment();
    attachStateRef.current = "attaching";
    setTmuxConfig({
      ...tmux,
      sessionName,
      mode,
    });
    host.replaceChildren();

    const terminal = new Terminal({
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
    terminalRef.current = terminal;
    fitAddonRef.current = fitAddon;
    terminal.open(host);
    fitAddon.fit();
    scheduleTerminalRefresh({ followUpWhenPending: true, resetTextureAtlas: true });
    setMeasuredTerminalSize({ cols: terminal.cols, rows: terminal.rows });
    deliveredAttachmentSizeRef.current = null;
    terminalDisposablesRef.current = [
      terminal.onScroll(() => scheduleTerminalRefresh()),
      terminal.onWriteParsed(() => scheduleTerminalRefresh({ followUpWhenPending: true })),
      addTerminalWheelRefreshHandler(host),
    ];

    runtimeDispatch({
      type: "tmux/registerOutputSink",
      paneId,
      sink: (data) => {
        terminal.write(data, () => scheduleTerminalRefresh({ followUpWhenPending: true }));
      },
    });
    runtimeDispatch({
      type: "tmux/attachRequested",
      paneId,
      sessionName,
      mode,
      cols: terminal.cols,
      rows: terminal.rows,
    });
    if (mode === "read-write") {
      terminalDisposablesRef.current.push(
        terminal.onData((data) => {
          runtimeDispatch({
            type: "tmux/inputRequested",
            paneId,
            data,
          });
        }),
      );
    }
    resizeObserverRef.current = new ResizeObserver(() => {
      scheduleFit({ settle: true });
    });
    resizeObserverRef.current.observe(host);
    scheduleFit({ settle: true });
  };

  const attachFromPicker = (sessionName: string, mode: TmuxAttachMode) => {
    closeSessionPicker();
    setQuery("");
    attach(sessionName, mode);
  };

  const closeAttachment = () => {
    disposeAll(terminalDisposablesRef.current);
    terminalDisposablesRef.current = [];
    resizeObserverRef.current?.disconnect();
    resizeObserverRef.current = null;
    attachStateRef.current = "unattached";
    if (fitFrameRef.current !== null) {
      window.cancelAnimationFrame(fitFrameRef.current);
      fitFrameRef.current = null;
    }
    clearFitTimers();
    if (refreshFrameRef.current !== null) {
      window.cancelAnimationFrame(refreshFrameRef.current);
      refreshFrameRef.current = null;
    }
    refreshAgainRef.current = false;
    refreshTextureAtlasRef.current = false;
    lastMeasuredTerminalSizeRef.current = null;
    deliveredAttachmentSizeRef.current = null;
    if (terminalHostRef.current) {
      delete terminalHostRef.current.dataset.tmuxCols;
      delete terminalHostRef.current.dataset.tmuxRows;
    }
    runtimeDispatch({
      type: "tmux/detachRequested",
      paneId,
    });
    runtimeDispatch({
      type: "tmux/unregisterOutputSink",
      paneId,
    });
    terminalRef.current?.dispose();
    terminalRef.current = null;
    fitAddonRef.current?.dispose();
    fitAddonRef.current = null;
  };

  function scheduleFit(options: { settle?: boolean } = {}) {
    scheduleFitFrame();
    if (options.settle) {
      scheduleSettledFits();
    }
  }

  function scheduleSettledFits() {
    clearFitTimers();
    for (const delay of FIT_SETTLE_DELAYS_MS) {
      const timer = window.setTimeout(() => {
        fitTimerRefs.current = fitTimerRefs.current.filter((value) => value !== timer);
        scheduleFitFrame();
      }, delay);
      fitTimerRefs.current.push(timer);
    }
  }

  function clearFitTimers() {
    for (const timer of fitTimerRefs.current) {
      window.clearTimeout(timer);
    }
    fitTimerRefs.current = [];
  }

  function scheduleFitFrame() {
    if (fitFrameRef.current !== null) {
      return;
    }
    fitFrameRef.current = window.requestAnimationFrame(() => {
      fitFrameRef.current = null;
      const terminal = terminalRef.current;
      const fitAddon = fitAddonRef.current;
      if (!terminal || !fitAddon) {
        return;
      }
      try {
        fitAddon.fit();
      } catch {
        return;
      }
      scheduleTerminalRefresh({ followUpWhenPending: true, resetTextureAtlas: true });
      const nextSize = { cols: terminal.cols, rows: terminal.rows };
      setMeasuredTerminalSize(nextSize);
      if (attachStateRef.current !== "attached") {
        return;
      }
      deliverMeasuredSizeToAttachment();
    });
  }

  function deliverMeasuredSizeToAttachment() {
    if (attachStateRef.current !== "attached") {
      return;
    }
    const nextSize = lastMeasuredTerminalSizeRef.current;
    if (!nextSize) {
      return;
    }
    deliveredAttachmentSizeRef.current = nextSize;
    runtimeDispatch({
      type: "tmux/resizeRequested",
      paneId,
      cols: nextSize.cols,
      rows: nextSize.rows,
    });
  }

  function setMeasuredTerminalSize(size: TerminalSize) {
    lastMeasuredTerminalSizeRef.current = size;
    const host = terminalHostRef.current;
    if (host) {
      host.dataset.tmuxCols = String(size.cols);
      host.dataset.tmuxRows = String(size.rows);
    }
  }

  function addTerminalWheelRefreshHandler(host: HTMLElement): Disposable {
    const handleWheel = (event: WheelEvent) => {
      if (attachStateRef.current === "attached") {
        scheduleTerminalRefresh({ followUpWhenPending: true });
      }
      const terminal = terminalRef.current;
      if (!terminal || terminal.buffer.active.type !== "alternate" || event.deltaY === 0) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      runtimeDispatch({
        type: "tmux/scrollRequested",
        paneId,
        direction: event.deltaY < 0 ? "up" : "down",
        lines: tmuxWheelLines(event),
      });
    };
    host.addEventListener("wheel", handleWheel, { capture: true, passive: false });
    return {
      dispose: () => host.removeEventListener("wheel", handleWheel, { capture: true }),
    };
  }

  function scheduleTerminalRefresh(
    options: { followUpWhenPending?: boolean; resetTextureAtlas?: boolean } = {},
  ) {
    if (options.resetTextureAtlas) {
      refreshTextureAtlasRef.current = true;
    }
    if (refreshFrameRef.current !== null) {
      if (options.followUpWhenPending) {
        refreshAgainRef.current = true;
      }
      return;
    }
    refreshFrameRef.current = window.requestAnimationFrame(() => {
      refreshFrameRef.current = null;
      const terminal = terminalRef.current;
      if (!terminal) {
        return;
      }
      if (refreshTextureAtlasRef.current) {
        refreshTextureAtlasRef.current = false;
        terminal.clearTextureAtlas();
      }
      terminal.refresh(0, Math.max(0, terminal.rows - 1));
      if (refreshAgainRef.current) {
        refreshAgainRef.current = false;
        scheduleTerminalRefresh();
      }
    });
  }

  const closePane = () => {
    closeAttachment();
    runtimeDispatch({
      type: "pane/disposed",
      paneId,
    });
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
        <div className="tmux-session-picker" ref={pickerRef}>
          <span>Session</span>
          <div className="tmux-combobox">
            <Search size={14} />
            <input
              data-testid={`tmux-search-${paneId}`}
              value={query}
              onFocus={openSessionPicker}
              onClick={openSessionPicker}
              onChange={(event) => {
                setQuery(event.target.value);
                openSessionPicker();
              }}
              placeholder={activeSession ? `Attached: ${activeSession}` : "session, agent, backend"}
              role="combobox"
              aria-expanded={pickerOpen}
              aria-controls={`tmux-session-list-${paneId}`}
            />
            <button
              type="button"
              className="tmux-picker-toggle"
              title="Open tmux session picker"
              data-testid={`tmux-picker-toggle-${paneId}`}
              onClick={toggleSessionPicker}
            >
              <ChevronDown size={15} />
            </button>
          </div>
          {pickerOpen ? (
            <div className="tmux-session-list" data-testid={`tmux-session-list-${paneId}`} id={`tmux-session-list-${paneId}`}>
              {visibleSessions.length === 0 ? (
                <div className="empty" data-testid={`tmux-empty-${paneId}`}>
                  {emptyMessage}
                </div>
              ) : (
                visibleSessions.map((row) => (
                  <button
                    key={row.session.sessionName}
                    type="button"
                    className="tmux-session-row"
                    data-testid={`tmux-session-${safeTestToken(row.session.sessionName)}`}
                    onClick={() => attachFromPicker(row.session.sessionName, tmux.mode)}
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
          ) : null}
        </div>
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

function disposeAll(disposables: Disposable[]): void {
  for (const disposable of disposables) {
    disposable.dispose();
  }
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

function tmuxWheelLines(event: WheelEvent): number {
  if (event.deltaMode === WheelEvent.DOM_DELTA_PAGE) {
    return 25;
  }
  if (event.deltaMode === WheelEvent.DOM_DELTA_LINE) {
    return Math.max(1, Math.min(25, Math.round(Math.abs(event.deltaY))));
  }
  return 5;
}

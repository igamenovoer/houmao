import { useEffect, useMemo, useState, type RefObject } from "react";
import { Activity, Braces, Info, X } from "lucide-react";

import { ToolCallRenderer } from "../ag-ui/componentRenderers";
import type {
  ActivityRecord,
  PaneEventState,
  ToolCallRecord,
  TranscriptMessage,
} from "../ag-ui/reducer";
import type { RawTimelineEntry } from "../ag-ui/types";

type DiagnosticsMode = "message" | "global";

interface MessageDiagnostics {
  message: TranscriptMessage;
  toolCalls: ToolCallRecord[];
  activity: ActivityRecord[];
  custom: ActivityRecord[];
  raw: unknown[];
  stateSnapshot: unknown;
}

interface AgUiDisplaySurfaceProps {
  paneId: string;
  eventState: PaneEventState;
  latestErrors: string[];
  transcriptSurfaceRef?: RefObject<HTMLElement | null>;
  diagnosticsMode?: DiagnosticsMode;
}

export function AgUiDisplaySurface({
  paneId,
  eventState,
  latestErrors,
  transcriptSurfaceRef,
  diagnosticsMode = "message",
}: AgUiDisplaySurfaceProps) {
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null);
  const selectedMessage = useMemo(
    () => eventState.transcript.find((message) => message.id === selectedMessageId) ?? null,
    [eventState.transcript, selectedMessageId],
  );
  const selectedDiagnostics = useMemo(
    () => (selectedMessage ? collectMessageDiagnostics(eventState, selectedMessage) : null),
    [eventState, selectedMessage],
  );
  const showDiagnostics = diagnosticsMode === "global" || selectedDiagnostics !== null;

  useEffect(() => {
    if (diagnosticsMode !== "message" || selectedMessageId === null || selectedMessage) {
      return;
    }
    setSelectedMessageId(null);
  }, [diagnosticsMode, selectedMessage, selectedMessageId]);

  return (
    <>
      {latestErrors.length > 0 ? (
        <div className="error-stack" data-testid={`errors-${paneId}`}>
          {latestErrors.map((error, index) => (
            <div key={`${error}-${index}`}>{error}</div>
          ))}
        </div>
      ) : null}

      <div className={`pane-body ${showDiagnostics ? "diagnostics-visible" : ""}`}>
        <section className="surface" data-testid={`transcript-${paneId}`} ref={transcriptSurfaceRef}>
          <h3>
            <Activity size={14} />
            Transcript
          </h3>
          {eventState.transcript.length === 0 ? <p className="empty">No messages</p> : null}
          {eventState.transcript.map((message) => {
            const token = safeTestToken(message.id);
            const selected = diagnosticsMode === "message" && message.id === selectedMessageId;
            return (
              <article key={message.id} className={`message ${selected ? "selected" : ""}`}>
                <div className="message-heading">
                  {diagnosticsMode === "message" ? (
                    <button
                      type="button"
                      className="message-info-button"
                      data-testid={`message-info-${paneId}-${token}`}
                      aria-label={`Show diagnostics for ${message.role} message ${message.id}`}
                      title="Show message diagnostics"
                      onClick={() => setSelectedMessageId(message.id)}
                    >
                      <Info size={13} />
                    </button>
                  ) : null}
                  <span>{message.role}</span>
                </div>
              <p>{message.content}</p>
            </article>
            );
          })}
          {eventState.toolCalls.map((toolCall) => (
            <ToolCallRenderer
              key={toolCall.id}
              toolCall={toolCall}
              paneId={paneId}
            />
          ))}
        </section>

        {diagnosticsMode === "global" ? (
          <GlobalDiagnostics paneId={paneId} eventState={eventState} />
        ) : selectedDiagnostics ? (
          <MessageDiagnosticsInspector
            paneId={paneId}
            diagnostics={selectedDiagnostics}
            onClose={() => setSelectedMessageId(null)}
          />
        ) : null}
      </div>
    </>
  );
}

function GlobalDiagnostics({
  paneId,
  eventState,
}: {
  paneId: string;
  eventState: PaneEventState;
}) {
  return (
    <section className="surface diagnostics" data-testid={`diagnostics-${paneId}`}>
      <h3>
        <span>
          <Braces size={14} />
          Diagnostics
        </span>
      </h3>
      <details open>
        <summary>State</summary>
        <pre data-testid={`state-${paneId}`}>{formatJson(eventState.stateSnapshot)}</pre>
      </details>
      <details>
        <summary>Activity</summary>
        <pre>{formatJson(eventState.activity)}</pre>
      </details>
      <details>
        <summary>Tool Calls</summary>
        <pre>{formatJson(eventState.toolCalls)}</pre>
      </details>
      <details>
        <summary>Raw</summary>
        <pre data-testid={`raw-${paneId}`}>{formatJson(eventState.raw.map(rawEntryValue))}</pre>
      </details>
    </section>
  );
}

function MessageDiagnosticsInspector({
  paneId,
  diagnostics,
  onClose,
}: {
  paneId: string;
  diagnostics: MessageDiagnostics;
  onClose: () => void;
}) {
  const token = safeTestToken(diagnostics.message.id);
  return (
    <section className="surface diagnostics message-diagnostics" data-testid={`message-diagnostics-${paneId}`}>
      <h3>
        <span>
          <Braces size={14} />
          Message Info
        </span>
        <button
          type="button"
          className="message-diagnostics-close"
          data-testid={`message-diagnostics-close-${paneId}`}
          title="Close message diagnostics"
          onClick={onClose}
        >
          <X size={13} />
        </button>
      </h3>
      <details open>
        <summary>Message</summary>
        <pre>{formatJson(diagnostics.message)}</pre>
      </details>
      <details open>
        <summary>State</summary>
        <div data-testid={`message-state-${paneId}-${token}`}>
          <pre data-testid={`state-${paneId}`}>{formatJson(diagnostics.stateSnapshot)}</pre>
        </div>
      </details>
      <details>
        <summary>Tool Calls</summary>
        <pre>{formatJson(diagnostics.toolCalls)}</pre>
      </details>
      <details>
        <summary>Activity</summary>
        <pre>{formatJson({ activity: diagnostics.activity, custom: diagnostics.custom })}</pre>
      </details>
      <details open>
        <summary>Raw</summary>
        <div data-testid={`message-raw-${paneId}-${token}`}>
          <pre data-testid={`raw-${paneId}`}>{formatJson(diagnostics.raw)}</pre>
        </div>
      </details>
    </section>
  );
}

function collectMessageDiagnostics(
  eventState: PaneEventState,
  message: TranscriptMessage,
): MessageDiagnostics {
  const toolCalls = eventState.toolCalls.filter((toolCall) => toolCall.parentMessageId === message.id);
  const toolCallIds = new Set(toolCalls.map((toolCall) => toolCall.id));
  return {
    message,
    toolCalls,
    activity: eventState.activity.filter((record) =>
      recordLinksToMessage(record, message.id, toolCallIds),
    ),
    custom: eventState.custom.filter((record) => recordLinksToMessage(record, message.id, toolCallIds)),
    raw: eventState.raw
      .filter((entry) => rawEntryLinksToMessage(entry, message.id, toolCallIds))
      .map(rawEntryValue),
    stateSnapshot: eventState.stateSnapshot ?? {},
  };
}

function rawEntryLinksToMessage(
  entry: RawTimelineEntry,
  messageId: string,
  toolCallIds: Set<string>,
): boolean {
  const event = entry.event;
  if (!isRecord(event)) {
    return false;
  }
  if (event.messageId === messageId || event.parentMessageId === messageId) {
    return true;
  }
  if (typeof event.toolCallId === "string" && toolCallIds.has(event.toolCallId)) {
    return true;
  }
  if (!Array.isArray(event.messages)) {
    return false;
  }
  return event.messages.some(
    (message) =>
      isRecord(message) && (message.id === messageId || message.messageId === messageId),
  );
}

function recordLinksToMessage(
  record: ActivityRecord,
  messageId: string,
  toolCallIds: Set<string>,
): boolean {
  return record.id === messageId || valueLinksToMessage(record.content, messageId, toolCallIds, 0);
}

function valueLinksToMessage(
  value: unknown,
  messageId: string,
  toolCallIds: Set<string>,
  depth: number,
): boolean {
  if (depth > 4) {
    return false;
  }
  if (Array.isArray(value)) {
    return value.some((item) => valueLinksToMessage(item, messageId, toolCallIds, depth + 1));
  }
  if (!isRecord(value)) {
    return false;
  }
  if (value.messageId === messageId || value.parentMessageId === messageId) {
    return true;
  }
  if (typeof value.toolCallId === "string" && toolCallIds.has(value.toolCallId)) {
    return true;
  }
  return Object.values(value).some((item) => valueLinksToMessage(item, messageId, toolCallIds, depth + 1));
}

function rawEntryValue(entry: RawTimelineEntry): unknown {
  return entry.event ?? entry.parseError ?? entry.data ?? entry.raw;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function safeTestToken(value: string): string {
  return (
    value
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9_.-]+/g, "-")
      .replace(/^-+|-+$/g, "") || "message"
  );
}

function formatJson(value: unknown): string {
  if (typeof value === "undefined") {
    return "{}";
  }
  return JSON.stringify(value, null, 2);
}

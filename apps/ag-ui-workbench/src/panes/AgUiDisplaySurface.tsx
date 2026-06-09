import { Activity, Braces } from "lucide-react";

import { ToolCallRenderer } from "../ag-ui/componentRenderers";
import type { PaneEventState } from "../ag-ui/reducer";

interface AgUiDisplaySurfaceProps {
  paneId: string;
  eventState: PaneEventState;
  latestErrors: string[];
}

export function AgUiDisplaySurface({ paneId, eventState, latestErrors }: AgUiDisplaySurfaceProps) {
  return (
    <>
      {latestErrors.length > 0 ? (
        <div className="error-stack" data-testid={`errors-${paneId}`}>
          {latestErrors.map((error, index) => (
            <div key={`${error}-${index}`}>{error}</div>
          ))}
        </div>
      ) : null}

      <div className="pane-body">
        <section className="surface" data-testid={`transcript-${paneId}`}>
          <h3>
            <Activity size={14} />
            Transcript
          </h3>
          {eventState.transcript.length === 0 ? <p className="empty">No messages</p> : null}
          {eventState.transcript.map((message) => (
            <article key={message.id} className="message">
              <span>{message.role}</span>
              <p>{message.content}</p>
            </article>
          ))}
          {eventState.toolCalls.map((toolCall) => (
            <ToolCallRenderer key={toolCall.id} toolCall={toolCall} paneId={paneId} />
          ))}
        </section>

        <section className="surface diagnostics">
          <h3>
            <Braces size={14} />
            Diagnostics
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
            <pre data-testid={`raw-${paneId}`}>
              {formatJson(eventState.raw.map((entry) => entry.event ?? entry.parseError ?? entry.data))}
            </pre>
          </details>
        </section>
      </div>
    </>
  );
}

function formatJson(value: unknown): string {
  if (typeof value === "undefined") {
    return "{}";
  }
  return JSON.stringify(value, null, 2);
}

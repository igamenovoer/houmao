import type { TargetConfig } from "../ag-ui/types";

interface TargetFormProps {
  paneId: string;
  target: TargetConfig;
  onChange: (target: TargetConfig) => void;
}

export function TargetForm({ paneId, target, onChange }: TargetFormProps) {
  return (
    <div className="target-form">
      <label>
        <span>Label</span>
        <input
          data-testid={`target-label-${paneId}`}
          value={target.label}
          onChange={(event) => onChange({ ...target, label: event.target.value })}
        />
      </label>
      <label className="target-url">
        <span>AG-UI URL</span>
        <input
          data-testid={`target-url-${paneId}`}
          value={target.url}
          placeholder="http://127.0.0.1:8765/v1/ag-ui"
          onChange={(event) => onChange({ ...target, url: event.target.value })}
        />
      </label>
      <label>
        <span>Thread</span>
        <input
          data-testid={`thread-id-${paneId}`}
          value={target.threadId}
          onChange={(event) => onChange({ ...target, threadId: event.target.value })}
        />
      </label>
    </div>
  );
}

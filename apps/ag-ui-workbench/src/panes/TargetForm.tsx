import { Users } from "lucide-react";

import type { TargetConfig } from "../ag-ui/types";

interface TargetFormProps {
  paneId: string;
  target: TargetConfig;
  onChange: (target: TargetConfig) => void;
  onChooseAgent: () => void;
}

export function TargetForm({ paneId, target, onChange, onChooseAgent }: TargetFormProps) {
  const updateManualTarget = (patch: Partial<TargetConfig>) => {
    onChange({ ...target, ...patch, source: { kind: "manual" } });
  };

  return (
    <div className="target-form">
      <label>
        <span>Label</span>
        <input
          data-testid={`target-label-${paneId}`}
          value={target.label}
          onChange={(event) => updateManualTarget({ label: event.target.value })}
        />
      </label>
      <label className="target-url">
        <span>AG-UI URL</span>
        <input
          data-testid={`target-url-${paneId}`}
          value={target.url}
          placeholder="http://127.0.0.1:8765/v1/ag-ui"
          onChange={(event) => updateManualTarget({ url: event.target.value })}
        />
      </label>
      <label>
        <span>Thread</span>
        <input
          data-testid={`thread-id-${paneId}`}
          value={target.threadId}
          onChange={(event) => updateManualTarget({ threadId: event.target.value })}
        />
      </label>
      <button
        className="target-picker-button"
        title="Choose discovered Houmao agent"
        data-testid={`choose-agent-${paneId}`}
        onClick={onChooseAgent}
      >
        <Users size={15} />
      </button>
    </div>
  );
}

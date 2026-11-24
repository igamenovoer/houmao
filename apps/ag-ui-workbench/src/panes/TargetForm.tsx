import { Users } from "lucide-react";

import type { TargetConfig } from "../ag-ui/types";
import { hasOperatorSession } from "../operatorSession";

interface TargetFormProps {
  paneId: string;
  target: TargetConfig;
  onChange: (target: TargetConfig) => void;
  onChooseAgent: () => void;
}

export function TargetForm({ paneId, target, onChange, onChooseAgent }: TargetFormProps) {
  const updateUrl = (url: string) => {
    onChange({ ...target, url, source: { kind: "manual" }, useOperatorSigner: undefined });
  };

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
          onChange={(event) => updateUrl(event.target.value)}
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
      {hasOperatorSession() ? (
        <label>
          <span>Use operator key</span>
          <input
            type="checkbox"
            checked={target.useOperatorSigner ?? false}
            onChange={(event) => onChange({ ...target, useOperatorSigner: event.target.checked })}
          />
        </label>
      ) : null}
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

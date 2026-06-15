import type { CapabilitiesResponse, HoumaoFeatureFlags } from "../ag-ui/types";

interface CapabilityBadgesProps {
  capabilities: CapabilitiesResponse | null;
}

export function CapabilityBadges({ capabilities }: CapabilityBadgesProps) {
  const features = capabilities?.houmao?.features;
  const flags: Array<[string, boolean]> = [
    ["SSE", featureValue(features, "httpSse", capabilities?.capabilities?.transport?.streaming)],
    ["Text", featureValue(features, "textInputParsing", true)],
    ["State", featureValue(features, "stateSnapshots", capabilities?.capabilities?.state?.snapshots)],
    ["Graphics", featureValue(features, "generatedGraphics", capabilities?.capabilities?.tools?.supported)],
    ["Frontend Tools", featureValue(features, "frontendToolExecution", capabilities?.capabilities?.tools?.clientProvided)],
    ["Deltas", featureValue(features, "stateDeltas", capabilities?.capabilities?.state?.deltas)],
    ["Multimodal", featureValue(features, "multimodalInput", false)],
  ];
  return (
    <div className="capability-grid" data-testid="capability-grid">
      {flags.map(([label, enabled]) => (
        <span key={label} className={enabled ? "capability on" : "capability off"}>
          {label}
        </span>
      ))}
    </div>
  );
}

function featureValue(
  features: Partial<HoumaoFeatureFlags> | undefined,
  key: keyof HoumaoFeatureFlags,
  fallback: boolean | undefined,
): boolean {
  return Boolean(features?.[key] ?? fallback);
}

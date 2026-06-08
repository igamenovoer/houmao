import type { RunAgentInput as CoreRunAgentInput } from "@ag-ui/core";

export type JsonScalar = string | number | boolean | null;
export type JsonValue = JsonScalar | JsonValue[] | { [key: string]: JsonValue };
export type JsonObject = { [key: string]: JsonValue };

export type RunAgentInput = CoreRunAgentInput;

export type TargetSource = ManualTargetSource | DiscoveredTargetSource;

export interface ManualTargetSource {
  kind: "manual";
}

export interface DiscoveredTargetSource {
  kind: "discovered";
  passiveServerUrl: string;
  agentId: string;
  agentName: string;
  generationId?: string;
  tool?: string;
  backend?: string;
}

export interface TargetConfig {
  label: string;
  url: string;
  threadId: string;
  source?: TargetSource;
}

export interface NormalizedAgUiTarget {
  inputUrl: string;
  baseUrl: string;
  capabilitiesUrl: string;
  connectUrl: string;
  runsUrl: string;
  detachUrlTemplate: string;
}

export interface AgUiEvent {
  type: string;
  [key: string]: unknown;
}

export interface RawTimelineEntry {
  id: string;
  receivedAt: string;
  raw: string;
  data?: string;
  event?: AgUiEvent;
  parseError?: string;
}

export interface HoumaoFeatureFlags {
  httpSse: boolean;
  guiConnect: boolean;
  textInputParsing: boolean;
  stateSnapshots: boolean;
  taskRunSubmission: boolean;
  stateDeltas: boolean;
  frontendToolExecution: boolean;
  generatedGraphics: boolean;
  openGenerativeUi: boolean;
  multimodalInput: boolean;
}

export interface CapabilitiesResponse {
  capabilities?: {
    identity?: {
      name?: string;
      type?: string;
      provider?: string;
      metadata?: JsonObject;
    };
    transport?: {
      streaming?: boolean;
      websocket?: boolean;
      httpBinary?: boolean;
      pushNotifications?: boolean;
      resumable?: boolean;
    };
    state?: {
      snapshots?: boolean;
      deltas?: boolean;
      memory?: boolean;
      persistentState?: boolean;
    };
    tools?: {
      supported?: boolean;
      clientProvided?: boolean;
      items?: Array<{ name?: string; description?: string }>;
    };
    multimodal?: {
      input?: Record<string, boolean>;
      output?: Record<string, boolean>;
    };
    custom?: JsonObject;
  };
  houmao?: {
    features?: Partial<HoumaoFeatureFlags>;
    gateway?: JsonObject;
    lifecycleBoundary?: string;
    agentLifecycleManagedByGui?: boolean;
  };
}

export interface GraphicArtifact {
  title: string;
  description?: string | null;
  format: string;
  content?: unknown;
  contentUrl?: string | null;
  altText?: string | null;
  metadata?: Record<string, unknown>;
}

export interface DiscoveredAgentSummary {
  agent_id: string;
  agent_name: string;
  generation_id: string;
  tool: string;
  backend: string;
  tmux_session_name: string;
  manifest_path: string;
  session_root: string;
  has_gateway: boolean;
  has_mailbox: boolean;
  published_at: string;
  lease_expires_at: string;
}

export interface DiscoveredAgentListResponse {
  agents: DiscoveredAgentSummary[];
}

export interface GatewayStatusSubset {
  gateway_host?: string | null;
  gateway_port?: number | null;
  [key: string]: unknown;
}

export interface ResolvedDiscoveredTarget {
  target: TargetConfig;
  agent: DiscoveredAgentSummary;
  gatewayStatus: GatewayStatusSubset;
}

export type AgentPickerRequest =
  | {
      mode: "new-pane";
    }
  | {
      mode: "retarget";
      paneId: string;
    };

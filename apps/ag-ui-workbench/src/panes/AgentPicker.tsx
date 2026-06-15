import { useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, Eye, EyeOff, PanelRightOpen, Plus, RefreshCw, Search, Target, Users, X } from "lucide-react";

import {
  agentRowTestId,
  discoveryErrorMessage,
  fetchDiscoveredAgents,
  resolveDiscoveredAgentTarget,
} from "../ag-ui/discovery";
import type { AgentPickerRequest, DiscoveredAgentSummary, TargetConfig } from "../ag-ui/types";
import type { WatchedTargetRuntime } from "../ag-ui/useWatchedTargets";
import type { WatchedTargetRecord } from "../ag-ui/watchedTargets";
import type { PaneRecord } from "../storage";

interface AgentPickerProps {
  request: AgentPickerRequest | null;
  passiveServerUrl: string;
  panes: Record<string, PaneRecord>;
  watchedTargets: Record<string, WatchedTargetRecord>;
  watchedTargetRuntimes: Record<string, WatchedTargetRuntime>;
  onPassiveServerUrlChange: (url: string) => void;
  onCreateBlankPane: () => void;
  onCreatePane: (target: TargetConfig, options?: AgentPickerApplyOptions) => void;
  onRetargetPane: (paneId: string, target: TargetConfig, options?: AgentPickerApplyOptions) => void;
  onWatchTarget: (target: TargetConfig) => string;
  onUnwatchTarget: (key: string) => void;
  onOpenWatchedTarget: (key: string) => void;
  onClose: () => void;
}

type PickerAction = "new-pane" | "retarget";

interface AgentPickerApplyOptions {
  autoConnect?: boolean;
}

export function AgentPicker({
  request,
  passiveServerUrl,
  panes,
  watchedTargets,
  watchedTargetRuntimes,
  onPassiveServerUrlChange,
  onCreateBlankPane,
  onCreatePane,
  onRetargetPane,
  onWatchTarget,
  onUnwatchTarget,
  onOpenWatchedTarget,
  onClose,
}: AgentPickerProps) {
  const [agents, setAgents] = useState<DiscoveredAgentSummary[]>([]);
  const [filter, setFilter] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [resolvingAgentId, setResolvingAgentId] = useState<string | null>(null);
  const [action, setAction] = useState<PickerAction>("new-pane");
  const [destinationPaneId, setDestinationPaneId] = useState("operator");
  const refreshGenerationRef = useRef(0);

  const paneEntries = useMemo(
    () =>
      Object.values(panes).sort((left, right) => {
        if (left.paneId === "operator") {
          return -1;
        }
        if (right.paneId === "operator") {
          return 1;
        }
        return left.paneId.localeCompare(right.paneId);
      }),
    [panes],
  );

  useEffect(() => {
    if (!request) {
      return;
    }
    if (request.mode === "retarget") {
      setAction("retarget");
      setDestinationPaneId(request.paneId);
    } else {
      setAction("new-pane");
      setDestinationPaneId(paneEntries[0]?.paneId ?? "operator");
    }
    setError("");
    setFilter("");
  }, [paneEntries, request]);

  useEffect(() => {
    if (!request) {
      refreshGenerationRef.current += 1;
      setLoading(false);
      return;
    }
    void refresh();
  }, [passiveServerUrl, request]);

  const filteredAgents = useMemo(() => {
    const needle = filter.trim().toLowerCase();
    if (!needle) {
      return agents;
    }
    return agents.filter((agent) =>
      [agent.agent_id, agent.agent_name, agent.tool, agent.backend, agent.generation_id]
        .filter(Boolean)
        .some((value) => value.toLowerCase().includes(needle)),
    );
  }, [agents, filter]);

  if (!request) {
    return null;
  }

  async function refresh() {
    const refreshGeneration = refreshGenerationRef.current + 1;
    refreshGenerationRef.current = refreshGeneration;
    setLoading(true);
    setError("");
    try {
      const nextAgents = await fetchDiscoveredAgents(passiveServerUrl);
      if (refreshGeneration !== refreshGenerationRef.current) {
        return;
      }
      setAgents(nextAgents);
    } catch (refreshError) {
      if (refreshGeneration !== refreshGenerationRef.current) {
        return;
      }
      setAgents([]);
      setError(discoveryErrorMessage(refreshError));
    } finally {
      if (refreshGeneration === refreshGenerationRef.current) {
        setLoading(false);
      }
    }
  }

  function createBlankPane() {
    onCreateBlankPane();
    onClose();
  }

  async function applyAgent(agent: DiscoveredAgentSummary) {
    setResolvingAgentId(agent.agent_id);
    setError("");
    try {
      const resolved = await resolveDiscoveredAgentTarget(passiveServerUrl, agent);
      if (action === "retarget") {
        onRetargetPane(destinationPaneId, resolved.target, { autoConnect: true });
      } else {
        onCreatePane(resolved.target, { autoConnect: true });
      }
      onClose();
    } catch (resolveError) {
      setError(discoveryErrorMessage(resolveError));
    } finally {
      setResolvingAgentId(null);
    }
  }

  async function watchAgent(agent: DiscoveredAgentSummary) {
    setResolvingAgentId(agent.agent_id);
    setError("");
    try {
      const resolved = await resolveDiscoveredAgentTarget(passiveServerUrl, agent);
      onWatchTarget(resolved.target);
    } catch (resolveError) {
      setError(discoveryErrorMessage(resolveError));
    } finally {
      setResolvingAgentId(null);
    }
  }

  const defaultActionLabel = action === "retarget" ? "Target" : "Open";

  return (
    <div className="picker-backdrop" role="presentation">
      <section className="agent-picker" role="dialog" aria-label="Houmao agents" data-testid="agent-picker">
        <header className="picker-header">
          <div>
            <Users size={17} />
            <strong>Houmao Agents</strong>
          </div>
          <button title="Close agent picker" data-testid="close-agent-picker" onClick={onClose}>
            <X size={15} />
          </button>
        </header>

        <div className="picker-controls">
          <label className="passive-server-field">
            <span>Passive Server</span>
            <input
              data-testid="passive-server-url"
              value={passiveServerUrl}
              placeholder="http://127.0.0.1:9891"
              onChange={(event) => onPassiveServerUrlChange(event.target.value)}
            />
          </label>
          <label>
            <span>Action</span>
            <select
              data-testid="picker-action-mode"
              value={action}
              onChange={(event) => setAction(event.target.value === "retarget" ? "retarget" : "new-pane")}
            >
              <option value="new-pane">New pane</option>
              <option value="retarget">Retarget pane</option>
            </select>
          </label>
          {action === "retarget" ? (
            <label>
              <span>Pane</span>
              <select
                data-testid="picker-pane-select"
                value={destinationPaneId}
                onChange={(event) => setDestinationPaneId(event.target.value)}
              >
                {paneEntries.map((pane) => (
                  <option value={pane.paneId} key={pane.paneId}>
                    {pane.paneId === "operator" ? "Operator" : pane.target.label || pane.paneId}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          <button className="primary" title="Refresh discovered agents" data-testid="refresh-agents" onClick={() => void refresh()}>
            <RefreshCw size={15} />
            Refresh
          </button>
          <button title="New manual agent pane" data-testid="new-agent-pane" onClick={createBlankPane}>
            <Plus size={15} />
            New
          </button>
        </div>

        <label className="agent-filter">
          <span>
            <Search size={13} />
            Filter
          </span>
          <input
            data-testid="agent-filter"
            value={filter}
            placeholder="name, id, tool, backend"
            onChange={(event) => setFilter(event.target.value)}
          />
        </label>

        {error ? (
          <div className="picker-error" data-testid="picker-error">
            <AlertTriangle size={14} />
            {error}
          </div>
        ) : null}

        <div className="agent-list" data-testid="agent-list">
          {loading ? <div className="agent-empty">Loading agents</div> : null}
          {!loading && filteredAgents.length === 0 ? <div className="agent-empty">No agents</div> : null}
          {filteredAgents.map((agent) => {
            const rowBusy = resolvingAgentId === agent.agent_id;
            const watchedKey = watchedKeyForAgent(watchedTargets, agent);
            const watchStatus = watchedKey ? watchedTargetRuntimes[watchedKey]?.status || "watched" : "unwatched";
            return (
              <article
                className={`agent-row ${agent.has_gateway ? "" : "agent-row-muted"}`}
                data-testid={agentRowTestId(agent)}
                key={`${agent.agent_id}-${agent.generation_id}`}
                onDoubleClick={() => void applyAgent(agent)}
              >
                <div className="agent-main">
                  <strong>{agent.agent_name}</strong>
                  <span>{agent.agent_id}</span>
                </div>
                <div className="agent-meta">
                  <span>{agent.tool}</span>
                  <span>{agent.backend}</span>
                  <span>{agent.tmux_session_name}</span>
                </div>
                <div className="agent-badges">
                  <span className={agent.has_gateway ? "badge-ok" : "badge-off"}>
                    {agent.has_gateway ? "gateway" : "no gateway"}
                  </span>
                  <span className={agent.has_mailbox ? "badge-ok" : "badge-off"}>
                    {agent.has_mailbox ? "mailbox" : "no mailbox"}
                  </span>
                  <span className={watchedKey ? "badge-ok" : "badge-off"} data-testid={`watch-state-${agent.agent_id}`}>
                    {watchStatus}
                  </span>
                </div>
                {watchedKey ? (
                  <>
                    <button
                      title={`Open watched ${agent.agent_name}`}
                      data-testid={`open-watched-agent-${agent.agent_id}`}
                      disabled={rowBusy}
                      onClick={() => onOpenWatchedTarget(watchedKey)}
                    >
                      <PanelRightOpen size={14} />
                      Open
                    </button>
                    <button
                      title={`Unwatch ${agent.agent_name}`}
                      data-testid={`unwatch-agent-${agent.agent_id}`}
                      disabled={rowBusy}
                      onClick={() => onUnwatchTarget(watchedKey)}
                    >
                      <EyeOff size={14} />
                      Unwatch
                    </button>
                  </>
                ) : (
                  <button
                    title={`Watch ${agent.agent_name}`}
                    data-testid={`watch-agent-${agent.agent_id}`}
                    disabled={rowBusy}
                    onClick={() => void watchAgent(agent)}
                  >
                    <Eye size={14} />
                    {rowBusy ? "Resolving" : "Watch"}
                  </button>
                )}
                <button
                  title={`${defaultActionLabel} ${agent.agent_name}`}
                  data-testid={`select-agent-${agent.agent_id}`}
                  disabled={rowBusy}
                  onClick={() => void applyAgent(agent)}
                >
                  {action === "retarget" ? <Target size={14} /> : <Plus size={14} />}
                  {rowBusy ? "Resolving" : defaultActionLabel}
                </button>
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}

function watchedKeyForAgent(
  watchedTargets: Record<string, WatchedTargetRecord>,
  agent: DiscoveredAgentSummary,
): string | null {
  for (const [key, record] of Object.entries(watchedTargets)) {
    const source = record.target.source;
    if (source?.kind !== "discovered") {
      continue;
    }
    if (source.agentId === agent.agent_id) {
      return key;
    }
  }
  return null;
}

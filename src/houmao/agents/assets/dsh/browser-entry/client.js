/** Select the existing native session before delivering the Workspace baseline. */
window.__ModuleLoader__.load({
  id: '@houmao/dsh-browser-entry',
  factory() {
    /** Verify the owner binding after both catalogs have arrived. */
    async function targetIsCurrent(target, signal) {
      const method = 'managed/v1/state';
      const rpcId = crypto.randomUUID();
      const response = await fetch(`/houmao/${method}`, {
        method: 'POST',
        credentials: 'same-origin',
        cache: 'no-store',
        redirect: 'error',
        headers: {'content-type': 'application/json'},
        body: JSON.stringify({type: 'client-request', rpcId, method, payload: {protocol_version: 1}}),
        signal,
      });
      if (!response.ok) return false;
      const envelope = await response.json();
      const state = envelope?.result?.value;
      return envelope?.type === 'server-response' && envelope.rpcId === rpcId && envelope.result?.ok === true
        && state?.protocol_version === 1 && state.available === true
        && state.identity?.native_session_id === target.sessionId
        && state.identity?.agent_incarnation === target.incarnation
        && state.browser_workspace_id === target.workspaceId;
    }

    function apply(ctx) {
      const gate = globalThis.__HOUMAO_DSH_BROWSER_GATE__;
      const target = globalThis.__HOUMAO_DSH_BROWSER_ENTRY__;
      if (gate === undefined || !gate.pending) return;
      ctx.effect(() => {
        const lifetime = new AbortController();
        let checking = false;
        const select = async () => {
          if (checking || !gate.pending || !gate.membershipReady) return;
          const sessions = ctx.sessions.list.getSnapshot();
          if (sessions.phase !== 'ready') return;
          if (sessions.byId[target.sessionId] === undefined) {
            gate.fail();
            return;
          }
          checking = true;
          try {
            const current = await targetIsCurrent(target, lifetime.signal);
            if (lifetime.signal.aborted || !gate.pending) return;
            if (!current) { gate.fail(); return; }
            if (!gate.membershipReady) return;
            ctx.uiWorkspace.openSession(target.sessionId);
            const selected = ctx.sessions.list.getSnapshot().byId[target.sessionId];
            if (selected?.retainedBy.mainView === 1) gate.release();
            else gate.fail();
          } catch {
            if (!lifetime.signal.aborted) gate.fail();
          } finally {
            checking = false;
          }
        };
        let scheduled = false;
        const schedule = () => {
          if (scheduled) return;
          scheduled = true;
          queueMicrotask(() => {
            scheduled = false;
            if (!gate.pending) stop();
            else if (!stopped) void select();
          });
        };
        let stopped = false;
        const stopSessions = ctx.sessions.list.subscribe(schedule);
        const stopMembership = gate.subscribe(schedule);
        const stop = () => {
          if (stopped) return;
          stopped = true;
          lifetime.abort();
          stopSessions();
          stopMembership();
        };
        schedule();
        return stop;
      }, 'houmao: select the managed agent session');
    }
    return {name: 'houmao-dsh-browser-entry', inject: ['sessions', 'uiWorkspace'], apply};
  },
});

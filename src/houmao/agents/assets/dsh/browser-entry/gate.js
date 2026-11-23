/** Defer the marked tab's Workspace catalog until exact native selection. */
(() => {
  const entry = new URLSearchParams(location.hash.slice(1));
  if (!entry.has('houmao-entry')) return;

  const target = globalThis.__HOUMAO_DSH_BROWSER_ENTRY__;
  const transport = globalThis.__DSH_TRANSPORT__;
  const streams = new Set();
  const subscribers = new Set();
  const frameLimit = 128;
  const bufferLimit = 4_194_304;
  let state = 'pending';
  let bufferedFrames = 0;
  let bufferedSize = 0;
  const timeout = setTimeout(fail, 15_000);

  function notify() {
    for (const subscriber of subscribers) subscriber();
  }

  function fail() {
    if (state !== 'pending') return;
    state = 'failed';
    clearTimeout(timeout);
    for (const stream of streams) stream.reject();
    notify();
    subscribers.clear();
    const show = () => {
      const dialog = document.createElement('dialog');
      dialog.setAttribute('aria-label', 'Managed session unavailable');
      const message = document.createElement('p');
      message.textContent = 'The managed session could not be opened. Open it again from the Houmao gateway.';
      dialog.append(message);
      dialog.addEventListener('cancel', event => event.preventDefault());
      document.body.append(dialog);
      dialog.showModal();
    };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', show, {once: true});
    else show();
  }

  function release() {
    if (state !== 'pending') return;
    try {
      history.replaceState(history.state, '', location.pathname + location.search);
    } catch {
      fail();
      return;
    }
    state = 'released';
    clearTimeout(timeout);
    for (const stream of streams) stream.deliver();
    notify();
    subscribers.clear();
  }

  globalThis.__HOUMAO_DSH_BROWSER_GATE__ = {
    get pending() { return state === 'pending'; },
    get membershipReady() { return [...streams].some(stream => stream.hasBaseline); },
    subscribe(listener) {
      subscribers.add(listener);
      return () => subscribers.delete(listener);
    },
    fail,
    release,
  };

  function readFrame(data) {
    if (typeof data !== 'string') return undefined;
    try { return JSON.parse(data); } catch { return undefined; }
  }

  function validWorkspace(workspace) {
    return Array.isArray(workspace?.sessionIds) && workspace.sessionIds.includes(target.sessionId);
  }

  function checkMembership(stream, value) {
    if (!stream.hasBaseline && value?.type !== 'baseline') return false;
    switch (value?.type) {
      case 'baseline':
      case 'replace': {
        const snapshot = value.value;
        if (!Array.isArray(snapshot?.items) || !Array.isArray(snapshot.archivedSessionIds)
          || snapshot.archivedSessionIds.includes(target.sessionId)) return false;
        const workspace = snapshot.items.find(item => item?.workspaceId === target.workspaceId);
        if (!validWorkspace(workspace)) return false;
        if (value.type === 'baseline') stream.hasBaseline = true;
        return true;
      }
      case 'upsert':
        return typeof value.workspace?.workspaceId === 'string'
          && (value.workspace.workspaceId !== target.workspaceId || validWorkspace(value.workspace));
      case 'remove':
        return typeof value.workspaceId === 'string' && value.workspaceId !== target.workspaceId;
      case 'archived':
        return Array.isArray(value.archivedSessionIds) && !value.archivedSessionIds.includes(target.sessionId);
      case 'order':
      case 'pinned':
        return true;
      default:
        return false;
    }
  }

  /** Keep unrelated DSH streams on their established carrier. */
  function createWebSocket(url) {
    const socket = transport?.createWebSocket?.(url) ?? new WebSocket(url);
    const destination = new URL(url);
    if (destination.host !== location.host || destination.pathname !== '/api/remote.mux'
      || destination.protocol !== (location.protocol === 'https:' ? 'wss:' : 'ws:')
      || state === 'released') return socket;

    const events = new EventTarget();
    const workspaceStreams = new Map();
    const rejectedStreams = new Set();
    const emit = data => events.dispatchEvent(new MessageEvent('message', {data}));
    socket.addEventListener('open', () => events.dispatchEvent(new Event('open')));
    socket.addEventListener('error', () => events.dispatchEvent(new Event('error')));
    socket.addEventListener('close', () => {
      for (const stream of workspaceStreams.values()) stream.clear();
      rejectedStreams.clear();
      events.dispatchEvent(new Event('close'));
    });

    function track(id) {
      const frames = [];
      const stream = {
        hasBaseline: false,
        sent: false,
        buffer(data) {
          frames.push(data);
          bufferedSize += data.length;
          bufferedFrames++;
        },
        clear() {
          bufferedFrames -= frames.length;
          for (const data of frames) bufferedSize -= data.length;
          frames.length = 0;
          workspaceStreams.delete(id);
          streams.delete(stream);
        },
        deliver() {
          const batch = frames.slice();
          stream.clear();
          if (socket.readyState === WebSocket.OPEN) for (const data of batch) emit(data);
        },
        reject() {
          stream.clear();
          if (stream.sent) {
            rejectedStreams.add(id);
            if (socket.readyState === WebSocket.OPEN) {
              try { socket.send(JSON.stringify({type: 'cancel', streamId: id})); }
              catch { /* Socket teardown will release the native stream. */ }
            }
          }
          queueMicrotask(() => {
            if (socket.readyState === WebSocket.OPEN) emit(JSON.stringify({
              type: 'error', streamId: id,
              error: {code: 'gateway/internal', message: 'Managed session unavailable', details: {}},
            }));
          });
        },
      };
      workspaceStreams.set(id, stream);
      streams.add(stream);
      return stream;
    }

    socket.addEventListener('message', event => {
      if (state === 'released') { emit(event.data); return; }
      const frame = readFrame(event.data);
      if (rejectedStreams.has(frame?.streamId)) return;
      if (state === 'failed') { emit(event.data); return; }
      const stream = workspaceStreams.get(frame?.streamId);
      if (stream === undefined) { emit(event.data); return; }
      if (frame.type === 'error' || frame.type === 'end') {
        stream.clear();
        emit(event.data);
        return;
      }
      if (frame.type !== 'item' || !checkMembership(stream, frame.value)
        || bufferedFrames >= frameLimit || bufferedSize + event.data.length > bufferLimit) {
        fail();
        return;
      }
      stream.buffer(event.data);
      notify();
    });

    return {
      get readyState() { return socket.readyState; },
      addEventListener: events.addEventListener.bind(events),
      removeEventListener: events.removeEventListener.bind(events),
      close: socket.close.bind(socket),
      send(data) {
        if (state === 'released') { socket.send(data); return; }
        const frame = readFrame(data);
        if (frame?.type === 'open' && frame.endpoint === 'workspace/follow') {
          if (typeof frame.streamId !== 'string' || workspaceStreams.has(frame.streamId)) {
            fail();
            return;
          }
          const stream = track(frame.streamId);
          if (state === 'failed') { stream.reject(); return; }
          if (streams.size > 16) { fail(); return; }
          stream.sent = true;
        } else if (frame?.type === 'cancel') workspaceStreams.get(frame.streamId)?.clear();
        socket.send(data);
      },
    };
  }

  globalThis.__DSH_TRANSPORT__ = {...transport, createWebSocket};
  globalThis.addEventListener('pagehide', fail, {once: true});
  if (entry.getAll('houmao-entry').length !== 1 || target?.incarnation !== entry.get('houmao-entry')
    || typeof target.workspaceId !== 'string' || !target.workspaceId
    || typeof target.sessionId !== 'string' || !target.sessionId) fail();
})();

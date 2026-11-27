/** Exercise the shipped browser entry module without network, DOM, or tmux fixtures. */

const [asset, parameters] = process.argv.slice(2);
const scenario = JSON.parse(parameters);
const requests = [];
const sockets = [];
const frames = [];
const replaced = [];
const elements = {
  "terminal-viewport": { dataset: { mode: "interact", entryPath: scenario.entryPath } },
  terminal: {},
  connection: {},
  restart: { hidden: true, href: scenario.entryPath },
};

globalThis.self = globalThis;
globalThis.window = { addEventListener() {} };
globalThis.document = { getElementById: (name) => elements[name] };
globalThis.location = new URL(scenario.url);
globalThis.history = { replaceState: (_state, _title, path) => replaced.push(path) };
globalThis.fetch = async (url, options) => {
  requests.push({ url, ...options });
  return new Response(scenario.receipt ? JSON.stringify(scenario.receipt) : null, {
    status: scenario.status,
  });
};
globalThis.WebSocket = class {
  static OPEN = 1;
  readyState = WebSocket.OPEN;

  constructor(url) {
    sockets.push(url.href);
  }

  addEventListener(event, callback) {
    if (event === "open") callback();
  }

  send(frame) {
    frames.push(JSON.parse(frame));
  }
};

await import(asset);
console.log(JSON.stringify({
  requests,
  sockets,
  frames,
  replaced,
  message: elements.connection.textContent,
  action: elements.restart.href,
}));
process.exit(0);

import { startWorkbenchServer, type WorkbenchServerMode } from "./app";

interface CliOptions {
  host?: string;
  port?: number;
  mode: WorkbenchServerMode;
}

const options = parseArgs(process.argv.slice(2));
const server = await startWorkbenchServer(options);

console.log(`Houmao AG-UI workbench listening at ${server.url}`);

const shutdown = async () => {
  await server.close();
};

process.once("SIGINT", () => {
  void shutdown().then(() => process.exit(0));
});
process.once("SIGTERM", () => {
  void shutdown().then(() => process.exit(0));
});

function parseArgs(args: string[]): CliOptions {
  const options: CliOptions = {
    mode: process.env.NODE_ENV === "production" ? "static" : "development",
  };
  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === "--dev") {
      options.mode = "development";
    } else if (arg === "--static" || arg === "--production") {
      options.mode = "static";
    } else if (arg === "--test") {
      options.mode = "test";
    } else if (arg === "--host" && args[index + 1]) {
      options.host = args[index + 1];
      index += 1;
    } else if (arg.startsWith("--host=")) {
      options.host = arg.slice("--host=".length);
    } else if (arg === "--port" && args[index + 1]) {
      options.port = parsePort(args[index + 1]);
      index += 1;
    } else if (arg.startsWith("--port=")) {
      options.port = parsePort(arg.slice("--port=".length));
    }
  }
  return options;
}

function parsePort(value: string): number {
  const port = Number.parseInt(value, 10);
  if (!Number.isInteger(port) || port <= 0) {
    throw new Error(`Invalid port: ${value}`);
  }
  return port;
}

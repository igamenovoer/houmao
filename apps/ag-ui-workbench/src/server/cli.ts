import { startWorkbenchServer, type WorkbenchServerMode } from "./app";
import { readOperatorConfig } from "./operatorSigner";

interface CliOptions {
  host?: string;
  port?: number;
  mode: WorkbenchServerMode;
  operatorConfigPath?: string;
}

const options = parseArgs(process.argv.slice(2));
const server = await startWorkbenchServer({
  ...options,
  operatorSignerConfig: options.operatorConfigPath
    ? await readOperatorConfig(options.operatorConfigPath)
    : undefined,
});

console.log(`Houmao AG-UI workbench listening at ${server.url}`);
if (server.operatorLaunchUrl) {
  console.log(`Open the one-use operator URL within two minutes: ${server.operatorLaunchUrl}`);
}

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
    } else if (arg === "--operator-config") {
      const filename = args[++index];
      if (!filename || filename.startsWith("-")) {
        throw new Error("--operator-config requires an owner-private configuration file.");
      }
      options.operatorConfigPath = filename;
    } else if (arg.startsWith("--operator-config=")) {
      options.operatorConfigPath = arg.slice("--operator-config=".length);
      if (!options.operatorConfigPath) {
        throw new Error("--operator-config requires an owner-private configuration file.");
      }
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

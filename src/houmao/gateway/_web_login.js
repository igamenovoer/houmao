function shellQuote(value) {
  return "'" + value.replaceAll("'", "'\"'\"'") + "'";
}

function challengeBytes(value) {
  const base64 = value.replaceAll("-", "+").replaceAll("_", "/");
  const bytes = Uint8Array.from(atob(base64), (character) => character.charCodeAt(0));
  return new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(bytes);
}

export function signingCommand(attempt, keyPath, origin, limits) {
  if (!/^[A-Za-z0-9_-]+$/.test(attempt.attempt_id)) {
    throw new Error("Invalid login attempt");
  }
  const prove = new URL("/v1/web/login/" + attempt.attempt_id + "/prove", origin);
  const namespace = shellQuote(limits.namespace);
  const challenge = shellQuote(challengeBytes(attempt.challenge));
  let signAndSubmit;
  if (keyPath) {
    const path = shellQuote(keyPath.startsWith("/") ? keyPath : "./" + keyPath);
    signAndSubmit = `  proof=$(printf '%s' ${challenge} | ssh-keygen -Y sign -n ${namespace} -f ${path}) || denied
  printf '%s\\n' "$proof" | submit`;
  } else {
    signAndSubmit = `  umask 077
  scratch=$(mktemp -d) || denied
  trap 'rm -f "$scratch/identity.pub" "$scratch/proofs"; rmdir "$scratch"' 0
  trap 'exit 1' HUP INT TERM
  ssh-add -L 2>/dev/null | {
    count=0
    while IFS=' ' read -r kind key comment; do
      case "$kind" in
        ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp256|ecdsa-sha2-nistp384|ecdsa-sha2-nistp521) ;;
        *) continue ;;
      esac
      count=$((count + 1))
      [ "$count" -le ${limits.signatureLimit} ] || denied
      printf '%s %s\\n' "$kind" "$key" > "$scratch/identity.pub" || denied
      proof=$(printf '%s' ${challenge} | ssh-keygen -Y sign -U -n ${namespace} -f "$scratch/identity.pub" 2>/dev/null) || continue
      printf '%s\\n' "$proof" >> "$scratch/proofs" || denied
    done
    [ -s "$scratch/proofs" ] || denied
    [ "$(wc -c < "$scratch/proofs")" -le ${limits.proofLimit} ] || denied
    submit < "$scratch/proofs"
  }`;
  }
  return `(
  denied() {
    printf '%s\\n' 'Login approval failed. Select an enrolled key file or start a new login.' >&2
    exit 1
  }
  submit() {
    code=$(curl -q --noproxy '*' --proto '=http' --silent --output /dev/null \\
      --connect-timeout 5 --max-time 15 --write-out '%{http_code}' \\
      --request POST --header 'Content-Type: text/plain' --data-binary @- ${shellQuote(prove.href)}) || denied
    case "$code" in
      2??) printf '%s\\n' 'Login approved. Return to the browser.' ;;
      *) denied ;;
    esac
  }
${signAndSubmit}
)`;
}

function post(path, headers) {
  return fetch(path, {
    method: "POST",
    mode: "same-origin",
    cache: "no-store",
    credentials: "omit",
    redirect: "error",
    headers,
  });
}

function entryUrl(ticket) {
  const url = new URL(ticket.url);
  if (
    url.origin !== location.origin ||
    url.username || url.password || url.hash ||
    url.pathname !== "/v1/web/enter" ||
    url.searchParams.size !== 1 ||
    !url.searchParams.get("ticket")
  ) {
    throw new Error("Invalid entry URL");
  }
  return url.href;
}

export function initializeWebLogin() {
  const limits = document.getElementById("web-login").dataset;
  const keyPath = document.getElementById("key-path");
  const start = document.getElementById("start-login");
  const commandSection = document.getElementById("command-section");
  const expiry = document.getElementById("approval-expiry");
  const command = document.getElementById("signing-command");
  const copy = document.getElementById("copy-command");
  const copyStatus = document.getElementById("copy-status");
  const status = document.getElementById("login-status");
  let attempt;
  document.getElementById("gateway-address").textContent = location.origin;

  function refreshCommand() {
    if (attempt) {
      command.value = signingCommand(attempt, keyPath.value, location.origin, limits);
      copyStatus.textContent = "";
    }
  }

  async function waitForApproval() {
    const path = "/v1/web/login/" + attempt.attempt_id + "/claim";
    const headers = { "X-Houmao-Web-Claim": attempt.claim_secret };
    for (;;) {
      const result = await post(path, headers);
      if (result.status === 200) {
        location.replace(entryUrl(await result.json()));
        return;
      }
      if (result.status !== 202) {
        throw new Error("Login unavailable");
      }
      await new Promise((resolve) => setTimeout(resolve, 750));
    }
  }

  start.addEventListener("click", async () => {
    start.disabled = true;
    status.textContent = "Starting login…";
    try {
      const result = await post("/v1/web/login");
      if (!result.ok) {
        throw new Error("Login unavailable");
      }
      attempt = await result.json();
      refreshCommand();
      expiry.dateTime = attempt.expires_at_utc;
      expiry.textContent = new Date(attempt.expires_at_utc).toLocaleTimeString();
      commandSection.hidden = false;
      status.textContent = "Waiting for terminal approval…";
      await waitForApproval();
    } catch {
      attempt = undefined;
      command.value = "";
      commandSection.hidden = true;
      status.textContent = "Login ended. Start a new login to try again.";
      start.disabled = false;
    }
  });
  keyPath.addEventListener("input", refreshCommand);
  copy.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(command.value);
      copyStatus.textContent = "Command copied.";
    } catch {
      command.focus();
      command.select();
      copyStatus.textContent = "Copy the selected command.";
    }
  });
}

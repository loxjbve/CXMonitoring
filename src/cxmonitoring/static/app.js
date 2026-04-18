const state = {
  snapshot: null,
  eventSource: null,
  lastHeartbeatAt: 0,
};

const elements = {
  taskTitle: document.getElementById("task-title"),
  heroCopy: document.getElementById("hero-copy"),
  connectionPill: document.getElementById("connection-pill"),
  statusPill: document.getElementById("status-pill"),
  updatedAt: document.getElementById("updated-at"),
  cwd: document.getElementById("cwd"),
  collaborationMode: document.getElementById("collaboration-mode"),
  progressText: document.getElementById("progress-text"),
  promptText: document.getElementById("prompt-text"),
  commandSummary: document.getElementById("command-summary"),
  commandStatus: document.getElementById("command-status"),
  commandDuration: document.getElementById("command-duration"),
  toolSummary: document.getElementById("tool-summary"),
  toolName: document.getElementById("tool-name"),
  toolStatus: document.getElementById("tool-status"),
  tokenStats: document.getElementById("token-stats"),
  timelineList: document.getElementById("timeline-list"),
  emptyState: document.getElementById("empty-state"),
  staleBanner: document.getElementById("stale-banner"),
};

async function bootstrap() {
  initDrawer();

  try {
    const response = await fetch("/api/current", { cache: "no-store" });
    if (response.ok) {
      const snapshot = await response.json();
      updateSnapshot(snapshot);
    }
  } catch (error) {
    console.error("Failed to fetch current snapshot", error);
  }

  connectStream();
  window.setInterval(checkStaleness, 1000);
}

function connectStream() {
  const source = new EventSource("/api/stream");
  state.eventSource = source;

  source.onopen = () => {
    setConnectionState(true);
    state.lastHeartbeatAt = Date.now();
  };

  source.onerror = () => {
    setConnectionState(false);
  };

  source.addEventListener("snapshot", (event) => {
    state.lastHeartbeatAt = Date.now();
    updateSnapshot(JSON.parse(event.data));
  });

  source.addEventListener("timeline", (event) => {
    state.lastHeartbeatAt = Date.now();
    const entry = JSON.parse(event.data);
    if (!state.snapshot) {
      return;
    }
    const timeline = Array.isArray(state.snapshot.timeline) ? state.snapshot.timeline.slice() : [];
    timeline.push(entry);
    state.snapshot.timeline = timeline.slice(-20);
    renderTimeline();
  });

  source.addEventListener("thread-switched", () => {
    state.lastHeartbeatAt = Date.now();
  });

  source.addEventListener("heartbeat", () => {
    state.lastHeartbeatAt = Date.now();
    setConnectionState(true);
  });
}

function updateSnapshot(snapshot) {
  state.snapshot = snapshot;
  renderSnapshot();
}

function renderSnapshot() {
  const snapshot = state.snapshot || {};
  const hasThread = Boolean(snapshot.thread_id);

  elements.taskTitle.textContent = hasThread
    ? snapshot.title || "Untitled Codex task"
    : "Looking for an active Codex task";

  elements.heroCopy.textContent = hasThread
    ? snapshot.last_agent_message || "Waiting for a visible Codex progress message."
    : "This page follows the latest active Codex VS Code task running on this machine.";

  setStatus(snapshot.status || "idle");
  elements.updatedAt.textContent = snapshot.updated_at
    ? `Updated ${formatTime(snapshot.updated_at)}`
    : "No updates yet";
  elements.cwd.textContent = snapshot.cwd || "Waiting for data";
  elements.collaborationMode.textContent = snapshot.collaboration_mode || "-";
  elements.progressText.textContent =
    snapshot.last_agent_message || "No active Codex task detected.";
  elements.promptText.textContent = snapshot.last_user_message || "-";

  const command = snapshot.last_command || {};
  elements.commandSummary.textContent = command.summary || "No command seen yet.";
  elements.commandStatus.textContent = command.status
    ? `Status: ${command.status}`
    : "Status: -";
  elements.commandDuration.textContent =
    typeof command.duration_seconds === "number"
      ? `Duration: ${command.duration_seconds.toFixed(2)}s`
      : "Duration: -";

  const activeTool = snapshot.active_tool || {};
  elements.toolSummary.textContent =
    snapshot.last_tool_output_summary || activeTool.summary || "No tool activity yet.";
  elements.toolName.textContent = activeTool.name
    ? `Tool: ${activeTool.name}`
    : "Tool: -";
  elements.toolStatus.textContent = activeTool.status
    ? `State: ${activeTool.status}`
    : "State: -";

  renderTokenStats(snapshot.token_usage || null);
  renderTimeline();
  elements.emptyState.classList.toggle("hidden", hasThread);
}

function renderTokenStats(tokenUsage) {
  const values = tokenUsage || {};
  const items = [
    ["Total", formatNumber(values.total_tokens)],
    ["Input", formatNumber(values.input_tokens)],
    ["Output", formatNumber(values.output_tokens)],
    ["Reasoning", formatNumber(values.reasoning_output_tokens)],
  ];

  elements.tokenStats.innerHTML = items
    .map(
      ([label, value]) =>
        `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`
    )
    .join("");
}

function renderTimeline() {
  const snapshot = state.snapshot || {};
  const timeline = Array.isArray(snapshot.timeline) ? snapshot.timeline : [];
  
  elements.timelineList.innerHTML = timeline
    .map((entry) => {
      const kindStr = (entry.kind || entry.label || "").toLowerCase();
      const isUser = kindStr.includes("user") || kindStr === "prompt";
      const isTool = kindStr.includes("tool") || kindStr.includes("action") || kindStr.includes("command") || kindStr.includes("step");
      const isDiff = kindStr.includes("diff") || kindStr.includes("edit") || kindStr.includes("code");
      
      if (isUser) {
        return "";
      }
      
      const label = escapeHtml(entry.label || entry.kind || "Event");
      const time = escapeHtml(formatTime(entry.ts));
      const summary = escapeHtml(entry.summary || "");

      if (isTool) {
        return `
          <div class="message ai">
            <div class="step-indicator">
              <div class="step-spinner"></div>
              <span>${label}: ${summary}</span>
              <span class="timestamp" style="margin-left: auto;">${time}</span>
            </div>
          </div>
        `;
      } else if (isDiff) {
        return `
          <div class="message ai">
            <div class="message-header">
              <span class="message-sender">Codex</span>
              <span class="timestamp">${time}</span>
            </div>
            <div class="diff-block">
              <div class="diff-header">
                <span>${label}</span>
                <div class="diff-actions">
                  <button class="diff-btn">Reject</button>
                  <button class="diff-btn apply">Apply</button>
                </div>
              </div>
              <div class="diff-content">
                <div class="diff-line remove">- // Old implementation</div>
                <div class="diff-line add">+ ${summary}</div>
              </div>
            </div>
          </div>
        `;
      } else {
        return `
          <div class="message ai">
            <div class="message-header">
              <span class="message-sender">Codex</span>
              <span class="timestamp">${time}</span>
            </div>
            <div class="message-content">${summary}</div>
          </div>
        `;
      }
    })
    .join("");

  const container = document.getElementById("timeline-container");
  if (container) {
    container.scrollTop = container.scrollHeight;
  }
}

function setConnectionState(isConnected) {
  elements.connectionPill.textContent = isConnected ? "Connected" : "Disconnected";
  elements.connectionPill.className = `pill ${isConnected ? "connected" : "disconnected"}`;
}

function setStatus(status) {
  const text = status ? capitalize(status) : "Idle";
  elements.statusPill.textContent = text;
  elements.statusPill.className = `pill ${status || "idle"}`;
}

function checkStaleness() {
  if (!state.lastHeartbeatAt) {
    return;
  }
  const stale = Date.now() - state.lastHeartbeatAt > 10000;
  elements.staleBanner.classList.toggle("hidden", !stale);
}

function formatTime(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatNumber(value) {
  if (typeof value !== "number") {
    return "-";
  }
  return new Intl.NumberFormat().format(value);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function capitalize(value) {
  return String(value).charAt(0).toUpperCase() + String(value).slice(1);
}

function initDrawer() {
  const toggleBtn = document.getElementById("toggle-details-btn");
  const closeBtn = document.getElementById("close-details-btn");
  const drawer = document.getElementById("details-drawer");

  if (toggleBtn && drawer) {
    toggleBtn.addEventListener("click", () => {
      drawer.classList.toggle("drawer-open");
    });
  }

  if (closeBtn && drawer) {
    closeBtn.addEventListener("click", () => {
      drawer.classList.remove("drawer-open");
    });
  }
}

bootstrap();

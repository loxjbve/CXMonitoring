const translations = {
  en: {
    taskTitle: "Looking for an active Codex task",
    disconnected: "Disconnected",
    connected: "Connected",
    idle: "Idle",
    details: "ℹ️ Details",
    emptyState: "No active Codex thread has been discovered yet.",
    placeholder: "Ask AI to code...",
    workspace: "Workspace",
    mode: "Mode",
    progressTitle: "Current Progress",
    liveSummary: "Live summary",
    noTask: "No active Codex task detected.",
    latestPrompt: "Latest prompt",
    recentCommand: "Recent Command",
    shellActivity: "Shell activity",
    noCommand: "No command seen yet.",
    recentTool: "Recent Tool",
    toolingActivity: "Tooling activity",
    noTool: "No tool activity yet.",
    tokenUsage: "Token Usage",
    latestTotals: "Latest totals",
    total: "Total",
    input: "Input",
    output: "Output",
    reasoning: "Reasoning",
    waitingForData: "Waiting for data",
    waitingForMessage: "Waiting for a visible Codex progress message.",
    heroDefault: "This page follows the latest active Codex VS Code task running on this machine.",
    updated: "Updated ",
    noUpdates: "No updates yet",
    statusPrefix: "Status: ",
    durationPrefix: "Duration: ",
    toolPrefix: "Tool: ",
    statePrefix: "State: ",
    user: "User",
    codex: "Codex",
    reject: "Reject",
    apply: "Apply",
    langToggle: "🇺🇸 EN",
    staleBanner: "Data may be stale. Waiting for a fresh update from the desktop service.",
    untitledTask: "Untitled Codex task",
    event: "Event",
    composePlaceholder: "Tell AI what to do next...",
    relayMode: "Mobile relay",
    send: "Send",
    langToggleLabel: "中文"
  },
  zh: {
    taskTitle: "正在寻找活跃的 Codex 任务",
    disconnected: "已断开",
    connected: "已连接",
    idle: "空闲",
    details: "ℹ️ 详情",
    emptyState: "尚未发现活跃的 Codex 线程。",
    placeholder: "让 AI 帮你写代码...",
    workspace: "工作区",
    mode: "模式",
    progressTitle: "当前进度",
    liveSummary: "实时摘要",
    noTask: "未检测到活跃的 Codex 任务。",
    latestPrompt: "最新提示词",
    recentCommand: "最近命令",
    shellActivity: "Shell 动态",
    noCommand: "尚未看到任何命令。",
    recentTool: "最近工具",
    toolingActivity: "工具动态",
    noTool: "尚未有工具活动。",
    tokenUsage: "Token 消耗",
    latestTotals: "最新统计",
    total: "总计",
    input: "输入",
    output: "输出",
    reasoning: "推理",
    waitingForData: "等待数据...",
    waitingForMessage: "等待可见的 Codex 进度消息。",
    heroDefault: "此页面跟踪本机正在运行的最新活跃 Codex VS Code 任务。",
    updated: "已更新 ",
    noUpdates: "暂无更新",
    statusPrefix: "状态: ",
    durationPrefix: "耗时: ",
    toolPrefix: "工具: ",
    statePrefix: "状态: ",
    user: "用户",
    codex: "Codex",
    reject: "拒绝",
    apply: "应用",
    langToggle: "🇨🇳 中文",
    staleBanner: "数据可能已过期。正在等待桌面服务的新更新。",
    untitledTask: "未命名 Codex 任务",
    event: "事件",
    composePlaceholder: "告诉 AI 下一步要做什么…",
    relayMode: "移动中继",
    send: "发送",
    langToggleLabel: "EN"
  }
};

let currentLang = localStorage.getItem("lang") || "zh";

const state = {
  snapshot: null,
  eventSource: null,
  lastHeartbeatAt: 0,
  isSending: false,
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
  langToggleBtn: document.getElementById("lang-toggle-btn"),
  chatInput: document.getElementById("chat-input"),
  sendBtn: document.getElementById("send-btn"),
};

async function bootstrap() {
  initDrawer();
  initI18n();
  initComposer();

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
  state.lastHeartbeatAt = Date.now();
  renderSnapshot();
}

function initI18n() {
  if (elements.langToggleBtn) {
    elements.langToggleBtn.addEventListener("click", () => {
      currentLang = currentLang === "en" ? "zh" : "en";
      localStorage.setItem("lang", currentLang);
      updateStaticTexts();
      if (state.snapshot) {
        renderSnapshot();
      }
    });
  }
  updateStaticTexts();
}

function updateStaticTexts() {
  const t = translations[currentLang];
  if (elements.langToggleBtn) {
    elements.langToggleBtn.textContent = t.langToggleLabel || (currentLang === "zh" ? "EN" : "中文");
  }

  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (t[key]) {
      el.textContent = t[key];
    }
  });

  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    const key = el.getAttribute("data-i18n-placeholder");
    if (t[key]) {
      el.placeholder = t[key];
    }
  });
}

function extractSimpleTitle(rawTitle) {
  if (!rawTitle) return "";
  const lines = String(rawTitle).split('\n').map(l => l.trim()).filter(Boolean);
  if (lines.length === 0) return rawTitle;
  
  let title = lines[lines.length - 1];
  title = title.replace(/^#+\s*/, '');
  title = title.replace(/^\*\*|\*\*$/g, '');
  title = title.replace(/^["']|["']$/g, '');
  
  if (title.length > 60) {
    title = title.substring(0, 57) + "...";
  }
  
  return title;
}

function renderSnapshot() {
  const snapshot = state.snapshot || {};
  const hasThread = Boolean(snapshot.thread_id);
  const t = translations[currentLang];

  const rawTitle = snapshot.title || t.untitledTask;
  elements.taskTitle.textContent = hasThread
    ? extractSimpleTitle(rawTitle)
    : t.taskTitle;

  elements.heroCopy.textContent = hasThread
    ? snapshot.last_agent_message || t.waitingForMessage
    : t.heroDefault;

  setStatus(snapshot.status || "idle");
  elements.updatedAt.textContent = snapshot.updated_at
    ? `${t.updated}${formatTime(snapshot.updated_at)}`
    : t.noUpdates;
  elements.cwd.textContent = snapshot.cwd || t.waitingForData;
  elements.collaborationMode.textContent = snapshot.collaboration_mode || "-";
  elements.progressText.textContent =
    snapshot.last_agent_message || t.noTask;

  const command = snapshot.last_command || {};
  elements.commandSummary.textContent = command.summary || t.noCommand;
  elements.commandStatus.textContent = command.status
    ? `${t.statusPrefix}${command.status}`
    : `${t.statusPrefix}-`;
  elements.commandDuration.textContent =
    typeof command.duration_seconds === "number"
      ? `${t.durationPrefix}${command.duration_seconds.toFixed(2)}s`
      : `${t.durationPrefix}-`;

  const activeTool = snapshot.active_tool || {};
  elements.toolSummary.textContent =
    snapshot.last_tool_output_summary || activeTool.summary || t.noTool;
  elements.toolName.textContent = activeTool.name
    ? `${t.toolPrefix}${activeTool.name}`
    : `${t.toolPrefix}-`;
  elements.toolStatus.textContent = activeTool.status
    ? `${t.statePrefix}${activeTool.status}`
    : `${t.statePrefix}-`;

  renderTokenStats(snapshot.token_usage || null);
  renderTimeline();
  elements.emptyState.classList.toggle("hidden", hasThread);
  syncComposerState();
}

function renderTokenStats(tokenUsage) {
  const values = tokenUsage || {};
  const t = translations[currentLang];
  const items = [
    [t.total, formatNumber(values.total_tokens)],
    [t.input, formatNumber(values.input_tokens)],
    [t.output, formatNumber(values.output_tokens)],
    [t.reasoning, formatNumber(values.reasoning_output_tokens)],
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
  const t = translations[currentLang];

  elements.timelineList.innerHTML = timeline
    .map((entry) => renderTimelineEntry(entry, t))
    .filter(Boolean)
    .join("");

  bindChoiceButtons();

  const container = document.getElementById("timeline-container");
  if (container) {
    container.scrollTop = container.scrollHeight;
  }
  syncComposerState();
}

function renderTimelineEntry(entry, t) {
  const kindStr = String(entry.kind || entry.label || "").toLowerCase();
  const isUser = kindStr.includes("user") || kindStr === "prompt";
  const choiceRequest = !isUser ? extractChoiceRequest(entry) : null;
  const time = escapeHtml(formatTime(entry.ts));

  if (choiceRequest) {
    return renderChoiceTimelineEntry(entry, choiceRequest, time, t);
  }

  if (isUser) {
    return renderUserTimelineEntry(entry, time, t);
  }

  const isTool =
    kindStr.includes("tool") ||
    kindStr.includes("action") ||
    kindStr.includes("command") ||
    kindStr.includes("step");
  const isDiff = kindStr.includes("diff") || kindStr.includes("edit") || kindStr.includes("code");
  const label = escapeHtml(entry.label || entry.kind || t.event);
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
  }

  if (isDiff) {
    return `
      <div class="message ai">
        <div class="message-header">
          <span class="message-sender">${t.codex}</span>
          <span class="timestamp">${time}</span>
        </div>
        <div class="diff-block">
          <div class="diff-header">
            <span>${label}</span>
            <div class="diff-actions">
              <button class="diff-btn" type="button">${t.reject}</button>
              <button class="diff-btn apply" type="button">${t.apply}</button>
            </div>
          </div>
          <div class="diff-content">
            <div class="diff-line remove">- // Old implementation</div>
            <div class="diff-line add">+ ${summary}</div>
          </div>
        </div>
      </div>
    `;
  }

  return `
    <div class="message ai">
      <div class="message-header">
        <span class="message-sender">${t.codex}</span>
        <span class="timestamp">${time}</span>
      </div>
      <div class="message-content">${summary}</div>
    </div>
  `;
}

function renderUserTimelineEntry(entry, time, t) {
  const sender = escapeHtml(t.user);
  const content = escapeHtml(entry.details || entry.summary || "");

  return `
    <div class="message user">
      <div class="message-header">
        <span class="message-sender">${sender}</span>
        <span class="timestamp">${time}</span>
      </div>
      <div class="message-content">${content}</div>
    </div>
  `;
}

function renderChoiceTimelineEntry(entry, choiceRequest, time, t) {
  const prompt = escapeHtml(choiceRequest.prompt || entry.details || entry.summary || "");
  const options = choiceRequest.choices
    .map((choice) => {
      const label = escapeHtml(choice.label || choice.value || "");
      const value = escapeHtml(choice.value || choice.label || "");
      const replyTo = escapeHtml(choice.replyTo || choice.reply_to || choiceRequest.replyTo || deriveReplyKey(entry));
      return `
        <button
          class="choice-btn"
          type="button"
          data-choice-value="${value}"
          data-choice-reply-to="${replyTo}"
        >${label}</button>
      `;
    })
    .join("");

  return `
    <div class="message ai choice-request">
      <div class="message-header">
        <span class="message-sender">${t.codex}</span>
        <span class="timestamp">${time}</span>
      </div>
      <div class="message-content choice-card">
        <div class="choice-prompt">${prompt}</div>
        <div class="choice-options">${options}</div>
      </div>
    </div>
  `;
}

function extractChoiceRequest(entry) {
  const metadata = entry.metadata || {};
  const structuredChoices = normalizeChoiceList(metadata.choices || metadata.options);
  if (structuredChoices.length >= 2) {
    return {
      prompt: metadata.prompt || entry.details || entry.summary || "",
      choices: structuredChoices,
      replyTo: metadata.request_id || metadata.requestId || metadata.reply_to || metadata.replyTo || deriveReplyKey(entry),
    };
  }

  const parsed = parseChoiceText(entry.details || entry.summary || "");
  if (parsed) {
    return {
      prompt: parsed.prompt || entry.details || entry.summary || "",
      choices: parsed.choices,
      replyTo: parsed.replyTo || deriveReplyKey(entry),
    };
  }

  return null;
}

function normalizeChoiceList(value) {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.map(normalizeChoiceOption).filter(Boolean);
}

function normalizeChoiceOption(choice) {
  if (typeof choice === "string") {
    const text = choice.trim();
    if (!text) {
      return null;
    }
    return { label: text, value: text };
  }

  if (choice && typeof choice === "object") {
    const label = choice.label || choice.text || choice.title || choice.value;
    const value = choice.value || label;
    if (!label && !value) {
      return null;
    }
    return {
      label: String(label || value),
      value: String(value || label),
      replyTo: choice.reply_to || choice.replyTo || choice.request_id || choice.requestId || null,
    };
  }

  const text = String(choice ?? "").trim();
  if (!text) {
    return null;
  }
  return { label: text, value: text };
}

function parseChoiceText(value) {
  const raw = String(value || "").trim();
  if (!raw) {
    return null;
  }

  if (raw.startsWith("{") || raw.startsWith("[")) {
    try {
      const parsed = JSON.parse(raw);
      const structuredChoices = normalizeChoiceList(parsed.choices || parsed.options);
      if (structuredChoices.length >= 2) {
        return {
          prompt: parsed.prompt || parsed.message || parsed.question || "",
          choices: structuredChoices,
          replyTo: parsed.request_id || parsed.requestId || parsed.call_id || parsed.callId || null,
        };
      }
    } catch (error) {
      // Fall through to line-based parsing.
    }
  }

  const lines = raw.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const choices = [];
  const promptLines = [];
  let seenChoice = false;

  for (const line of lines) {
    const match = line.match(/^(?:[-*•]|\d+[.)]|[A-Za-z][.)])\s+(.+)$/);
    if (match) {
      seenChoice = true;
      choices.push({ label: match[1].trim(), value: match[1].trim() });
      continue;
    }

    if (!seenChoice) {
      promptLines.push(line);
    }
  }

  const prompt = promptLines.join(" ").trim();
  const looksLikeChoice =
    choices.length >= 2 &&
    (/choose|select|pick|reply|option|which|decision/i.test(prompt || raw) || /:\s*$/.test(promptLines[promptLines.length - 1] || ""));

  if (!looksLikeChoice) {
    return null;
  }

  return {
    prompt: prompt || "Choose a reply.",
    choices,
    replyTo: null,
  };
}

function deriveReplyKey(entry) {
  const metadata = entry.metadata || {};
  return (
    metadata.request_id ||
    metadata.requestId ||
    [entry.ts || "", entry.kind || "", entry.label || "", entry.summary || ""].join("::")
  );
}

function bindChoiceButtons() {
  if (!elements.timelineList) {
    return;
  }

  elements.timelineList.querySelectorAll("[data-choice-value]").forEach((button) => {
    button.addEventListener("click", () => {
      const value = button.getAttribute("data-choice-value") || button.textContent || "";
      const replyTo = button.getAttribute("data-choice-reply-to") || null;
      sendMessage(value, { kind: "choice_reply", replyTo });
    });
  });
}

function initComposer() {
  if (elements.chatInput) {
    elements.chatInput.addEventListener("input", resizeComposer);
    elements.chatInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage(elements.chatInput.value);
      }
    });
    resizeComposer();
  }

  if (elements.sendBtn) {
    elements.sendBtn.addEventListener("click", () => {
      sendMessage(elements.chatInput ? elements.chatInput.value : "");
    });
  }

  syncComposerState();
}

function resizeComposer() {
  if (!elements.chatInput) {
    return;
  }

  elements.chatInput.style.height = "auto";
  const nextHeight = Math.min(elements.chatInput.scrollHeight, 120);
  elements.chatInput.style.height = `${nextHeight}px`;
}

function syncComposerState() {
  const hasThread = Boolean(state.snapshot && state.snapshot.thread_id);
  const disabled = !hasThread || state.isSending;

  if (elements.chatInput) {
    elements.chatInput.disabled = disabled;
  }
  if (elements.sendBtn) {
    elements.sendBtn.disabled = disabled;
  }
  if (elements.timelineList) {
    elements.timelineList.querySelectorAll("[data-choice-value]").forEach((button) => {
      button.disabled = disabled;
    });
  }
}

async function sendMessage(content, options = {}) {
  const text = String(content || "").trim();
  if (!text || state.isSending) {
    return false;
  }

  const hasThread = Boolean(state.snapshot && state.snapshot.thread_id);
  if (!hasThread) {
    return false;
  }

  state.isSending = true;
  syncComposerState();

  try {
    const payload = {
      content: text,
      kind: options.kind || "instruction",
    };
    if (options.replyTo) {
      payload.reply_to = options.replyTo;
    }

    const response = await fetch("/api/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(await response.text());
    }

    const data = await response.json();
    if (data.snapshot) {
      updateSnapshot(data.snapshot);
    }

    if (elements.chatInput) {
      elements.chatInput.value = "";
      resizeComposer();
    }
    return true;
  } catch (error) {
    console.error("Failed to send message", error);
    return false;
  } finally {
    state.isSending = false;
    syncComposerState();
  }
}

function setConnectionState(isConnected) {
  const t = translations[currentLang];
  elements.connectionPill.textContent = isConnected ? t.connected : t.disconnected;
  elements.connectionPill.className = `pill ${isConnected ? "connected" : "disconnected"}`;
}

function setStatus(status) {
  const t = translations[currentLang];
  const text = status ? capitalize(status) : t.idle;
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

<div align="center">
  <h1>🚀 CXMonitoring</h1>
  <p>
    <strong>一个实时、只读的局域网仪表板，用于监控 VS Code 扩展中活跃的 Codex 任务。</strong>
  </p>
  
  <p>
    <a href="https://github.com/loxjbve/CXMonitoring/commits/main">
      <img src="https://img.shields.io/github/last-commit/loxjbve/CXMonitoring?style=flat-square&color=5e6ad2" alt="Last Commit" />
    </a>
    <a href="https://github.com/loxjbve/CXMonitoring/issues">
      <img src="https://img.shields.io/github/issues/loxjbve/CXMonitoring?style=flat-square&color=8a96ff" alt="Issues" />
    </a>
    <img src="https://img.shields.io/badge/python-3.8+-blue.svg?style=flat-square" alt="Python Version">
    <img src="https://img.shields.io/badge/FastAPI-0.115+-00a393.svg?style=flat-square" alt="FastAPI">
  </p>

  <p>
    <a href="README.md">🇨🇳 中文</a> · <a href="README_en.md">🇺🇸 English</a>
  </p>
</div>

<br/>

`CXMonitoring` 是一个时尚、移动端优先的 Web 仪表板。当你离开工位时，它能让你随时随地通过局域网在浏览器中实时查看 AI 编程助手（Codex）的执行动态、命令输出和 Token 消耗。

## ✨ 特性

- 🕵️ **自动检测**：瞬间检测并追踪 VS Code 中最新活跃的 Codex 线程。
- ⚡ **实时流式传输**：回放当前任务记录，并通过 Server-Sent Events (SSE) 向浏览器实时推送最新的 JSONL 事件流。
- 📱 **移动端优先 UI**：拥有美观的响应式抽屉布局，专为手机等移动设备监控而设计。
- 🔒 **只读安全**：严格执行只读监控，不修改 OpenAI 扩展配置，也不会写回 Codex 状态。
- 📊 **丰富指标**：直观展示当前任务标题、Agent 最新进度、Shell 终端命令、工具调用活动以及详细的 Token 消耗统计。

## 🛠️ 工作原理

仪表板通过读取 VS Code 扩展生成的本地文件来跟踪 Agent 的状态：
- **活跃线程元数据**：`%USERPROFILE%\.codex\state_5.sqlite`
- **实时事件流**：`%USERPROFILE%\.codex\sessions\...\rollout-*.jsonl`

## 🚀 快速开始

### 1. 安装依赖

你可以直接通过安装所需的依赖包来运行服务器：

```bash
python -m pip install fastapi uvicorn httpx
```

*或者，以可编辑模式安装项目包：*

```bash
python -m pip install -e .
```

### 2. 启动服务器

运行独立脚本：

```bash
python run_server.py
```

*或者作为模块运行：*

```bash
python -m cxmonitoring
```

### 3. 打开仪表板

在浏览器中访问以下 URL 之一：
- 本地访问：`http://127.0.0.1:3180`
- 局域网访问（通过手机）：`http://<你的局域网-IP>:3180`

## ⚙️ 配置 (环境变量)

你可以通过以下环境变量自定义服务器的行为：

| 变量名 | 描述 | 默认值 |
| :--- | :--- | :--- |
| `CXMONITORING_CODEX_HOME` | 覆盖默认的 Codex 主目录 | *(自动检测)* |
| `CXMONITORING_HOST` | 绑定的主机地址 | `0.0.0.0` |
| `CXMONITORING_PORT` | 监听的端口号 | `3180` |
| `CXMONITORING_THREAD_POLL` | 线程刷新间隔（秒） | `1.0` |
| `CXMONITORING_ROLLOUT_POLL` | 记录追踪间隔（秒） | `0.3` |

## 🧪 运行测试

运行测试套件以确保一切工作正常：

```bash
python -m unittest discover -s tests
```

## ⚠️ 安全提示

默认情况下，此服务器绑定到 `0.0.0.0:3180` 并且无需身份验证。本地网络 (LAN) 上的任何人都可以查看你当前的任务、最近的提示词、工具摘要和命令输出。请在受信任的网络中负责任地使用。

---

<div align="center">
  由 CXMonitoring 团队用心 ❤️ 制作。
</div>
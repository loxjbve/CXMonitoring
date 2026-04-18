# 前端移动端优化与重构方案

## 1. 概述 (Summary)
重构 `cxmonitoring` 的前端页面，采用移动端优先的设计理念。核心改动包括：隐藏时间线中的用户输入消息、将 Agent 的动态作为页面的主体展示区域，并将其他所有元数据信息（工作区、Token 统计、执行命令等）默认折叠，通过点击按钮才展示。

## 2. 现状分析 (Current State Analysis)
- **布局**：目前采用左右分栏布局（左侧 `.sidebar` 显示对话，右侧 `.main-content` 显示状态信息），在移动端（`< 900px`）下会上下堆叠，各占 50vh，导致移动端可视区域极度拥挤。
- **逻辑**：`app.js` 中的 `renderTimeline` 会同时渲染 `isUser`（用户输入）和 Agent 动态，目前用户输入会直接占用屏幕空间。
- **样式**：`styles.css` 中缺乏完善的折叠交互和响应式抽屉组件。

## 3. 详细修改方案 (Proposed Changes)

### 3.1 `src/cxmonitoring/static/app.js`
- **隐藏用户输出**：在 `renderTimeline` 函数中，当识别到消息类型为用户（`isUser === true`）时，直接 `return ""`，不生成 HTML，从而隐藏用户输入。
- **折叠交互逻辑**：新增状态变量和 DOM 操作逻辑。获取“详细信息”按钮和侧边/底部抽屉面板的 DOM 节点，通过监听点击事件来切换 CSS 类（如 `.drawer-open` / `.hidden`），实现信息面板的展开与折叠。

### 3.2 `src/cxmonitoring/static/index.html`
- **DOM 结构重构**：
  - 移除原有的固定左右分栏（`.sidebar` 和 `.main-content` 的并排结构）。
  - **主视图**：将头部状态栏（`.chat-header`）和聊天时间线（`#timeline-container`）作为页面的主体核心，占据整个屏幕空间。
  - **控制按钮**：在头部导航栏增加一个“详细信息”按钮（例如：ℹ️ 详情）。
  - **折叠面板 (Drawer)**：将原 `.main-content` 中的所有状态卡片（Workspace, Mode, Progress, Command, Tool, Token Usage 等）统一移动到一个新的抽屉式容器中（如 `<div id="details-drawer" class="drawer hidden">`），默认不显示。

### 3.3 `src/cxmonitoring/static/styles.css`
- **主界面布局**：调整 `.layout-wrapper`，让主视图容器高度设为 `100vh` 且宽度 `100%`，保证 Agent 动态在移动端有最大的阅读空间。
- **折叠面板样式**：
  - 为 `#details-drawer` 添加固定定位（`position: fixed`），层级调高（`z-index: 100`）。
  - 在移动端可设计为从底部滑出的面板（Bottom Sheet），在 PC 端可设计为从右侧滑出的侧边栏。
  - 添加半透明的背景遮罩层（Overlay），并在打开时展示过渡动画（`transition: transform 0.3s ease`）。
- **清理冗余**：移除原来针对 `< 900px` 的 `50vh` 分屏逻辑。

## 4. 假设与决策 (Assumptions & Decisions)
- **决策**：将“其他信息”统一收纳到一个全局的悬浮抽屉（Drawer）中。这能保证页面在任何设备下都足够简洁，并最大化 Agent 执行过程的可见性。
- **假设**：底部的输入框区域（`chat-input-container`）保留，但由于不再展示用户消息，其主要功能转为触发后台操作，UI 也可以适当做极简处理。

## 5. 验证步骤 (Verification Steps)
1. 在浏览器中打开页面并切换至移动端视图，确认页面默认仅显示 Agent 动态。
2. 确认此前和新发送的 User Prompt 均不再出现在页面时间线中。
3. 点击顶部新增的“详情”按钮，确认状态面板能顺滑弹出。
4. 在面板外点击或再次点击按钮，确认状态面板能正确折叠。
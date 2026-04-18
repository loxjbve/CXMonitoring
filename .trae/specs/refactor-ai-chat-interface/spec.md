# Agentic Coding 风格 AI 交互中心重构 Spec

## Why
当前前端页面的 AI 交互体验不足以支撑高效的 Agentic Coding（类似于 Cursor, Roocode, Windsurf 等工具）。需要通过极简、深色模式和高科技感的设计语言，提升用户进行代码编写、问答和代码 Diff 审查时的专注度与交互体验。

## What Changes
- **整体主题重构**：引入深色模式（纯黑/极深灰背景 #0A0A0A），细微灰色边框（rgba(255,255,255,0.1)），以及科技蓝/紫色的强调色。
- **布局调整**：增加宽度 300px-400px 的固定侧边栏作为主要 AI 对话区。
- **视觉优化**：引入毛玻璃效果（Glassmorphism），采用无边框设计，通过阴影和色块区分层级。
- **核心组件开发/重构**：
  - **Chat Input**：底部悬浮多行自适应输入框，包含添加上下文的 "+" 按钮和模型选择器标签。
  - **Message Bubbles**：区分用户和 AI 的消息气泡。AI 回复无背景直接展示文本/Markdown；用户回复使用深灰色圆角矩形。
  - **Step/Action Indicators**：增加任务执行步骤条（如 Searching files... -> Applying changes...），包含微缩动画或 Loading 点。
  - **Code Diff Block**：新增类似于 Git Diff 的代码块展示，带有绿色/红色高亮块及 "Apply" 和 "Reject" 悬浮按钮。

## Impact
- Affected specs: 页面整体 UI/UX 规范、AI 聊天交互流程。
- Affected code: 全局样式文件（CSS/Tailwind 配置）、主页面布局组件、聊天交互相关的所有 UI 组件。

## ADDED Requirements
### Requirement: AI 侧边栏布局与视觉体验
系统 SHALL 提供一个 300px-400px 的固定侧边栏作为对话区，具有毛玻璃透明效果和深色模式适配。

#### Scenario: Success case
- **WHEN** 用户打开页面
- **THEN** 侧边栏应以深黑/极深灰为主色调，没有突兀的粗边框，层级分明，视觉上呈现极客感。

### Requirement: 核心交互组件
系统 SHALL 提供自适应输入框、气泡消息、步骤指示器和代码 Diff 预览块。

#### Scenario: Success case
- **WHEN** 用户输入多行文本
- **THEN** 输入框高度自动适应，且左侧有加号按钮，右侧显示当前模型。
- **WHEN** AI 正在执行动作
- **THEN** 界面展示带有微缩动画的步骤指示器。
- **WHEN** AI 提出代码修改建议
- **THEN** 渲染包含 Apply/Reject 按钮及红绿高亮对比的 Code Diff 视图。
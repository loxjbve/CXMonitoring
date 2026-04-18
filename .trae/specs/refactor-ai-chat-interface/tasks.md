# Tasks
- [x] Task 1: 基础架构与样式重置
  - [x] SubTask 1.1: 配置全局深色模式变量（#0A0A0A 背景，rgba(255,255,255,0.1) 边框，科技蓝/紫强调色）。
  - [x] SubTask 1.2: 引入和配置毛玻璃（Glassmorphism）和无边框设计相关的 CSS 工具类。
- [x] Task 2: 整体布局重构
  - [x] SubTask 2.1: 实现带有固定宽度的侧边栏（300px-400px），将其设为主 AI 对话区。
  - [x] SubTask 2.2: 调整主内容区与侧边栏的响应式适配与阴影层级。
- [x] Task 3: 核心交互组件开发
  - [x] SubTask 3.1: 开发悬浮底部自适应 Chat Input，包含 "+" 按钮和模型选择器。
  - [x] SubTask 3.2: 开发 Message Bubbles，区分用户（深灰色圆角矩形）与 AI（无背景 Markdown 渲染）。
  - [x] SubTask 3.3: 开发 Step/Action Indicators，实现执行步骤的加载动画。
  - [x] SubTask 3.4: 开发 Code Diff Block 组件，支持红绿代码高亮及 Apply/Reject 悬浮操作。
- [x] Task 4: 组件集成与交互打通
  - [x] SubTask 4.1: 将新开发的组件接入现有页面逻辑。
  - [x] SubTask 4.2: 测试输入框自适应、消息气泡渲染及 Diff 块交互的流畅度。

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 1]
- [Task 4] depends on [Task 2] and [Task 3]
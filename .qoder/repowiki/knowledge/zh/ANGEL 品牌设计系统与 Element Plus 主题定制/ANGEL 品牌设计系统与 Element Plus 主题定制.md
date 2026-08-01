---
kind: frontend_style
name: ANGEL 品牌设计系统与 Element Plus 主题定制
category: frontend_style
scope:
    - '**'
source_files:
    - frontend/package.json
    - frontend/vite.config.js
    - frontend/src/main.js
    - frontend/src/style.css
    - frontend/src/styles/angel-theme.css
---

## 1. 系统/方法概述
- 前端基于 Vue 3 + Vite，UI 组件库统一使用 Element Plus（v2.13+），通过 CSS 变量与全局样式覆盖实现 ANGEL 品牌视觉定制。
- 采用「CSS 变量 + 全局主题文件」的设计系统方案：所有颜色、字体、间距、圆角、阴影、动画缓动等设计令牌集中在单一主题文件中，由业务组件直接引用，避免硬编码样式值。
- 构建工具链为 Vite，开发服务器默认 5173 端口，并通过代理将 `/api` 请求转发到后端 5002 端口，解决跨域问题。

## 2. 关键文件与包
- `frontend/package.json`：声明依赖（Vue 3、Element Plus、ECharts、Axios、highlight.js、marked 等）与 Vite 脚本。
- `frontend/vite.config.js`：Vite 配置，含路径别名 `@` → `src`、开发代理、缓存目录自定义。
- `frontend/src/main.js`：应用入口，注册 ElementPlus 中文语言包、图标集、路由，并引入全局样式。
- `frontend/src/style.css`：全局基础重置（box-sizing、滚动条美化、基础排版、背景色等）。
- `frontend/src/styles/angel-theme.css`：核心主题文件，定义完整的 ANGEL 品牌设计令牌与 Element Plus 全局覆写。

## 3. 架构与约定
### 设计令牌体系（Design Tokens）
- 字体：`--font-sans` / `--font-mono`，代码块强制使用等宽字体。
- 品牌色：以安吉尔红 `#E61F24` 为主品牌色，配合深灰黑体系作为主行动色（`--brand-action`）。
- 语义色：`--text-title/body/secondary/muted/placeholder`、`--bg-page/card/soft/hover/elevated/mask`、`--border/border-light/border-hover/border-strong`。
- 状态色：success/warning/error/info 及其 soft 变体。
- 阴影：从 `--shadow-xs` 到 `--shadow-xl` 的层级化阴影体系。
- 圆角：`--radius-xs/sm/md/card/lg/xl/pill`。
- 间距：`--space-xs` 到 `--space-3xl` 的 8px 倍数网格。
- 动画：统一的 `--ease-out` / `--ease-in-out` 缓动曲线与 `--duration-fast/normal/slow` 时长。

### Element Plus 主题映射
- 通过覆盖 `--el-color-*`、`--el-text-color-*`、`--el-border-color-*`、`--el-fill-color-*`、`--el-bg-color*`、`--el-box-shadow*` 等 CSS 变量，将 Element Plus 默认蓝色主题完全替换为 ANGEL 品牌色系。
- 对按钮、输入框、选择器、卡片、对话框、表格、标签、消息、下拉菜单、分页、步骤、进度条、单选/复选、滑块、日期时间选择器等几乎所有内置组件进行全局样式覆写。

### 组件级样式约定
- 页面骨架类：`.admin-workspace`、`.agent-page`、`.dataset-page`、`.cs-page`、`.rc-page` 等用于统一页面容器样式。
- 通用工具类：`.sa-glass-card`（毛玻璃卡片）、`.sa-dark-panel` / `.sa-dark-panel-soft`（深色面板）、`.sa-page-title` / `.sa-section-title` / `.sa-muted-text`（文本层级）、`.sa-striped`（隔行变色）。
- 动画工具类：`.animate-fade-in-up`、`.animate-pulse`、`.animate-spin`、`.animate-blink` 等。
- Toast 通知：`.sa-toast-modern` 提供现代化毛玻璃风格通知。

### 样式加载顺序与优先级
- `main.js` 中按顺序引入：Element Plus 默认样式 → 全局基础重置 (`style.css`) → 品牌主题 (`angel-theme.css`)，确保主题覆盖生效。
- 大量使用 `!important` 强制覆盖 Element Plus 默认样式，保证品牌一致性。

## 4. 约定与约束
- **禁止在组件内硬编码颜色/尺寸**：所有视觉值必须通过 CSS 变量引用，确保主题可维护性。
- **Element Plus 组件样式统一**：所有 Element Plus 组件的样式覆写在 `angel-theme.css` 中集中管理，不在组件内重复定义。
- **焦点可见性**：通过兜底规则覆盖浏览器默认 focus ring，改用品牌色的外发光效果（`--brand-action-focus`）。
- **响应式策略**：当前未使用媒体查询或 Tailwind 等响应式框架，主要通过弹性布局和相对单位实现适配。
- **构建与开发**：Vite 开发服务器固定 5173 端口，API 代理目标为 `http://localhost:5002`，生产构建产物由 Nginx 托管。
- **向后兼容**：主题文件同时保留旧版变量名（如 `--color-primary`、`--gray-*`）以保证历史代码兼容。

## 5. 技术栈总结
| 层面 | 技术选型 |
|------|----------|
| 框架 | Vue 3 (Composition API) |
| 构建 | Vite 8 |
| UI 组件库 | Element Plus 2.13 + @element-plus/icons-vue |
| 图表 | ECharts 6 |
| Markdown 渲染 | marked 17 |
| HTTP 客户端 | Axios 1.13 |
| 代码高亮 | highlight.js 11 |
| 样式方案 | CSS 变量 + 全局主题覆盖（无预处理器） |
| 路由 | Vue Router 4 |

该设计系统通过集中化的 CSS 变量管理和 Element Plus 全局覆写，实现了 ANGEL 品牌在智能问数系统中的统一视觉呈现，具备良好的可维护性和扩展性。
---
# Trae 项目规则 - 前端专属
# 生效方式：Apply to Specific Files
alwaysApply: false
globs:
  - "frontend/**/*.{vue,js,ts,css}"
---

# SmartAsk 前端开发规范

## 技术栈

- Vue 3.5 (`<script setup>` 语法) + Vite 8 + Element Plus 2.x + ECharts 6
- 路由：vue-router 4
- HTTP：axios
- Markdown 渲染：marked + highlight.js

## 目录约定

| 目录 | 放什么 |
|---|---|
| `frontend/src/views/` | 页面级组件 |
| `frontend/src/components/` | 可复用组件 |
| `frontend/src/api/` | API 调用封装（统一走这层，不要在组件里直接调 axios） |

## 规范

- 组件用 `<script setup>` 语法，不用 Options API
- 用 Element Plus 组件，不要引入其他 UI 库
- 图表用 ECharts，新图表封装成独立组件放 `components/`
- API 调用统一走 `api/` 层封装，组件不直接调 axios
- 响应式样式用项目既有断点，不引入 Tailwind 或其他 CSS 框架
- 构建：`cd frontend && npm run dev`（开发）/ `npm run build`（构建）

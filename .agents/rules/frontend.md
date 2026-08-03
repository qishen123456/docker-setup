# SmartAsk 前端开发规范

> Antigravity 工作区规则 - 处理 `frontend/` 下的文件时自动生效。
> 激活方式建议设为 Glob: `frontend/**/*.{vue,js,ts,css}`

## 技术栈

- Vue 3.5 (`<script setup>`) + Vite 8 + Element Plus 2.x + ECharts 6
- 路由：vue-router 4 | HTTP：axios | Markdown：marked + highlight.js

## 目录约定

| 目录 | 放什么 |
|---|---|
| `frontend/src/views/` | 页面级组件 |
| `frontend/src/components/` | 可复用组件 |
| `frontend/src/api/` | API 调用封装（统一走这层） |

## 规范

- 组件用 `<script setup>` 语法，不用 Options API
- 用 Element Plus，不引入其他 UI 库
- 图表用 ECharts，封装成独立组件放 `components/`
- API 调用统一走 `api/` 层，组件不直接调 axios
- 构建：`cd frontend && npm run dev` / `npm run build`

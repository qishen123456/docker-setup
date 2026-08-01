---
kind: external_dependency
name: Nginx 反向代理与静态资源服务
slug: nginx
category: external_dependency
category_hints:
    - framework_behavior
scope:
    - '**'
source_files:
    - frontend/nginx.conf
    - frontend/Dockerfile
---

前端容器使用 Nginx 托管 Vue 静态产物，配置了 SSE 长连接支持（proxy_buffering off, read_timeout 300s），将 /api 请求反向代理到后端 Flask 服务。静态资源启用 hash 长缓存，index.html 禁用缓存以确保更新及时生效。
---
kind: external_dependency
name: PostgreSQL 数据库
slug: postgresql
category: external_dependency
category_hints:
    - vendor_identity
scope:
    - '**'
source_files:
    - docker-compose.yml
    - backend/requirements.txt
---

使用 PostgreSQL 16-alpine 作为主数据库，容器端口映射到 5433。业务数据、bs_* 元数据表、系统日志均存储于此。通过 psycopg2-binary 驱动连接，当前无连接池配置，每次请求新建短连接。支持 schema 迁移脚本在 docker/postgres/init 目录自动执行。
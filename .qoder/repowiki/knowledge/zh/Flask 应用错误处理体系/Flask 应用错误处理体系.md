---
kind: error_handling
name: Flask 应用错误处理体系
category: error_handling
scope:
    - '**'
source_files:
    - backend/app.py
    - backend/security.py
    - backend/controllers/auth.py
    - backend/controllers/ai_models.py
    - backend/controllers/agents.py
---

SmartAsk 后端基于 Flask 构建，采用「全局 errorhandler + 控制器内 try/except + 安全守卫函数」三层混合的错误处理模式，未定义统一的自定义异常类型或错误码枚举。

**1. 全局错误处理器（app.py）**
- 通过 `@app.errorhandler(404)`、`@app.errorhandler(405)`、`@app.errorhandler(500)` 统一返回 JSON 格式：`{"error": "...", "detail": "..."}`。
- 所有 HTTP 错误响应均使用 `jsonify` 包装，保证前端一致解析。
- `after_request` 钩子 `_record_access_log` 对状态码 ≥400 的请求自动记录到系统日志表，并附带 `_http_error_guidance` 生成的诊断提示（按路径区分数据集生成、保存失败、权限不足等场景）。

**2. 控制器层错误处理（controllers/*.py）**
- 每个路由函数普遍采用 `try/except Exception as e` 包裹业务逻辑，捕获后返回 `jsonify({"error": str(e)}), 500`。
- 参数校验失败直接返回 400，如 `ai_models.py` 中对空请求体、缺失 name/api_key 的校验。
- 资源不存在返回 404，如 `agents.py` 中 `agent not found`、`ai_models.py` 中 `未找到 ID=xxx 的模型`。
- 权限拒绝通过 `security.py` 的守卫函数返回 401/403，而非抛出异常。

**3. 安全与鉴权错误（security.py）**
- `require_login()`、`require_feature()`、`require_any_feature()`、`require_super_admin()` 四个守卫函数统一返回 `(user, error_tuple)` 形式，其中 error_tuple 为 `(jsonify({"error": "..."}), 401/403)`，由调用方判断是否提前返回。
- 未登录返回 401，无功能权限返回 403，且错误消息可定制。

**4. 外部依赖错误（auth.py）**
- 飞书 API 调用通过 `_feishu_post` / `_feishu_get` 封装，HTTP 状态码 ≥400 时抛 `RuntimeError`，业务 code ≠ 0 时也抛 `RuntimeError`，由上层 try/except 捕获后转为 500 响应。
- 登录回调中的异常通过 `_log_auth_event` 记录 auth 类别日志，再返回带详细错误信息的 JSON。

**5. 业务异常（agent_registry.py）**
- 使用 Python 内置 `ValueError` 表示业务校验失败（如 `Agent not found: {agent_no}`），由调用方的 try/except ValueError 捕获并转为 404。

**6. 约定与约束**
- 所有错误响应统一使用 `{"error": "..."}` 字段名，便于前端统一处理。
- 未定义自定义异常类或错误码常量，错误信息以字符串形式硬编码在控制器中。
- 未使用 `abort()` 或 `HTTPException`，全部通过 `return jsonify(...), status_code` 显式返回。
- 未使用 `panic/recover`（Python 无此概念），也未见 `sys.exit()` 或 `os._exit()` 用于错误退出。
- 所有异常路径均通过 `after_request` 钩子记录访问日志，但 400+ 错误不会重复记录（通过 `_smartask_event_logged` 标记避免）。
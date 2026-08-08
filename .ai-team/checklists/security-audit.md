# 安全审计清单（精简版）

> 基于 gstack-security-officer 的 14 阶段框架精简，适配 fullstack-dev-team reviewer。
> 审查时逐阶段执行，每条发现打置信度（0-10）。

## 审计模式

| 模式 | 置信度门禁 | 适用 |
|---|---|---|
| 快速（Daily） | ≥ 8 才报告 | 日常 PR 审查 |
| 深度（Comprehensive） | ≥ 2 都报告 | 发布前/月度安全审计 |

## 审计阶段

### 1. 架构心智模型
- 读配置文件，画服务边界与数据流
- 标注信任边界（数据跨越鉴权检查点的地方）
- 列出入口点（API / CLI / Webhook）

### 2. 攻击面普查
- 列出所有 HTTP 端点
- 标注暴露级别（public / internal / admin）
- 检查鉴权覆盖是否完整

### 3. 密钥考古
- 搜索硬编码 api_key / secret / password / token
- 检查 base64 编码的长字符串（>40 字符）
- 检查私钥标记（BEGIN RSA / BEGIN PRIVATE）
- **规则：只报告位置，不输出实际密钥值**

### 4. 依赖供应链
- 读 lock 文件，检查已知 CVE
- 检查废弃/无人维护的包
- 检查依赖混淆风险

### 5. CI/CD 安全
- 检查 pull_request_target + checkout PR head
- 检查 secrets 是否泄露到构建日志
- 检查 CI 命令注入

### 6. OWASP A01-A10 逐项
- A01 越权（IDOR / RBAC 缺失）
- A02 加密失败（弱哈希 / 明文传输）
- A03 注入（SQL 拼接 / 命令注入 / 模板注入）
- A04 不安全设计（缺限流 / 缺威胁模型）
- A05 配置错误（默认凭证 / 错误堆栈外泄 / 缺安全头）
- A06 过时组件（EOL 框架 / 已知 CVE）
- A07 认证失败（弱哈希 / 无暴力保护 / 会话管理）
- A08 完整性失败（未签名代码 / 不安全反序列化）
- A09 日志监控失败（安全事件未记录 / 日志存敏感数据）
- A10 SSRF（用户控制 URL / 元数据服务访问）

### 7. STRIDE 威胁建模
- **Spoofing**：能否冒充用户/服务？
- **Tampering**：能否篡改传输中/存储中数据？
- **Repudiation**：能否否认操作？
- **Information Disclosure**：敏感数据能否被未授权访问？
- **Denial of Service**：能否耗尽资源？
- **Elevation of Privilege**：能否提权？

### 8. 误报过滤 + 主动验证
- 每条发现打置信度 0-10
- 10 = 已复现完整攻击链
- 8-9 = 高确定性可利用
- 5-7 = 可能存在，部分复现
- 2-4 = 理论可能
- 0-1 = 大概率误报
- **快速模式只报告 ≥ 8 的，深度模式报告 ≥ 2 的**
- **每条发现必须给出复现步骤或标注"理论推测"**

## 输出格式

```
### [F-001] 发现标题
- 类别：OWASP A0X / STRIDE
- 严重级：Critical / High / Medium / Low
- 置信度：[0-10]
- 位置：file:line 或 endpoint
- 描述：漏洞是什么
- 复现步骤：具体步骤
- 修复建议：具体方案
```

## SmartAsk 特有检查项（2026-08-06 审计补充）

通用 OWASP 清单之外，以下四项是 SmartAsk 架构特有的安全缺陷类型，每次审查必须逐项检查。

### S-1 只读护栏方向检查

检查点：SQL 执行链上，可信路径与不可信路径的校验强度是否倒挂。

- approved=True（LLM 改写的 SQL）是否在执行前做了只读校验？
- approved=False（被否决的 SQL）是否反而过了校验？
- 物理执行点 `datasource_router.execute_sql_for_source` 是否有强制闸口？
- 修复后的目标：唯一闸口在执行点，上层全部分支式校验删除。

参考：审计报告 A-01，`four_agent_ask.py:8225-8263` / `datasource_router.py:192-199`

### S-2 行级权限 fail-open 检查

检查点：无权限规则时默认行为是放行还是拒绝。

- `data_permission_store.py` 中无规则时 `return sql`（放行）还是返回 `1=0`（拒绝）？
- `config/data_permissions.json` 覆盖了多少数据集？未覆盖的是否默认放行？
- 排名 SQL 的权限谓词是否下推到最内层事实表？外层包裹对窗口函数是否有效？
- 修复后的目标：默认 deny，public 数据集白名单化。

参考：审计报告 B3/B4，`data_permission_store.py:475` / `ask_engine_sql.py:36-47`

### S-3 LLM 候选链跨域过滤检查

检查点：LLM 失败时是否会把 prompt 重发给不同服务商。

- `llm_client.py` 候选链是否按服务商归属域切分？
- `ask_engine_core.py` 可重试集合是否包含 `AuthenticationError` / `PermissionDeniedError`（配置问题不应触发重试）？
- retry 埋点是否记录了实际外发 endpoint（当前只记 candidate_index）？
- 修复后的目标：跨域不自动降级，凭据失效直接失败+告警。

参考：审计报告 L-04/B16-c，`llm_client.py:74-83` / `ask_engine_core.py:31-39`

### S-4 迁移完整性检查

检查点：数据库表结构是否有可信的、单一的、幂等的真相源。

- `angel_group_data` 表是否有正规迁移文件（不仅靠 docker init 首次执行）？
- `bs_common_questions` / `bs_dataset_external_configs` / `bs_regression_cases` 是否在 `backend/migrations/` 中有定义？
- 是否存在多处 `_ensure_optional_tables` 副本？md5 是否一致？
- `bootstrap.py` 迁移失败是否阻断启动（当前仅记日志注释"非致命"）？
- 修复后的目标：`backend/migrations/` 为唯一真相源，docker init 只含数据库/用户初始化，迁移失败阻断启动。

参考：审计报告 L-01/L-02/L-03，`bootstrap.py:45-57` / `controllers/bookshelf.py:526-576`

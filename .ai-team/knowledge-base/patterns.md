# 重复模式

> 项目特定的最佳实践。反复出现的有效模式。
> 格式：模式名 / 适用场景 / 具体做法 / 代表性文件

配置优先于硬编码
适用场景：数据集策略、功能开关、角色权限、分析口径
具体做法：写 config/ 下 json，不写进代码；feature_flag 控制 advanced 开关；advancedRoles 控制权限
代表性文件：config/dataset_policies.json, config/feature_flags.json

Flask Blueprint 分层注册
适用场景：新增功能模块时
具体做法：在 backend/controllers/ 下新建模块 .py，定义 Blueprint，在 app.py 中注册；18 个 blueprint 各管一个域
代表性文件：backend/app.py（入口注册）, backend/controllers/smart_chat.py（问数主路由）

SSE 帧序列模式
适用场景：问数 SSE 流式输出
具体做法：帧序列 ready -> trace -> summary -> heartbeat -> result -> done，内存 queue 单线程消费
代表性文件：backend/controllers/smart_chat.py

契约边界模式
适用场景：改动 ask_flow 相关逻辑时
具体做法：AskRequest / ConfirmRequest / FlowDecision 是改动边界，改动前先读 contracts.py，改动后确认序列化/反序列化兼容
代表性文件：backend/ask_flow/contracts.py

前端 API 封装层
适用场景：前端调用后端接口
具体做法：在 frontend/src/api/ 下封装，views/ 层只调 api/ 不直接发请求
代表性文件：frontend/src/api/

---

## 审计发现的新模式（2026-08-06，反模式——需要消除而非效仿）

以下三条是审计中发现的、反复出现的**反模式**。它们不是最佳实践，是项目里需要消除的结构性缺陷。记录在此是因为后续修复时会反复遇到，需要识别并根除。

### 静默降级族（反模式）

适用场景：理解"为什么用户拿到的数字可能是错的"
具体做法（当前现状，需消除）：Agent2 没生成 SQL / Agent3 否决 / SQL 执行报错 / LLM 调用挂掉 / 权限过滤滤空——这些性质完全不同的硬失败，全部汇流成同一句用户可见文案"未查询到匹配数据"。用户读到的是"这块没数据"，真相是"这个查询坏了"。族内还有一条更严重的成员：否决态被伪造为成功态（步骤条无条件写 success，写在判断 approved 之前）
代表性文件：four_agent_ask.py:8139-8154 / 8228-8237 / 8358-8367（汇流点）→ _build_graceful_dataset_result → _build_fallback_analysis；:8217-8223（否决态伪造）

### 护栏倒挂（反模式）

适用场景：理解"为什么安全校验没生效"
具体做法（当前现状，需消除）：可信路径（规则引擎/Golden SQL）校验最严（只读校验+字段校验+行级权限），不可信路径（LLM 自由生成）校验最松（无只读校验），物理执行点零护栏。规律：越可信校验越严，越不可信越松。防护强度和路径重要性完全倒挂
代表性文件：four_agent_ask.py:7425（可信路径有校验）vs :7676-7683（不可信路径无校验）vs datasource_router.py:192-199（执行点零护栏）

### 分叉副本（反模式）

适用场景：理解"为什么表结构在不同环境不一致"
具体做法（当前现状，需消除）：同一份 schema 的 DDL 存在 5 份同名函数 `_ensure_optional_tables`，md5 归一化比对全部不同——已分叉的副本。配合 CREATE TABLE IF NOT EXISTS 语义（先跑者定义结构，后者静默跳过），表结构取决于环境历史上先跑过哪个脚本，不可预测、不可复现
代表性文件：controllers/bookshelf.py:526-576 / runtime_migration.py:616-674 / import_bookshelf_bundle.py:39-101 / create_consumer_standard_dataset.py:659-716 / export_bookshelf_bundle.py:45-57

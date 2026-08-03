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

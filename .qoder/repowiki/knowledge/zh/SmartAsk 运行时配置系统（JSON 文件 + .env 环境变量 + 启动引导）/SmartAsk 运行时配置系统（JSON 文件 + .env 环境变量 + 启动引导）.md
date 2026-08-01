---
kind: configuration_system
name: SmartAsk 运行时配置系统（JSON 文件 + .env 环境变量 + 启动引导）
category: configuration_system
scope:
    - '**'
source_files:
    - backend/config_manager.py
    - backend/bootstrap.py
    - backend/app.py
    - backend/secret_codec.py
    - backend/feature_flags.py
    - config/app_config.json
    - config/datasources.json
    - config/ai_settings.json
    - config/feature_flags.json
    - config/.secret_master_key
---

## 1. 系统与架构概览
SmartAsk 的运行时配置采用「JSON 文件持久化 + .env 环境变量覆盖 + bootstrap 一次性初始化」的组合模式：
- 所有可编辑的配置以 JSON 文件形式存放在 `config/` 目录，由后端统一通过 `backend/config_manager.py` 读写。
- 敏感值（数据库密码、AI Key、Flask secret_key）通过 `backend/secret_codec.py` 使用基于主密钥的流式加密存储，读取时自动解密。
- 应用启动前由 `backend/bootstrap.py` 执行幂等初始化：等待 PostgreSQL、运行 SQL 迁移、恢复运行态配置包、导入内置数据集与模板，最后 `os.execv` 切换到 `app.py` 启动 Flask。
- 功能开关（feature flags）集中保存在 `config/feature_flags.json`，由 `backend/feature_flags.py` 提供注册表与默认值。

该设计将「环境差异」交给 `.env`，「业务配置」交给 JSON 文件，「启动流程」交给 bootstrap，三者互不干扰且可独立替换。
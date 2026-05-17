"""
JSON-backed feature gate registry.

This module intentionally keeps feature switches in config/feature_flags.json so
they can travel with runtime export/import bundles without introducing a new DB
table or migration dependency.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any

from config_manager import read_json, write_json


FEATURE_FLAGS_FILE = "feature_flags.json"
ROLE_SCHEMA_VERSION = 2
ROLE_ORDER = {"user": 1, "business_admin": 2, "admin": 3, "super_admin": 4}
VALID_ROLES = tuple(ROLE_ORDER.keys())


DEFAULT_FEATURE_FLAGS: dict[str, Any] = {
    "version": 1,
    "role_schema_version": ROLE_SCHEMA_VERSION,
    "updated_at": "",
    "features": {
        "smart_ask_workspace": {
            "label": "智能分析工作台",
            "description": "面向业务用户的问数、分析和报告生成入口。",
            "category": "导航入口",
            "module": "navigation",
            "module_label": "左侧导航栏",
            "kind": "navigation",
            "order": 10,
            "enabled": True,
            "roles": ["super_admin", "admin", "user"],
            "experimental": False,
        },
        "agent_management": {
            "label": "智能体编排配置",
            "description": "维护 Agent 流程、节点和执行策略。",
            "category": "导航入口",
            "module": "navigation",
            "module_label": "左侧导航栏",
            "kind": "navigation",
            "order": 20,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "dataset_management": {
            "label": "数据资产管理",
            "description": "维护数据集、字段语义和问数口径。",
            "category": "导航入口",
            "module": "navigation",
            "module_label": "左侧导航栏",
            "kind": "navigation",
            "order": 30,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "database_management": {
            "label": "数据连接管理",
            "description": "维护数据库连接和连通性测试。",
            "category": "导航入口",
            "module": "navigation",
            "module_label": "左侧导航栏",
            "kind": "navigation",
            "order": 40,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "ai_model_config": {
            "label": "模型服务配置",
            "description": "维护模型供应商、Key 和默认模型。",
            "category": "导航入口",
            "module": "navigation",
            "module_label": "左侧导航栏",
            "kind": "navigation",
            "order": 50,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "report_config": {
            "label": "报告模板配置",
            "description": "维护报告样式、指标卡和展示规则。",
            "category": "导航入口",
            "module": "navigation",
            "module_label": "左侧导航栏",
            "kind": "navigation",
            "order": 60,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "feishu_sync": {
            "label": "飞书数据同步",
            "description": "维护飞书表格同步任务。",
            "category": "导航入口",
            "module": "navigation",
            "module_label": "左侧导航栏",
            "kind": "navigation",
            "order": 70,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "runtime_migration": {
            "label": "迁移发布管理",
            "description": "导出、导入和备份运行态配置。",
            "category": "导航入口",
            "module": "navigation",
            "module_label": "左侧导航栏",
            "kind": "navigation",
            "order": 80,
            "enabled": True,
            "roles": ["super_admin"],
            "experimental": False,
        },
        "runtime_file_select": {
            "label": "选择导入包",
            "description": "迁移发布页，控制上传运行态 JSON 包。",
            "category": "按钮 · 迁移发布管理",
            "module": "runtime_migration",
            "module_label": "迁移发布管理",
            "kind": "button",
            "order": 805,
            "enabled": True,
            "roles": ["super_admin"],
            "experimental": False,
        },
        "runtime_export": {
            "label": "导出运行态包",
            "description": "迁移发布页，控制运行态包导出按钮。",
            "category": "按钮 · 迁移发布管理",
            "module": "runtime_migration",
            "module_label": "迁移发布管理",
            "kind": "button",
            "order": 810,
            "enabled": True,
            "roles": ["super_admin"],
            "experimental": False,
        },
        "runtime_backup": {
            "label": "手动备份",
            "description": "迁移发布页，控制手动备份当前环境按钮。",
            "category": "按钮 · 迁移发布管理",
            "module": "runtime_migration",
            "module_label": "迁移发布管理",
            "kind": "button",
            "order": 820,
            "enabled": True,
            "roles": ["super_admin"],
            "experimental": False,
        },
        "runtime_import_preview": {
            "label": "预检导入",
            "description": "迁移发布页，控制运行态包预检按钮。",
            "category": "按钮 · 迁移发布管理",
            "module": "runtime_migration",
            "module_label": "迁移发布管理",
            "kind": "button",
            "order": 830,
            "risk": "high",
            "enabled": True,
            "roles": ["super_admin"],
            "experimental": False,
        },
        "runtime_import_confirm": {
            "label": "确认导入",
            "description": "迁移发布页，控制正式写入运行态资源按钮。",
            "category": "按钮 · 迁移发布管理",
            "module": "runtime_migration",
            "module_label": "迁移发布管理",
            "kind": "button",
            "order": 840,
            "risk": "high",
            "enabled": True,
            "roles": ["super_admin"],
            "experimental": False,
        },
        "runtime_replace_mode": {
            "label": "替换模式",
            "description": "迁移发布页，控制替换书架表模式选项。",
            "category": "按钮 · 迁移发布管理",
            "module": "runtime_migration",
            "module_label": "迁移发布管理",
            "kind": "button",
            "order": 850,
            "risk": "high",
            "enabled": True,
            "roles": ["super_admin"],
            "experimental": False,
        },
        "runtime_overwrite_config": {
            "label": "覆盖 JSON",
            "description": "迁移发布页，控制覆盖已有 JSON 配置开关。",
            "category": "按钮 · 迁移发布管理",
            "module": "runtime_migration",
            "module_label": "迁移发布管理",
            "kind": "button",
            "order": 860,
            "risk": "high",
            "enabled": True,
            "roles": ["super_admin"],
            "experimental": False,
        },
        "organization_tree_management": {
            "label": "组织树管理",
            "description": "维护多套独立组织树类型和树形节点。",
            "category": "导航入口",
            "module": "navigation",
            "module_label": "左侧导航栏",
            "kind": "navigation",
            "order": 88,
            "enabled": True,
            "roles": ["super_admin"],
            "experimental": False,
        },
        "organization_tree_edit": {
            "label": "维护组织树",
            "description": "控制组织树类型和节点的新增、编辑、删除操作。",
            "category": "按钮 · 组织树管理",
            "module": "organization_tree_management",
            "module_label": "组织树管理",
            "kind": "button",
            "order": 881,
            "enabled": True,
            "roles": ["super_admin"],
            "experimental": False,
        },
        "employee_permissions": {
            "label": "角色权限管理",
            "description": "维护 RBAC 角色、用户分组、账号状态和飞书 UnionID 映射。",
            "category": "导航入口",
            "module": "navigation",
            "module_label": "左侧导航栏",
            "kind": "navigation",
            "order": 90,
            "enabled": True,
            "roles": ["super_admin"],
            "experimental": False,
        },
        "admin_console": {
            "label": "系统控制台",
            "description": "超级管理员专用，用于控制功能入口和按钮开放范围。",
            "category": "导航入口",
            "module": "navigation",
            "module_label": "左侧导航栏",
            "kind": "navigation",
            "order": 100,
            "enabled": True,
            "roles": ["super_admin"],
            "experimental": False,
        },
        "app_password_change": {
            "label": "修改密码",
            "description": "右上角账号菜单里的修改密码入口。",
            "category": "按钮 · 全局顶部栏",
            "module": "global_shell",
            "module_label": "全局顶部栏",
            "kind": "button",
            "order": 105,
            "enabled": True,
            "roles": ["super_admin", "admin", "user"],
            "experimental": False,
        },
        "app_history_clear": {
            "label": "清空历史",
            "description": "智能分析页左侧历史区和抽屉里的清空按钮。",
            "category": "按钮 · 全局侧边栏",
            "module": "global_shell",
            "module_label": "全局侧边栏",
            "kind": "button",
            "order": 106,
            "risk": "high",
            "enabled": True,
            "roles": ["super_admin", "admin", "user"],
            "experimental": False,
        },
        "app_history_delete": {
            "label": "删除单条历史",
            "description": "智能分析页历史卡片右侧的单条删除按钮。",
            "category": "按钮 · 全局侧边栏",
            "module": "global_shell",
            "module_label": "全局侧边栏",
            "kind": "button",
            "order": 107,
            "risk": "high",
            "enabled": True,
            "roles": ["super_admin", "admin", "user"],
            "experimental": False,
        },
        "employee_permission_edit": {
            "label": "保存/新增",
            "description": "员工权限页，控制保存配置和新增员工。",
            "category": "按钮 · 员工权限配置",
            "module": "employee_permissions",
            "module_label": "员工权限配置",
            "kind": "button",
            "order": 910,
            "enabled": True,
            "roles": ["super_admin"],
            "experimental": False,
        },
        "employee_create": {
            "label": "新增员工",
            "description": "员工权限页，控制新增账号按钮和新增保存。",
            "category": "按钮 · 员工权限配置",
            "module": "employee_permissions",
            "module_label": "员工权限配置",
            "kind": "button",
            "order": 911,
            "enabled": True,
            "roles": ["super_admin"],
            "experimental": False,
        },
        "employee_update": {
            "label": "编辑员工",
            "description": "员工权限页，控制编辑账号按钮和编辑保存。",
            "category": "按钮 · 员工权限配置",
            "module": "employee_permissions",
            "module_label": "员工权限配置",
            "kind": "button",
            "order": 912,
            "enabled": True,
            "roles": ["super_admin"],
            "experimental": False,
        },
        "employee_status_update": {
            "label": "启停员工",
            "description": "员工权限页，控制账号状态开关。",
            "category": "按钮 · 员工权限配置",
            "module": "employee_permissions",
            "module_label": "员工权限配置",
            "kind": "button",
            "order": 913,
            "enabled": True,
            "roles": ["super_admin"],
            "experimental": False,
        },
        "employee_bulk_update": {
            "label": "批量修改员工",
            "description": "员工权限页，控制批量修改角色、组织和状态。",
            "category": "按钮 · 员工权限配置",
            "module": "employee_permissions",
            "module_label": "员工权限配置",
            "kind": "button",
            "order": 914,
            "enabled": True,
            "roles": ["super_admin"],
            "experimental": False,
        },
        "employee_password_reset": {
            "label": "重置密码",
            "description": "员工权限页，控制默认密码重置入口。",
            "category": "按钮 · 员工权限配置",
            "module": "employee_permissions",
            "module_label": "员工权限配置",
            "kind": "button",
            "order": 920,
            "risk": "high",
            "enabled": True,
            "roles": ["super_admin"],
            "experimental": False,
        },
        "employee_delete": {
            "label": "删除员工",
            "description": "员工权限页，控制员工账号删除入口。",
            "category": "按钮 · 员工权限配置",
            "module": "employee_permissions",
            "module_label": "员工权限配置",
            "kind": "button",
            "order": 930,
            "risk": "high",
            "enabled": True,
            "roles": ["super_admin"],
            "experimental": False,
        },
        "organization_tree_type_create": {
            "label": "新增组织树",
            "description": "组织树管理页，控制新增组织树类型。",
            "category": "按钮 · 组织树管理",
            "module": "organization_tree_management",
            "module_label": "组织树管理",
            "kind": "button",
            "order": 882,
            "enabled": True,
            "roles": ["super_admin"],
            "experimental": False,
        },
        "organization_tree_type_update": {
            "label": "编辑组织树",
            "description": "组织树管理页，控制编辑组织树类型。",
            "category": "按钮 · 组织树管理",
            "module": "organization_tree_management",
            "module_label": "组织树管理",
            "kind": "button",
            "order": 883,
            "enabled": True,
            "roles": ["super_admin"],
            "experimental": False,
        },
        "organization_tree_type_delete": {
            "label": "删除组织树",
            "description": "组织树管理页，控制删除组织树类型。",
            "category": "按钮 · 组织树管理",
            "module": "organization_tree_management",
            "module_label": "组织树管理",
            "kind": "button",
            "order": 884,
            "risk": "high",
            "enabled": True,
            "roles": ["super_admin"],
            "experimental": False,
        },
        "organization_tree_node_create": {
            "label": "新增组织节点",
            "description": "组织树管理页，控制新增根节点和新增下级。",
            "category": "按钮 · 组织树管理",
            "module": "organization_tree_management",
            "module_label": "组织树管理",
            "kind": "button",
            "order": 885,
            "enabled": True,
            "roles": ["super_admin"],
            "experimental": False,
        },
        "organization_tree_node_update": {
            "label": "编辑组织节点",
            "description": "组织树管理页，控制编辑组织节点。",
            "category": "按钮 · 组织树管理",
            "module": "organization_tree_management",
            "module_label": "组织树管理",
            "kind": "button",
            "order": 886,
            "enabled": True,
            "roles": ["super_admin"],
            "experimental": False,
        },
        "organization_tree_node_delete": {
            "label": "删除组织节点",
            "description": "组织树管理页，控制删除组织节点。",
            "category": "按钮 · 组织树管理",
            "module": "organization_tree_management",
            "module_label": "组织树管理",
            "kind": "button",
            "order": 887,
            "risk": "high",
            "enabled": True,
            "roles": ["super_admin"],
            "experimental": False,
        },
        "organization_tree_import_preview": {
            "label": "预检导入组织树",
            "description": "组织树管理页，控制组织树导入预检。",
            "category": "按钮 · 组织树管理",
            "module": "organization_tree_management",
            "module_label": "组织树管理",
            "kind": "button",
            "order": 888,
            "enabled": True,
            "roles": ["super_admin"],
            "experimental": False,
        },
        "organization_tree_import_apply": {
            "label": "确认导入组织树",
            "description": "组织树管理页，控制确认写入组织树导入结果。",
            "category": "按钮 · 组织树管理",
            "module": "organization_tree_management",
            "module_label": "组织树管理",
            "kind": "button",
            "order": 889,
            "risk": "high",
            "enabled": True,
            "roles": ["super_admin"],
            "experimental": False,
        },
        "dataset_create": {
            "label": "新建数据集",
            "description": "数据资产页，控制左侧数据集新建按钮。",
            "category": "按钮 · 数据资产管理",
            "module": "dataset_management",
            "module_label": "数据资产管理",
            "kind": "button",
            "order": 310,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "dataset_save": {
            "label": "保存书架",
            "description": "数据资产页，控制保存书架内容按钮。",
            "category": "按钮 · 数据资产管理",
            "module": "dataset_management",
            "module_label": "数据资产管理",
            "kind": "button",
            "order": 320,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "dataset_delete": {
            "label": "删除数据集",
            "description": "数据资产页，控制删除当前数据集按钮。",
            "category": "按钮 · 数据资产管理",
            "module": "dataset_management",
            "module_label": "数据资产管理",
            "kind": "button",
            "order": 330,
            "risk": "high",
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": True,
        },
        "dataset_prompt_generate": {
            "label": "提示词生成",
            "description": "数据资产页，控制左侧根据提示词生成数据集按钮。",
            "category": "按钮 · 数据资产管理",
            "module": "dataset_management",
            "module_label": "数据资产管理",
            "kind": "button",
            "order": 335,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": True,
        },
        "dataset_autofill": {
            "label": "自动补齐",
            "description": "数据资产页，控制基于 DDL 和数据集信息的智能补齐按钮。",
            "category": "按钮 · 数据资产管理",
            "module": "dataset_management",
            "module_label": "数据资产管理",
            "kind": "button",
            "order": 340,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": True,
        },
        "dataset_question_edit": {
            "label": "常见问题维护",
            "description": "数据资产页，控制常见问题新增、编辑、删除。",
            "category": "按钮 · 数据资产管理",
            "module": "dataset_management",
            "module_label": "数据资产管理",
            "kind": "button",
            "order": 350,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "dataset_regression_edit": {
            "label": "回归题维护",
            "description": "数据资产页，控制回归题新增、编辑、删除。",
            "category": "按钮 · 数据资产管理",
            "module": "dataset_management",
            "module_label": "数据资产管理",
            "kind": "button",
            "order": 360,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "dataset_synonym_edit": {
            "label": "路由词维护",
            "description": "数据资产页，控制路由词新增、编辑、删除。",
            "category": "按钮 · 数据资产管理",
            "module": "dataset_management",
            "module_label": "数据资产管理",
            "kind": "button",
            "order": 370,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "dataset_lld_edit": {
            "label": "LLD 维护",
            "description": "数据资产页，控制 LLD 新增、编辑、删除。",
            "category": "按钮 · 数据资产管理",
            "module": "dataset_management",
            "module_label": "数据资产管理",
            "kind": "button",
            "order": 380,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "dataset_dict_edit": {
            "label": "字段维护",
            "description": "数据资产页，控制字段字典新增、编辑、删除。",
            "category": "按钮 · 数据资产管理",
            "module": "dataset_management",
            "module_label": "数据资产管理",
            "kind": "button",
            "order": 390,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "dataset_dict_extract": {
            "label": "DDL 提取字段",
            "description": "数据资产页，控制从 DDL 提取字段按钮。",
            "category": "按钮 · 数据资产管理",
            "module": "dataset_management",
            "module_label": "数据资产管理",
            "kind": "button",
            "order": 400,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "dataset_source_table": {
            "label": "从数据源拉表",
            "description": "数据资产页，控制从数据源拉表和加入当前数据集按钮。",
            "category": "按钮 · 数据资产管理",
            "module": "dataset_management",
            "module_label": "数据资产管理",
            "kind": "button",
            "order": 405,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "dataset_schema_edit": {
            "label": "表结构维护",
            "description": "数据资产页，控制拉表、DDL、关联和表结构保存。",
            "category": "按钮 · 数据资产管理",
            "module": "dataset_management",
            "module_label": "数据资产管理",
            "kind": "button",
            "order": 410,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "dataset_relation_edit": {
            "label": "表关联维护",
            "description": "数据资产页，控制表关联新增、编辑、删除。",
            "category": "按钮 · 数据资产管理",
            "module": "dataset_management",
            "module_label": "数据资产管理",
            "kind": "button",
            "order": 415,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "dataset_golden_edit": {
            "label": "训练实例维护",
            "description": "数据资产页，控制 Golden SQL 新增、编辑、删除。",
            "category": "按钮 · 数据资产管理",
            "module": "dataset_management",
            "module_label": "数据资产管理",
            "kind": "button",
            "order": 420,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "dataset_prompt_edit": {
            "label": "提示词维护",
            "description": "数据资产页，控制 Agent 提示词片段新增、编辑、删除。",
            "category": "按钮 · 数据资产管理",
            "module": "dataset_management",
            "module_label": "数据资产管理",
            "kind": "button",
            "order": 430,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "dataset_extcfg_edit": {
            "label": "扩展配置维护",
            "description": "数据资产页，控制外部配置新增、编辑、删除。",
            "category": "按钮 · 数据资产管理",
            "module": "dataset_management",
            "module_label": "数据资产管理",
            "kind": "button",
            "order": 440,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "dataset_sql_preview_run": {
            "label": "执行 SQL 测试",
            "description": "数据资产页，控制 SQL 测试页签内的执行 SQL 按钮。",
            "category": "按钮 · 数据资产管理",
            "module": "dataset_management",
            "module_label": "数据资产管理",
            "kind": "button",
            "order": 445,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "dataset_sql_preview_copy": {
            "label": "复制 SQL 测试结果",
            "description": "数据资产页，控制 SQL 测试结果的复制表格和复制 JSON 按钮。",
            "category": "按钮 · 数据资产管理",
            "module": "dataset_management",
            "module_label": "数据资产管理",
            "kind": "button",
            "order": 446,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "datasource_create": {
            "label": "添加数据源",
            "description": "数据连接页，控制添加数据源按钮。",
            "category": "按钮 · 数据连接管理",
            "module": "database_management",
            "module_label": "数据连接管理",
            "kind": "button",
            "order": 410,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "datasource_test": {
            "label": "测试连接",
            "description": "数据连接页，控制单个和批量测试连接按钮。",
            "category": "按钮 · 数据连接管理",
            "module": "database_management",
            "module_label": "数据连接管理",
            "kind": "button",
            "order": 420,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "datasource_edit": {
            "label": "编辑保存",
            "description": "数据连接页，控制编辑数据源和保存弹窗按钮。",
            "category": "按钮 · 数据连接管理",
            "module": "database_management",
            "module_label": "数据连接管理",
            "kind": "button",
            "order": 425,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "datasource_delete": {
            "label": "删除数据源",
            "description": "数据连接页，控制删除数据源按钮。",
            "category": "按钮 · 数据连接管理",
            "module": "database_management",
            "module_label": "数据连接管理",
            "kind": "button",
            "order": 430,
            "risk": "high",
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": True,
        },
        "agent_config_edit": {
            "label": "保存配置",
            "description": "智能体页，控制保存配置和知识片段维护。",
            "category": "按钮 · 智能体编排配置",
            "module": "agent_management",
            "module_label": "智能体编排配置",
            "kind": "button",
            "order": 210,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "ai_channel_edit": {
            "label": "通道维护",
            "description": "模型服务页，控制通道新增、名称、图标和 API Key。",
            "category": "按钮 · 模型服务配置",
            "module": "ai_model_config",
            "module_label": "模型服务配置",
            "kind": "button",
            "order": 510,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "ai_model_edit": {
            "label": "模型维护",
            "description": "模型服务页，控制模型新增、编辑、设默认和删除。",
            "category": "按钮 · 模型服务配置",
            "module": "ai_model_config",
            "module_label": "模型服务配置",
            "kind": "button",
            "order": 520,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "ai_model_test": {
            "label": "连接测试",
            "description": "模型服务页，控制模型测试和全部检测按钮。",
            "category": "按钮 · 模型服务配置",
            "module": "ai_model_config",
            "module_label": "模型服务配置",
            "kind": "button",
            "order": 530,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "report_template_edit": {
            "label": "模板编辑",
            "description": "报告模板页，控制添加、解析 JSON、重置和保存。",
            "category": "按钮 · 报告模板配置",
            "module": "report_config",
            "module_label": "报告模板配置",
            "kind": "button",
            "order": 610,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "report_template_delete": {
            "label": "删除配置",
            "description": "报告模板页，控制删除模板配置按钮。",
            "category": "按钮 · 报告模板配置",
            "module": "report_config",
            "module_label": "报告模板配置",
            "kind": "button",
            "order": 620,
            "risk": "high",
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": True,
        },
        "feishu_sync_edit": {
            "label": "任务维护",
            "description": "飞书同步页，控制新建、编辑、保存和删除任务。",
            "category": "按钮 · 飞书数据同步",
            "module": "feishu_sync",
            "module_label": "飞书数据同步",
            "kind": "button",
            "order": 710,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "feishu_sync_run": {
            "label": "同步启停",
            "description": "飞书同步页，控制同步、暂停和恢复按钮。",
            "category": "按钮 · 飞书数据同步",
            "module": "feishu_sync",
            "module_label": "飞书数据同步",
            "kind": "button",
            "order": 720,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "feishu_sync_test": {
            "label": "测试预览",
            "description": "飞书同步页，控制连接测试、链接解析和字段预览。",
            "category": "按钮 · 飞书数据同步",
            "module": "feishu_sync",
            "module_label": "飞书数据同步",
            "kind": "button",
            "order": 730,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "feishu_log_clear": {
            "label": "清空日志",
            "description": "飞书同步页，控制日志弹窗里的清空按钮。",
            "category": "按钮 · 飞书数据同步",
            "module": "feishu_sync",
            "module_label": "飞书数据同步",
            "kind": "button",
            "order": 740,
            "risk": "high",
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "report_fullscreen": {
            "label": "全屏报告",
            "description": "智能分析页，控制经营报告全屏查看入口。",
            "category": "体验开关",
            "module": "smart_ask_workspace",
            "module_label": "智能分析工作台",
            "kind": "button",
            "order": 130,
            "enabled": True,
            "roles": ["super_admin", "admin", "user"],
            "experimental": False,
        },
        "chart_viewer": {
            "label": "图表放大",
            "description": "智能分析页，控制图表放大查看按钮。",
            "category": "体验开关",
            "module": "smart_ask_workspace",
            "module_label": "智能分析工作台",
            "kind": "button",
            "order": 120,
            "enabled": True,
            "roles": ["super_admin", "admin", "user"],
            "experimental": False,
        },
        "debug_execution_trace": {
            "label": "执行详情",
            "description": "智能分析页，控制右侧执行轨迹详情入口。",
            "category": "体验开关",
            "module": "smart_ask_workspace",
            "module_label": "智能分析工作台",
            "kind": "button",
            "order": 110,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": True,
        },
        "smart_new_chat": {
            "label": "新会话",
            "description": "智能分析页，控制顶部新会话按钮。",
            "category": "体验开关",
            "module": "smart_ask_workspace",
            "module_label": "智能分析工作台",
            "kind": "button",
            "order": 140,
            "enabled": True,
            "roles": ["super_admin", "admin", "user"],
            "experimental": False,
        },
        "smart_send_question": {
            "label": "发送问题",
            "description": "智能分析页，控制输入区发送按钮。",
            "category": "体验开关",
            "module": "smart_ask_workspace",
            "module_label": "智能分析工作台",
            "kind": "button",
            "order": 150,
            "enabled": True,
            "roles": ["super_admin", "admin", "user"],
            "experimental": False,
        },
        "smart_stop_run": {
            "label": "停止执行",
            "description": "智能分析页，控制问数运行中的停止按钮。",
            "category": "体验开关",
            "module": "smart_ask_workspace",
            "module_label": "智能分析工作台",
            "kind": "button",
            "order": 160,
            "enabled": True,
            "roles": ["super_admin", "admin", "user"],
            "experimental": False,
        },
        "smart_confirm_scope": {
            "label": "确认口径",
            "description": "智能分析页，控制候选口径卡片选择按钮。",
            "category": "体验开关",
            "module": "smart_ask_workspace",
            "module_label": "智能分析工作台",
            "kind": "button",
            "order": 165,
            "enabled": True,
            "roles": ["super_admin", "admin", "user"],
            "experimental": False,
        },
        "smart_submit_note": {
            "label": "补充说明",
            "description": "智能分析页，控制确认卡片里的发送补充说明按钮。",
            "category": "体验开关",
            "module": "smart_ask_workspace",
            "module_label": "智能分析工作台",
            "kind": "button",
            "order": 166,
            "enabled": True,
            "roles": ["super_admin", "admin", "user"],
            "experimental": False,
        },
        "smart_report_download": {
            "label": "下载报告",
            "description": "智能分析页，控制报告下载/导出按钮。",
            "category": "体验开关",
            "module": "smart_ask_workspace",
            "module_label": "智能分析工作台",
            "kind": "button",
            "order": 170,
            "enabled": True,
            "roles": ["super_admin", "admin", "user"],
            "experimental": False,
        },
        "smart_sql_copy": {
            "label": "复制 SQL",
            "description": "智能分析页，控制 SQL 块右上角复制按钮。",
            "category": "体验开关",
            "module": "smart_ask_workspace",
            "module_label": "智能分析工作台",
            "kind": "button",
            "order": 180,
            "enabled": True,
            "roles": ["super_admin", "admin", "user"],
            "experimental": False,
        },
        "smart_question_copy": {
            "label": "复制问题",
            "description": "智能分析页，控制用户问题气泡上的复制按钮。",
            "category": "按钮 · 智能分析工作台",
            "module": "smart_ask_workspace",
            "module_label": "智能分析工作台",
            "kind": "button",
            "order": 190,
            "enabled": True,
            "roles": ["super_admin", "admin", "user"],
            "experimental": False,
        },
        "smart_question_edit": {
            "label": "修改问题",
            "description": "智能分析页，控制用户问题气泡上的修改按钮。",
            "category": "按钮 · 智能分析工作台",
            "module": "smart_ask_workspace",
            "module_label": "智能分析工作台",
            "kind": "button",
            "order": 191,
            "enabled": True,
            "roles": ["super_admin", "admin", "user"],
            "experimental": False,
        },
        "smart_question_rerun": {
            "label": "重新问",
            "description": "智能分析页，控制用户问题气泡上的重新执行按钮。",
            "category": "按钮 · 智能分析工作台",
            "module": "smart_ask_workspace",
            "module_label": "智能分析工作台",
            "kind": "button",
            "order": 192,
            "enabled": True,
            "roles": ["super_admin", "admin", "user"],
            "experimental": False,
        },
        "smart_dataset_select": {
            "label": "选择数据集",
            "description": "智能分析页，控制底部输入区的数据集选择器。",
            "category": "按钮 · 智能分析工作台",
            "module": "smart_ask_workspace",
            "module_label": "智能分析工作台",
            "kind": "button",
            "order": 193,
            "enabled": True,
            "roles": ["super_admin", "admin", "user"],
            "experimental": False,
        },
        "smart_model_select": {
            "label": "选择模型",
            "description": "智能分析页，控制底部输入区的模型选择器。",
            "category": "按钮 · 智能分析工作台",
            "module": "smart_ask_workspace",
            "module_label": "智能分析工作台",
            "kind": "button",
            "order": 194,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
        "smart_quick_ask": {
            "label": "常用问题带入",
            "description": "智能分析页，控制欢迎页常用问题点击带入。",
            "category": "按钮 · 智能分析工作台",
            "module": "smart_ask_workspace",
            "module_label": "智能分析工作台",
            "kind": "button",
            "order": 195,
            "enabled": True,
            "roles": ["super_admin", "admin", "user"],
            "experimental": False,
        },
        "smart_quick_refresh": {
            "label": "刷新常用问题",
            "description": "智能分析页，控制欢迎页换一批常用问题按钮。",
            "category": "按钮 · 智能分析工作台",
            "module": "smart_ask_workspace",
            "module_label": "智能分析工作台",
            "kind": "button",
            "order": 196,
            "enabled": True,
            "roles": ["super_admin", "admin", "user"],
            "experimental": False,
        },
        "smart_chart_auto_infer": {
            "label": "自动推荐图表",
            "description": "智能分析页，当后端报告未返回图表配置时，允许前端按结果字段兜底生成推荐图表。",
            "category": "按钮 · 智能分析工作台",
            "module": "smart_ask_workspace",
            "module_label": "智能分析工作台",
            "kind": "button",
            "order": 197,
            "enabled": True,
            "roles": ["super_admin", "admin", "user"],
            "experimental": False,
        },
    },
}


_DATASET_ITEM_ACTIONS = {
    "question": ("常见问题", 350),
    "regression": ("回归题", 360),
    "synonym": ("路由词", 370),
    "lld": ("LLD", 380),
    "dict": ("字段", 390),
    "schema": ("DDL", 410),
    "relation": ("表关联", 415),
    "golden": ("训练实例", 420),
    "prompt": ("提示词片段", 430),
    "extcfg": ("扩展配置", 440),
}

_DATASET_ACTION_LABELS = {
    "create": ("新增", "新增"),
    "update": ("编辑", "编辑"),
    "delete": ("删除", "删除"),
}

for _item_key, (_item_label, _base_order) in _DATASET_ITEM_ACTIONS.items():
    for _offset, (_action_key, (_action_label, _action_desc)) in enumerate(_DATASET_ACTION_LABELS.items(), start=1):
        DEFAULT_FEATURE_FLAGS["features"].setdefault(
            f"dataset_{_item_key}_{_action_key}",
            {
                "label": f"{_action_label}{_item_label}",
                "description": f"数据资产页，控制{_item_label}{_action_desc}按钮。",
                "category": "按钮 · 数据资产管理",
                "module": "dataset_management",
                "module_label": "数据资产管理",
                "kind": "button",
                "order": _base_order + _offset,
                "risk": "high" if _action_key == "delete" else "normal",
                "enabled": True,
                "roles": ["super_admin", "admin"],
                "experimental": False,
            },
        )

_DATASET_LEGACY_MAINTENANCE_KEYS = {
    "dataset_question_edit",
    "dataset_regression_edit",
    "dataset_synonym_edit",
    "dataset_lld_edit",
    "dataset_dict_edit",
    "dataset_schema_edit",
    "dataset_relation_edit",
    "dataset_golden_edit",
    "dataset_prompt_edit",
    "dataset_extcfg_edit",
}
_MANAGEMENT_LEGACY_KEYS = {
    "employee_permission_edit",
    "organization_tree_edit",
}
_FEISHU_ACTION_FEATURES = {
    "feishu_sync_create": ("新建同步任务", "飞书同步页，控制新建同步任务按钮。", 711, ""),
    "feishu_sync_update": ("编辑同步任务", "飞书同步页，控制编辑和保存同步任务。", 712, ""),
    "feishu_sync_delete": ("删除同步任务", "飞书同步页，控制删除同步任务。", 713, "high"),
    "feishu_sync_start": ("立即同步", "飞书同步页，控制立即同步和批量启动同步。", 721, ""),
    "feishu_sync_pause": ("暂停同步任务", "飞书同步页，控制暂停同步任务。", 722, ""),
    "feishu_sync_resume": ("恢复同步任务", "飞书同步页，控制恢复同步任务。", 723, ""),
    "feishu_connection_test": ("测试飞书连接", "飞书同步页，控制测试连接按钮。", 731, ""),
    "feishu_link_parse": ("解析飞书链接", "飞书同步页，控制飞书多维表格链接解析按钮。", 732, ""),
    "feishu_schema_preview": ("预览飞书字段", "飞书同步页，控制字段元数据和样本预览按钮。", 733, ""),
    "feishu_log_view": ("查看同步日志", "飞书同步页，控制查看和刷新同步日志。", 741, ""),
}
_FEISHU_LEGACY_KEYS = {
    "feishu_sync_edit",
    "feishu_sync_run",
    "feishu_sync_test",
}

for _legacy_key in _DATASET_LEGACY_MAINTENANCE_KEYS:
    DEFAULT_FEATURE_FLAGS["features"].pop(_legacy_key, None)
for _legacy_key in _MANAGEMENT_LEGACY_KEYS:
    DEFAULT_FEATURE_FLAGS["features"].pop(_legacy_key, None)
for _legacy_key in _FEISHU_LEGACY_KEYS:
    DEFAULT_FEATURE_FLAGS["features"].pop(_legacy_key, None)
for _key, (_label, _description, _order, _risk) in _FEISHU_ACTION_FEATURES.items():
    DEFAULT_FEATURE_FLAGS["features"].setdefault(
        _key,
        {
            "label": _label,
            "description": _description,
            "category": "按钮 · 飞书数据同步",
            "module": "feishu_sync",
            "module_label": "飞书数据同步",
            "kind": "button",
            "order": _order,
            "risk": _risk,
            "enabled": True,
            "roles": ["super_admin", "admin"],
            "experimental": False,
        },
    )

_BUSINESS_ADMIN_DEFAULT_FEATURES = {
    "smart_ask_workspace",
    "app_password_change",
    "app_history_clear",
    "app_history_delete",
    "dataset_management",
    "dataset_save",
    "dataset_prompt_generate",
    "dataset_dict_extract",
    "dataset_source_table",
    "dataset_sql_preview_run",
    "dataset_sql_preview_copy",
    "report_config",
    "report_template_edit",
    "report_fullscreen",
    "chart_viewer",
    "smart_new_chat",
    "smart_send_question",
    "smart_stop_run",
    "smart_confirm_scope",
    "smart_submit_note",
    "smart_report_download",
    "smart_sql_copy",
    "smart_question_copy",
    "smart_question_edit",
    "smart_question_rerun",
    "smart_dataset_select",
    "smart_quick_ask",
    "smart_quick_refresh",
    "smart_chart_auto_infer",
}
_BUSINESS_ADMIN_DATASET_MAINTENANCE_PREFIXES = (
    "dataset_question_",
    "dataset_regression_",
    "dataset_synonym_",
    "dataset_lld_",
    "dataset_dict_",
    "dataset_schema_",
    "dataset_relation_",
    "dataset_golden_",
    "dataset_prompt_",
    "dataset_extcfg_",
)
for _feature_key, _feature in DEFAULT_FEATURE_FLAGS["features"].items():
    if (
        _feature_key in _BUSINESS_ADMIN_DEFAULT_FEATURES
        or (
            _feature_key.startswith(_BUSINESS_ADMIN_DATASET_MAINTENANCE_PREFIXES)
            and not _feature_key.endswith("_delete")
        )
    ):
        _feature.setdefault("roles", [])
        if "business_admin" not in _feature["roles"]:
            _feature["roles"].append("business_admin")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _role_allowed(user_role: str, allowed_roles: list[str]) -> bool:
    return user_role in allowed_roles


def _clean_roles(value: Any, fallback: list[str]) -> list[str]:
    if not isinstance(value, list):
        return list(fallback)
    return [str(item).strip() for item in value if str(item).strip() in VALID_ROLES]


def _merge_feature(default_feature: dict[str, Any], current: Any) -> dict[str, Any]:
    merged = deepcopy(default_feature)
    if isinstance(current, dict):
        merged["enabled"] = bool(current.get("enabled", merged.get("enabled", True)))
        merged["roles"] = _clean_roles(current.get("roles"), merged.get("roles", []))
        merged["experimental"] = bool(current.get("experimental", merged.get("experimental", False)))
    merged.setdefault("module", "other")
    merged.setdefault("module_label", merged.get("category") or "其他")
    merged.setdefault("kind", "button")
    merged.setdefault("order", 999)
    merged.setdefault("risk", "")
    return merged


def _role_schema_version(data: dict[str, Any]) -> int:
    try:
        return int(data.get("role_schema_version") or 1)
    except (TypeError, ValueError):
        return 1


def _migrate_builtin_role_matrix(result: dict[str, Any], data: dict[str, Any]) -> None:
    if _role_schema_version(data) >= ROLE_SCHEMA_VERSION:
        result["role_schema_version"] = ROLE_SCHEMA_VERSION
        return
    features = result.get("features") if isinstance(result.get("features"), dict) else {}
    for key, default_feature in DEFAULT_FEATURE_FLAGS["features"].items():
        if "business_admin" not in set(default_feature.get("roles") or []):
            continue
        feature = features.get(key)
        if not isinstance(feature, dict):
            continue
        roles = feature.get("roles") if isinstance(feature.get("roles"), list) else []
        if "business_admin" not in roles:
            roles.append("business_admin")
        feature["roles"] = _clean_roles(roles, default_feature.get("roles", []))
    result["role_schema_version"] = ROLE_SCHEMA_VERSION


def load_feature_flags() -> dict[str, Any]:
    data = read_json(FEATURE_FLAGS_FILE)
    if not isinstance(data, dict):
        data = {}
    result = deepcopy(DEFAULT_FEATURE_FLAGS)
    current_features = data.get("features") if isinstance(data.get("features"), dict) else {}
    for key, default_feature in DEFAULT_FEATURE_FLAGS["features"].items():
        result["features"][key] = _merge_feature(default_feature, current_features.get(key))
    legacy_keys = {"danger_delete_buttons", "runtime_import"} | _DATASET_LEGACY_MAINTENANCE_KEYS | _MANAGEMENT_LEGACY_KEYS | _FEISHU_LEGACY_KEYS
    for key, feature in current_features.items():
        if key in legacy_keys:
            continue
        if key not in result["features"] and isinstance(feature, dict):
            result["features"][key] = _merge_feature(
                {
                    "label": str(feature.get("label") or key),
                    "description": str(feature.get("description") or ""),
                    "category": str(feature.get("category") or "自定义"),
                    "enabled": bool(feature.get("enabled", False)),
                    "roles": ["super_admin"],
                    "experimental": bool(feature.get("experimental", True)),
                },
                feature,
            )
    result["updated_at"] = str(data.get("updated_at") or result.get("updated_at") or "")
    _migrate_builtin_role_matrix(result, data)
    return result


def ensure_feature_flags() -> dict[str, Any]:
    flags = load_feature_flags()
    write_json(FEATURE_FLAGS_FILE, flags)
    return flags


def save_feature_flags(payload: dict[str, Any], operator: str = "") -> dict[str, Any]:
    current = load_feature_flags()
    incoming = payload.get("features") if isinstance(payload, dict) else None
    if not isinstance(incoming, dict):
        raise ValueError("features 必须是对象")

    for key, value in incoming.items():
        if key not in current["features"] or not isinstance(value, dict):
            continue
        feature = current["features"][key]
        if key == "admin_console":
            feature["enabled"] = True
            feature["roles"] = ["super_admin"]
            continue
        feature["enabled"] = bool(value.get("enabled", feature.get("enabled", True)))
        feature["roles"] = _clean_roles(value.get("roles"), feature.get("roles", []))
        feature["experimental"] = bool(value.get("experimental", feature.get("experimental", False)))

    current["updated_at"] = _now()
    current["updated_by"] = operator or ""
    write_json(FEATURE_FLAGS_FILE, current)
    _sync_builtin_role_permissions(current, operator=operator)
    return current


def _sync_builtin_role_permissions(flags: dict[str, Any], operator: str = "") -> None:
    """Keep the role-permission file aligned with the console matrix.

    The system console is the operational UI for feature permissions. Older
    code also persisted function permissions in rbac_permissions.json, so a
    stale RBAC file could hide a feature that the console had just granted.
    """
    try:
        from rbac_store import BUILTIN_ROLE_IDS, load_rbac, save_rbac

        rbac = load_rbac(flags)
        features = flags.get("features") if isinstance(flags.get("features"), dict) else {}
        role_functions = {role_id: [] for role_id in BUILTIN_ROLE_IDS}
        for key, feature in features.items():
            if not isinstance(feature, dict) or not feature.get("enabled", False):
                continue
            for role_id in feature.get("roles") or []:
                if role_id in role_functions:
                    role_functions[role_id].append(str(key))
        for role in rbac.get("roles") or []:
            if role.get("id") in role_functions:
                role["function_permissions"] = sorted(set(role_functions[role["id"]]))
        save_rbac(rbac, flags, operator=operator)
    except Exception as exc:
        print(f"同步功能权限到 RBAC 失败: {exc}")


def view_for_user(flags: dict[str, Any], user: dict[str, Any] | None) -> dict[str, Any]:
    role = (user or {}).get("role") or "user"
    result = deepcopy(flags)
    for key, feature in result.get("features", {}).items():
        roles = feature.get("roles") if isinstance(feature.get("roles"), list) else []
        feature["available"] = bool(feature.get("enabled", False)) and _role_allowed(role, roles)
    return result


def feature_available(key: str, user: dict[str, Any] | None) -> bool:
    flags = load_feature_flags()
    feature = flags.get("features", {}).get(key)
    if not isinstance(feature, dict):
        return True
    roles = feature.get("roles") if isinstance(feature.get("roles"), list) else []
    role = (user or {}).get("role") or "user"
    return bool(feature.get("enabled", False)) and _role_allowed(role, roles)

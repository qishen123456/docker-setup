"""
SQL提示词配置管理器
支持前端配置SQL生成提示词
"""

import json
import os
from typing import Dict, Optional, List

class SQLPromptManager:
    def __init__(self):
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'sql_prompts.json')
        self.prompts = {}
        self.settings = {}
        self.load_config()
    
    def load_config(self):
        """加载SQL提示词配置"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.prompts = config.get('sql_generation_prompts', {})
                    self.settings = config.get('global_settings', {})
            else:
                self.create_default_config()
        except Exception as e:
            print(f"加载SQL提示词配置失败: {e}")
            self.create_default_config()
    
    def create_default_config(self):
        """创建默认配置"""
        self.prompts = {
            "default": {
                "name": "默认SQL生成提示词",
                "content": "你是一个SQL专家。重要提示：\n1. 当前连接的数据库是：{database_name} ({database_type})\n2. 请根据这个数据源的特点生成SQL\n3. 确保生成的SQL只包含这个数据库中存在的表和字段\n4. 生成只读SQL（SELECT/WITH/SHOW）\n5. 自动限制返回最多100行数据",
                "is_active": True
            }
        }
        self.settings = {
            "default_prompt_id": "default",
            "allow_frontend_override": True,
            "max_sql_rows": 100,
            "enforce_read_only": True
        }
        self.save_config()
    
    def save_config(self):
        """保存配置到文件"""
        try:
            config = {
                "sql_generation_prompts": self.prompts,
                "global_settings": self.settings
            }
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存SQL提示词配置失败: {e}")
    
    def get_prompt(self, prompt_id: Optional[str] = None) -> Dict:
        """获取指定的提示词"""
        if not prompt_id:
            prompt_id = self.settings.get('default_prompt_id', 'default')
        
        return self.prompts.get(prompt_id, self.prompts.get('default', {}))
    
    def format_prompt(self, prompt_id: Optional[str] = None, **kwargs) -> str:
        """获取格式化的提示词"""
        prompt_config = self.get_prompt(prompt_id)
        content = prompt_config.get('content', '')
        
        # 支持变量替换
        try:
            return content.format(**kwargs)
        except KeyError as e:
            print(f"提示词变量替换失败: {e}")
            return content
    
    def list_prompts(self) -> List[Dict]:
        """列出所有可用的提示词"""
        result = []
        for prompt_id, config in self.prompts.items():
            result.append({
                'id': prompt_id,
                'name': config.get('name', prompt_id),
                'content': config.get('content', ''),
                'is_active': config.get('is_active', False)
            })
        return result
    
    def add_prompt(self, prompt_id: str, name: str, content: str, is_active: bool = False) -> bool:
        """添加新的提示词"""
        try:
            self.prompts[prompt_id] = {
                'name': name,
                'content': content,
                'is_active': is_active
            }
            self.save_config()
            return True
        except Exception as e:
            print(f"添加提示词失败: {e}")
            return False
    
    def update_prompt(self, prompt_id: str, name: str = None, content: str = None, is_active: bool = None) -> bool:
        """更新提示词"""
        try:
            if prompt_id not in self.prompts:
                return False
            
            if name is not None:
                self.prompts[prompt_id]['name'] = name
            if content is not None:
                self.prompts[prompt_id]['content'] = content
            if is_active is not None:
                self.prompts[prompt_id]['is_active'] = is_active
            
            self.save_config()
            return True
        except Exception as e:
            print(f"更新提示词失败: {e}")
            return False
    
    def delete_prompt(self, prompt_id: str) -> bool:
        """删除提示词"""
        try:
            if prompt_id == 'default':
                return False  # 不能删除默认提示词
            
            if prompt_id in self.prompts:
                del self.prompts[prompt_id]
                self.save_config()
                return True
            return False
        except Exception as e:
            print(f"删除提示词失败: {e}")
            return False
    
    def set_default_prompt(self, prompt_id: str) -> bool:
        """设置默认提示词"""
        try:
            if prompt_id in self.prompts:
                self.settings['default_prompt_id'] = prompt_id
                self.save_config()
                return True
            return False
        except Exception as e:
            print(f"设置默认提示词失败: {e}")
            return False
    
    def get_settings(self) -> Dict:
        """获取全局设置"""
        return self.settings.copy()
    
    def update_settings(self, **kwargs) -> bool:
        """更新全局设置"""
        try:
            for key, value in kwargs.items():
                if key in self.settings:
                    self.settings[key] = value
            self.save_config()
            return True
        except Exception as e:
            print(f"更新设置失败: {e}")
            return False

# 全局实例
sql_prompt_manager = SQLPromptManager()

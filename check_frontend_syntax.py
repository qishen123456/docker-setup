#!/usr/bin/env python3

print("🔧 前端代码检查")
print("="*50)

import os
import re

def check_vue_syntax(file_path):
    """检查Vue文件语法"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        errors = []
        
        # 检查常见的语法问题
        if 'v-for="(step, idx) in msg.steps"' in content:
            if 'step.key' in content and 'step.name' in content:
                # 检查步骤映射是否正确
                if 'undefined' in content:
                    errors.append("发现 'undefined' - 可能是步骤映射问题")
        
        # 检查模板语法
        template_match = re.search(r'<template>(.*?)</template>', content, re.DOTALL)
        if template_match:
            template_content = template_match.group(1)
            
            # 检查未闭合的标签
            open_tags = re.findall(r'<([a-zA-Z-]+)[^>]*>', template_content)
            close_tags = re.findall(r'</([a-zA-Z-]+)>', template_content)
            
            # 简单的标签匹配检查
            for tag in open_tags:
                tag_name = re.match(r'<([a-zA-Z-]+)', tag).group(1)
                if tag_name not in ['img', 'br', 'hr', 'input', 'meta', 'link']:  # 自闭合标签
                    if f"</{tag_name}>" not in template_content:
                        errors.append(f"可能未闭合的标签: {tag_name}")
        
        # 检查脚本部分
        script_match = re.search(r'<script setup>(.*?)</script>', content, re.DOTALL)
        if script_match:
            script_content = script_match.group(1)
            
            # 检查常见的导入问题
            if 'import' in script_content:
                imports = re.findall(r'import.*from.*', script_content)
                for imp in imports:
                    if '{' in imp and '}' in imp:
                        # 检查导入的花括号是否匹配
                        if imp.count('{') != imp.count('}'):
                            errors.append(f"导入语法错误: {imp}")
        
        return errors
        
    except Exception as e:
        return [f"文件读取错误: {e}"]

def main():
    vue_file = "frontend/src/views/Chat.vue"
    
    if not os.path.exists(vue_file):
        print(f"❌ 文件不存在: {vue_file}")
        return
    
    print(f"📝 检查文件: {vue_file}")
    print()
    
    errors = check_vue_syntax(vue_file)
    
    if errors:
        print("❌ 发现问题:")
        for i, error in enumerate(errors, 1):
            print(f"   {i}. {error}")
    else:
        print("✅ 未发现明显的语法问题")
    
    print()
    print("🔍 常见的前端错误原因:")
    print("1. 后端返回的数据结构与前端期望不匹配")
    print("2. API响应拦截器处理错误")
    print("3. Vue组件响应式数据问题")
    print("4. 浏览器缓存问题")
    
    print()
    print("💡 建议的调试步骤:")
    print("1. 打开浏览器开发者工具")
    print("2. 查看Console面板的错误信息")
    print("3. 查看Network面板的API请求")
    print("4. 清除浏览器缓存并刷新")
    print("5. 检查Vue组件的mounted生命周期")

if __name__ == "__main__":
    main()

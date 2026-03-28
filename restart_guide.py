#!/usr/bin/env python3

print("🔄 后端服务重启指南")
print("="*50)

print("🔍 问题分析:")
print("• 诊断脚本显示Vanna初始化正常")
print("• 但前端仍报400错误")
print("• 可能是后端服务缓存了旧代码")
print()

print("📋 重启步骤:")
print()

print("1. 🛑 停止后端服务:")
print("   • 在后端终端按 Ctrl+C")
print("   • 确保看到服务停止信息")
print()

print("2. 🚀 重新启动后端:")
print("   • 运行: python backend/app.py")
print("   • 或运行: start_backend.bat")
print("   • 等待服务完全启动")
print()

print("3. 🔄 重启前端 (可选):")
print("   • 在前端终端按 Ctrl+C")
print("   • 重新运行: npm run dev")
print("   • 或运行: start_frontend.bat")
print()

print("4. 🌐 测试:")
print("   • 打开浏览器: http://localhost:5173")
print("   • 强制刷新: Ctrl+Shift+R")
print("   • 发送测试查询: '查询前3条数据'")
print()

print("🎯 预期结果:")
print("✅ 不再显示错误状态")
print("✅ 正确显示查询结果")
print("✅ 步骤状态正常显示")
print("✅ SQL和数据正常返回")
print()

print("🐛 如果问题仍然存在:")
print("1. 检查后端启动日志是否有错误")
print("2. 确认PostgreSQL服务正在运行")
print("3. 检查端口5432是否被占用")
print("4. 尝试使用SQLite作为数据源")
print()

print("💡 快速检查命令:")
print("• 检查PostgreSQL: pg_isready -h localhost -p 5432")
print("• 检查端口占用: netstat -an | findstr 5432")
print("• 检查Python进程: tasklist | findstr python")
print()

print("="*50)
print("🚀 请按照步骤重启服务，然后测试结果！")
print("="*50)

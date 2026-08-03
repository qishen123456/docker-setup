# AI 模板味检测清单

> 审查 AI 生成代码时逐项检查。命中 P0 必须修复。
> 详见 knowledge-base/ai-smells.md

## P0 级（BLOCKER）

- [ ] emoji 作功能图标（改用 SVG 图标库）
- [ ] 紫粉渐变主视觉（改用 Design Token 主色）
- [ ] 空洞占位文案（Lorem Ipsum / "Welcome to..."）
- [ ] 硬编码颜色值（改用 CSS 变量，例外 #fff/#000）

## P1 级（MAJOR）

- [ ] 弹跳缓动 cubic-bezier(0.68,-0.55,0.265,1.55)
- [ ] 过度抽象（简单功能包 5 层）
- [ ] 不必要的依赖引入
- [ ] AI 风格解释性注释（写"是什么"而非"为什么"）
- [ ] 不符合项目既有模式（与 AGENTS.md 公约摘要冲突）

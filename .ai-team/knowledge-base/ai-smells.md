# AI 生成代码典型坏味道

> AI 生成代码中反复出现的"模板味"问题。
> 审查时逐项检查，命中即要求修复。

## P0 级（必须修复）

### 1. emoji 作功能图标
- **症状**：UI 代码用 emoji（🔧⚙️📋）代替图标
- **修复**：改用项目锁定的 SVG 图标库，统一描边风格
- **来源**：mvp-dev-expert-team P0-1

### 2. 紫粉渐变模板视觉
- **症状**：`linear-gradient(135deg, #7C3AED, #A855F7, #EC4899)` + 发光边框 + 毛玻璃
- **修复**：用项目 Design Token 中的主色，不用 Indigo->Pink 渐变
- **来源**：mvp-dev-expert-team P0-2

### 3. 空洞占位文案
- **症状**：Lorem Ipsum / "Welcome to Our App" / "Sign up today"
- **修复**：用真实的业务文案或明确的 TODO 标注
- **来源**：mvp-dev-expert-team P0-3

### 4. 硬编码颜色值
- **症状**：代码中出现 `#3B82F6` 而非引用 CSS 变量
- **修复**：一律走 Design Token / CSS 变量（唯一例外 `#fff` `#000`）
- **来源**：mvp-dev-expert-team P0-3

## P1 级（建议修复）

### 5. 弹跳缓动动画
- **症状**：`cubic-bezier(0.68, -0.55, 0.265, 1.55)` 弹性缓动
- **修复**：除非有明确的交互理由，否则用 ease/linear

### 6. 过度抽象
- **症状**：简单 CRUD 被包了 5 层抽象（Controller->Service->Manager->Helper->Util）
- **修复**：按项目既有的分层深度，不加层

### 7. 不必要的依赖引入
- **症状**：为了一个小功能引入整个库（如为格式化日期引入 moment.js）
- **修复**：优先用项目已有的依赖或原生 API

### 8. AI 风格注释
- **症状**：`// This function handles the user authentication process` 这种解释性注释
- **修复**：注释写"为什么"不写"是什么"，代码自解释

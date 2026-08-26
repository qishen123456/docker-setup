# 问数对话框语音输入（语音转文字）设计方案

> 2026-08-26 · 状态：方案待评审 · 参考：WorkBuddy 语音输入交互

---

## 一、需求

在智能问数输入框（`ComposerArea.vue`）加语音输入转文字：

- **桌面端**：点麦克风图标 → 动作区变成录音条（跳动的麦克风 + `mm:ss` 计时 + ✕ 取消 + ✓ 确认）→ 点 ✓ 结束并转写
- **移动端**：按住说话 → 松手结束转写（上滑取消）
- 转写出的文字**填入输入框待确认**（追加到已有文字后面，可编辑再发送）
- 空识别结果 toast 提示「未检测到语音内容，请重试。」

---

## 二、先回答一个关键问题：内置大模型能直接转文字吗？

**不能。** 当前已配置的模型（qwen-max / GLM-5.1 / MiniMax-M3 / DeepSeek-V4）都是**纯文本对话模型**——接口只接受文字输入，音频文件喂不进去。语音转文字需要 **ASR 模型**（输入音频、输出文字），这是另一类模型、另一个接口。

**但不需要新买服务**：现有供应商渠道里就有 ASR 模型，复用现有 API Key 即可：

- 硅基流动（DeepSeek 那家平台）托管了 `FunAudioLLM/SenseVoiceSmall` 等 ASR 模型
- dashscope（阿里）有 Paraformer 语音识别系列

---

## 三、ASR 通道选型对比

| 方案 | 原理 | 优点 | 缺点 | 结论 |
|---|---|---|---|---|
| **A. OpenAI 兼容转录接口** | 录音上传后端 → 后端调供应商 `POST /audio/transcriptions`（硅基流动 SenseVoice、智谱 glm-asr、OpenAI whisper 都是这套协议） | 协议统一、接入最简单（一次 HTTP 调用）、复用现有 Key、将来私有化可无缝切换 | 整段录音上传后识别，延迟约 1-3 秒（非边录边出字） | **推荐** |
| B. 阿里 Paraformer 实时识别 | dashscope WebSocket 流式 | 中文效果好、边说边出字 | 接入复杂（ws 鉴权 + 二进制流，前后端都要流式改造）；其文件转写模式要求音频有公网可访问 URL，内网部署不满足 | 体验最好但成本高，二期再考虑 |
| C. 浏览器 Web Speech API | Chrome 内置 `webkitSpeechRecognition` | 零后端零成本 | Chrome 实际走 Google 服务，国内网络不可用；Safari 兼容差。企业内网**不可用** | 排除 |
| D. 私有化 FunASR / SenseVoice | docker 部署开源 ASR 服务，暴露 OpenAI 兼容接口 | 数据不出内网、零调用费 | 多维护一个服务（GPU 更佳，CPU 也能跑） | 作为 A 的一个 provider 后续接入 |

**推荐方案 A**：代码只写一套，provider 做成配置项——开发期接硅基流动/智谱的兼容端点，将来要私有化就部署 FunASR、改个 `base_url` 就行。

---

## 四、架构设计

### 4.1 后端（新增约 150 行，不碰现有问数链路）

**1. 新增配置 `config/asr_settings.json`**（遵循项目「配置优先于代码」约定）：

```json
{
  "enabled": true,
  "provider": "openai_compatible",
  "base_url": "https://api.siliconflow.cn/v1",
  "api_key_b64": "",
  "model": "FunAudioLLM/SenseVoiceSmall",
  "max_duration_sec": 60,
  "max_file_mb": 10
}
```

**2. 新增 `backend/controllers/asr.py`（blueprint）**：`POST /api/asr/transcribe`

- multipart 上传音频（字段名 `file`），校验大小（≤10MB）、类型（webm/mp4/wav/m4a）
- 读取 `asr_settings.json`，用项目已有的 `requests` 转发到 `{base_url}/audio/transcriptions`（OpenAI 协议：表单带 `file` + `model`）
- 返回 `{"text": "..."}`；空结果返回 `{"text": ""}` 由前端弹提示；供应商错误透传状态码
- 鉴权复用现有 token 体系（参照 `controllers/ai_models.py` 的用户识别方式）
- `backend/app.py` 加 1 行注册 blueprint
- **不新增 Python 依赖**

### 4.2 前端（`ComposerArea.vue` 为主，约 200 行）

**1. 麦克风按钮**：输入框右下角动作区（模型选择器与发送按钮之间），Element Plus `Microphone` 图标；`asr_settings.enabled=false` 或浏览器不支持 `MediaRecorder` 时不渲染。

**2. 录音状态机**：`idle → recording → transcribing → idle`

| 状态 | 表现 |
|---|---|
| `recording` | 动作区变成 WorkBuddy 式录音条：跳动的麦克风图标 + `mm:ss` 计时 + ✕（取消丢弃）+ ✓（结束转写）；输入框保持可见可编辑；录音中禁止发送 |
| `transcribing` | 录音条变 loading 文案「识别中…」 |

- **桌面端**（非触屏）：点击麦克风开始，点 ✓ 结束
- **移动端**（`pointer: coarse` 判定）：按住开始、松手结束、上滑取消
- 60 秒到顶自动结束并转写

**3. 音频采集**：`navigator.mediaDevices.getUserMedia({audio:true})` + `MediaRecorder`

- mimeType 按浏览器能力选：优先 `audio/webm;codecs=opus`（桌面 Chrome/Edge），Safari/iOS 回退 `audio/mp4`
- 取消 → 停轨丢弃；确认 → `FormData` POST `/api/asr/transcribe`
- `api/index.js` 加 `transcribeAudio()` 封装，沿用现有 axios 实例与鉴权头

**4. 结果处理**：

- 成功 → 文字追加到输入框（已有文字则补空格衔接），聚焦输入框
- 空结果 → `ElMessage.info('未检测到语音内容，请重试。')`
- 失败 → `ElMessage.error('语音识别失败，请稍后重试')`
- 麦克风权限被拒 → toast「请允许浏览器使用麦克风」

---

## 五、部署注意（重要）

1. **浏览器强制安全上下文**：`getUserMedia` 只在 HTTPS 或 `localhost` 下可用。当前通过 `http://内网IP:端口` 访问时，**浏览器会直接拒绝麦克风权限**——企业部署必须给 nginx 配 HTTPS 证书（改 `nginx/nginx.prod.conf`），这是移动端使用的前置条件。
2. nginx 需放行上传体 ≥ 10MB（`client_max_body_size`）。
3. 方案 A 不需要新增 docker 服务；将来上私有化 FunASR 才需要加容器。

---

## 六、实施步骤（方案获批后）

1. 后端：`config/asr_settings.json` + `controllers/asr.py` + `app.py` 注册
2. 用 curl 带测试音频验证转录链路（需要确认用哪家供应商的 Key，或复用现有渠道 Key）
3. 前端：`api/index.js` 封装 + `ComposerArea.vue` 麦克风按钮 + 录音条 + 状态机
4. 桌面 Chrome 实测：点击录音 → ✓ → 文字进输入框；✕ 取消；空识别 toast；权限拒绝提示
5. 移动端按住说话实测（依赖 HTTPS 部署环境，没有则标记为部署前置条件）

## 七、验证标准

- 语音说「京东直营和天猫直营对比」→ 文字正确进输入框 → 正常问数出结果
- 取消 / 空识别 / 权限拒绝 / 60s 超时，四条边界路径行为符合设计
- 现有输入、发送、模型选择功能不受影响

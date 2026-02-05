# LLM 多提供商配置说明

系统支持 **OpenAI、DeepSeek、Claude、Qianwen（通义千问）**，优先使用 `.env` 中已设置好的密钥。

## 一、提供商选择与优先级

1. **显式指定**：在 `.env` 中设置 `LLM_PROVIDER=openai|deepseek|claude|qianwen`，则固定使用该提供商。
2. **自动推断**：未设置 `LLM_PROVIDER` 时，按以下顺序选择**第一个已配置 API Key** 的提供商：
   - OpenAI（`OPENAI_API_KEY`）
   - DeepSeek（`DEEPSEEK_API_KEY`）
   - Claude（`ANTHROPIC_API_KEY`）
   - Qianwen（`DASHSCOPE_API_KEY`）
3. **兜底**：若上述都未配置，则使用 `openai`，并依赖 `OPENAI_API_KEY` 调用。

## 二、.env 配置示例（按提供商）

### 1. 使用 OpenAI

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 可选：自定义 Base URL（如 Azure OpenAI）
# OPENAI_API_BASE=https://your-resource.openai.azure.com/

# 可选：模型
# LLM_MODEL=gpt-4-turbo-preview
```

### 2. 使用 DeepSeek

```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 可选：模型（如 deepseek-chat, deepseek-reasoner）
# LLM_MODEL=deepseek-chat
```

### 3. 使用 Claude（Anthropic）

```env
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 可选：模型
# LLM_MODEL=claude-3-5-sonnet-20241022
```

需安装：`pip install anthropic`

### 4. 使用 Qianwen（通义千问 / 阿里云 DashScope）

```env
LLM_PROVIDER=qianwen
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 可选：Base URL（区域）
# 北京: https://dashscope.aliyuncs.com/compatible-mode/v1
# 美国: https://dashscope-us.aliyuncs.com/compatible-mode/v1
# 新加坡: https://dashscope-intl.aliyuncs.com/compatible-mode/v1
# DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# 可选：模型（如 qwen-plus, qwen-turbo, qwen-max）
# LLM_MODEL=qwen-plus
```

## 三、嵌入模型（Embedding）

**OpenAI、DeepSeek、Qianwen** 支持嵌入接口，用于文档向量化与检索。

**配置**:
```env
# 可选：openai | deepseek | qianwen。不设则：LLM_PROVIDER=deepseek 或已配置 DEEPSEEK_API_KEY 用 deepseek，有 DASHSCOPE_API_KEY 用 qianwen，否则 openai
EMBEDDING_PROVIDER=openai

# 可选：模型名
# OpenAI: text-embedding-3-small, text-embedding-3-large
# DeepSeek: deepseek-embedding, deepseek-embedding-v2
# Qianwen: text-embedding-v3
EMBEDDING_MODEL=text-embedding-3-small
```

**组合示例**:
- 全用 DeepSeek（Chat + 嵌入）：设置 `LLM_PROVIDER=deepseek`、`DEEPSEEK_API_KEY`，嵌入会默认用 `deepseek`（无需再设 `EMBEDDING_PROVIDER`）。
- Chat 用 Claude、Embedding 用 OpenAI：设置 `LLM_PROVIDER=claude`、`OPENAI_API_KEY`、`EMBEDDING_PROVIDER=openai`。
- 全用 Qianwen：设置 `LLM_PROVIDER=qianwen`、`DASHSCOPE_API_KEY`，嵌入会默认用 `qianwen`（或显式 `EMBEDDING_PROVIDER=qianwen`）。

## 四、按角色指定模型（可选）

可为 Router / Decider / Answerer 指定不同模型：

```env
LLM_ROUTER_MODEL=gpt-4-turbo-preview
LLM_DECIDER_MODEL=gpt-4-turbo-preview
LLM_ANSWERER_MODEL=gpt-4-turbo-preview
```

未设置时使用 `LLM_MODEL`，再未设置则使用各提供商的默认模型。

## 五、默认模型一览

| 提供商   | 默认模型 |
|----------|----------|
| OpenAI   | gpt-4-turbo-preview |
| DeepSeek | deepseek-chat |
| Claude   | claude-3-5-sonnet-20241022 |
| Qianwen  | qwen-plus |

## 六、.env 中与 LLM 相关的完整示例（含注释）

可将以下内容合并进 `.env`，按需取消注释并填写密钥：

```env
# ---------- LLM 提供商（四选一或留空自动推断） ----------
# LLM_PROVIDER=openai
# LLM_PROVIDER=deepseek
# LLM_PROVIDER=claude
# LLM_PROVIDER=qianwen

# ---------- 各提供商 API Key（优先使用 .env 中设置好的） ----------
# OpenAI
OPENAI_API_KEY=sk-your-openai-api-key
# OPENAI_API_BASE=https://api.openai.com/v1

# DeepSeek
# DEEPSEEK_API_KEY=sk-your-deepseek-key

# Claude（Anthropic）
# ANTHROPIC_API_KEY=sk-ant-your-anthropic-key

# 通义千问 / Qianwen（DashScope）
# DASHSCOPE_API_KEY=sk-your-dashscope-key
# DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# ---------- 模型（可选） ----------
# LLM_MODEL=gpt-4-turbo-preview
# LLM_ROUTER_MODEL=
# LLM_DECIDER_MODEL=
# LLM_ANSWERER_MODEL=

# ---------- 嵌入（可选：openai / deepseek / qianwen） ----------
# EMBEDDING_PROVIDER=openai
# EMBEDDING_MODEL=text-embedding-3-small
```

## 七、常见问题

**Q: 如何强制使用 DeepSeek？**  
A: 设置 `LLM_PROVIDER=deepseek` 并配置 `DEEPSEEK_API_KEY`。

**Q: 只配置了 DASHSCOPE_API_KEY，会用哪家？**  
A: 若未设置 `LLM_PROVIDER`，会因「自动推断」使用 Qianwen；嵌入默认也会用 Qianwen。

**Q: Claude 是否支持 response_format=json_object？**  
A: 支持。内部会在 system 中追加「只输出合法 JSON」的说明，效果与 OpenAI 的 `response_format` 类似。

**Q: 嵌入用哪家？**  
A: 由 `EMBEDDING_PROVIDER` 决定；未设置时，有 `DASHSCOPE_API_KEY` 则用 `qianwen`，否则用 `openai`。Chat 与嵌入可分别选不同提供商。

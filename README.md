# Intent-Driven Retrieval & Workflow Decision System

生产级意图驱动检索与工作流决策系统

## 核心架构

- **Intent Router**: 意图识别与检索计划生成
- **Retrieval Layer**: 多库检索（DOC/WORKFLOW/RESULT/STRUCTURED）
- **Decider**: 决策器（选择结果或执行工作流）
- **Executor**: 工作流执行器
- **Answerer**: 证据约束式回答生成

## LLM 多提供商支持

对话与推理支持 **OpenAI、DeepSeek、Claude、Qianwen（通义千问）**，优先使用 `.env` 中配置的密钥：

- 通过 `LLM_PROVIDER=openai|deepseek|claude|qianwen` 指定提供商，或留空由系统按已配置 Key 自动选择
- 嵌入（文档向量化）支持 **OpenAI** 与 **Qianwen**，可通过 `EMBEDDING_PROVIDER` 配置

详见 [doc/07_LLM多提供商配置.md](doc/07_LLM多提供商配置.md) 与 [配置指南 - LLM 多提供商](doc/02_配置指南.md)。

## 8个核心常量决策

### 1. Intent Enum 列表

```yaml
- KNOWLEDGE_QA          # 知识问答（偏 DOC）
- LOOKUP_STATUS         # 查状态（偏 STRUCTURED/RESULT）
- EXECUTE_TASK          # 需要执行动作流程（偏 WORKFLOW/TOOL）
- DECISION_RECOMMEND    # 给方案建议（偏 DOC + 推理）
- TROUBLESHOOT          # 排障（偏 DOC + WORKFLOW）
- ACCOUNT_USER_SPECIFIC # 强用户态（必须 user_id）
- OTHER                 # 其他
```

### 2. 数据源定义

- **DOC**: 知识库（S3）、文档（S3）
- **WORKFLOW**: 工作流注册表（Postgres）
- **RESULT**: 执行结果缓存（Postgres）
- **STRUCTURED**: PostgreSQL + Elasticsearch

### 3. Structured Data 技术选型

- **主数据库**: PostgreSQL（Registry + Results）
- **搜索引擎**: Elasticsearch（全文检索增强）
- **图数据库**: 暂不使用（未来可扩展）

### 4. Workflow 编排格式

- **格式**: JSON Steps
- **版本化**: 支持 semver
- **Step 类型**: TOOL, CONDITION, TRANSFORM, RETRIEVE, PARALLEL

### 5. Citations（引用）策略

- **必须引用**: 是
- **格式**: Markdown 链接
- **显示**: 行内引用 + 元数据

示例：
```
[来源: 知识库 > 产品文档](doc://res_doc_123#chunk_5)
[来源: 执行结果 run_20260123_abc](result://res_result_456)
```

### 6. RESULT TTL 策略

- **策略**: 按 workflow 配置，全局默认 fallback
- **默认 TTL**: 3600 秒（1小时）
- **优先级**: workflow.ttl > resource.freshness.ttl > default
- **严格检查**: 是（过期后 5 分钟宽限期）

### 7. 多租户隔离模型

- **启用**: 是
- **隔离级别**: tenant_id（必须）
- **隔离规则**:
  - RESULT: 严格隔离（tenant_id + user_id）
  - WORKFLOW: 严格隔离（tenant_id）
  - DOC: 软隔离（tenant_id，可共享）

### 8. 输出形态默认策略

- **默认**: 步骤化（steps）
- **选项**: text, steps, json, table
- **选择规则**: 用户指定 > 意图推断 > 默认（steps）

## 项目结构

```
.
├── config/              # 配置文件
│   ├── constants.yaml   # 8个核心常量
│   ├── llm_config.py    # LLM 多提供商配置（OpenAI/DeepSeek/Claude/Qianwen）
│   ├── ranking.yaml     # 打分权重配置
│   └── policy.yaml      # 策略配置
├── services/            # 核心服务
│   ├── llm/             # 统一 LLM 客户端（OpenAI/DeepSeek/Claude/Qianwen）
│   ├── chat_api/        # Chat API 服务
│   ├── orchestrator/    # 编排器
│   ├── retrieval/       # 检索层
│   ├── executor/        # 执行器
│   ├── resource_registry/ # 资源注册表
│   └── observability/   # 可观测性
├── prompts/             # LLM Prompt 模板
│   ├── router_v1.md
│   ├── decider_v1.md
│   └── answerer_v1.md
├── workflows/           # 工作流定义
├── docs/                # 预制文档
├── migrations/          # 数据库迁移
└── tests/               # 测试
    ├── unit/
    ├── integration/
    └── eval/
```

## 开发计划

### Sprint 1: 骨架与数据层
- Registry DB schema + migrations
- Resource CRUD API
- Vector store 接入
- Result store 写入与查询

### Sprint 2: Router + Retrieval
- Router schema + prompts + 校验重试
- Doc Retriever（chunking + hybrid search）
- Workflow Retriever
- Result Retriever

### Sprint 3: Decider + 硬规则 + 执行器
- Decider schema + prompts
- 编排器硬规则引擎
- Workflow Executor
- RunResult 入库

### Sprint 4: Answerer + 安全 + 可观测
- Evidence pack 组装
- Answerer 约束式生成
- Prompt injection 防护
- OTel trace + structured logs

### Sprint 5: 压测、评测、灰度
- Eval dataset 管道
- AB prompt 版本
- 成本与延迟优化
- 灰度策略

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行迁移
alembic upgrade head

# 启动服务
python -m services.chat_api.main
```

## 配置说明

所有核心常量定义在 `config/constants.yaml`，包括：
- Intent 枚举
- 数据源定义
- 技术选型
- Workflow 格式
- Citations 策略
- TTL 策略
- 多租户模型
- 输出格式

详细配置请参考各配置文件。

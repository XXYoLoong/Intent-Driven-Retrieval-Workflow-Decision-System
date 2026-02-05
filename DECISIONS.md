# 架构决策记录（ADR）

## 8个核心常量决策说明

本文档详细说明系统设计中的8个关键决策及其理由。

---

### 1. Intent Enum 最终列表

**决策**: 7个固定意图类型

**理由**:
- 覆盖主要业务场景（知识问答、状态查询、任务执行、决策建议、排障、用户特定、其他）
- 固定枚举便于统计、评测、路由优化
- 每个意图对应不同的检索策略和输出格式偏好

**实现**: 见 `config/constants.yaml` 的 `intents` 字段

---

### 2. 数据源定义

**决策**: 
- DOC: S3 存储（知识库、文档）
- WORKFLOW: Postgres（注册表）
- RESULT: Postgres（执行结果缓存）
- STRUCTURED: Postgres + Elasticsearch

**理由**:
- S3 适合大规模文档存储，成本低
- Postgres 适合结构化数据和关系查询
- Elasticsearch 提供全文检索能力
- 分离存储便于独立扩展

**实现**: 见 `config/constants.yaml` 的 `data_sources` 字段

---

### 3. Structured Data 技术选型

**决策**: PostgreSQL（主）+ Elasticsearch（检索增强）

**理由**:
- PostgreSQL 已用于 Registry，复用降低复杂度
- Elasticsearch 提供强大的全文检索和聚合能力
- 暂不使用图数据库，避免过度设计（未来可扩展）

**实现**: 见 `config/constants.yaml` 的 `structured_data` 字段

---

### 4. Workflow 编排格式

**决策**: JSON Steps（可版本化、可序列化）

**理由**:
- JSON 易于序列化、版本控制、调试
- 支持多种 step 类型（TOOL, CONDITION, TRANSFORM, RETRIEVE, PARALLEL）
- 便于在数据库中存储和查询
- 可扩展性强

**实现**: 见 `config/constants.yaml` 的 `workflow_format` 字段

---

### 5. Citations（引用）策略

**决策**: 必须引用 + Markdown 链接格式 + 行内显示

**理由**:
- 必须引用确保可追溯性（符合文档要求）
- Markdown 格式通用、易解析
- 行内引用用户体验更好
- 包含元数据（版本、时间）便于审计

**实现**: 见 `config/constants.yaml` 的 `citations` 字段

---

### 6. RESULT TTL 策略

**决策**: 按 workflow 配置，全局默认 fallback

**理由**:
- 不同 workflow 的结果有效期不同（订单状态 vs 用户画像）
- 允许 workflow 自定义 TTL 提供灵活性
- 全局默认确保所有结果都有过期时间
- 优先级规则清晰：workflow > resource > default

**实现**: 见 `config/constants.yaml` 的 `result_ttl` 字段

---

### 7. 多租户隔离模型

**决策**: tenant_id 必须，user_id 可选，严格隔离 RESULT/WORKFLOW

**理由**:
- 生产环境必须支持多租户
- tenant_id 必须确保数据安全
- RESULT 和 WORKFLOW 严格隔离防止数据泄露
- DOC 软隔离允许共享知识库降低成本

**实现**: 见 `config/constants.yaml` 的 `multi_tenant` 字段

---

### 8. 输出形态默认策略

**决策**: 默认步骤化（steps），可选 text/json/table

**理由**:
- 步骤化更稳、更易理解（符合文档"通常步骤化更稳"）
- 支持多种格式满足不同场景
- 选择规则：用户指定 > 意图推断 > 默认
- LOOKUP_STATUS 倾向 json/table，EXECUTE_TASK 倾向 steps

**实现**: 见 `config/constants.yaml` 的 `output_format` 字段

---

## 决策原则

1. **可追溯**: 所有决策可配置、可版本化
2. **可扩展**: 预留扩展点（如图数据库、新意图类型）
3. **生产级**: 考虑安全、性能、可观测性
4. **可控性**: 避免黑箱，结构化输出，硬规则优先

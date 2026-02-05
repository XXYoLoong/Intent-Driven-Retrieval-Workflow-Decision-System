# C 语言知识库设置指南

## 快速设置 C 语言知识库

### 1. 确保数据库已创建并初始化

```bash
# 创建数据库
createdb -U postgres intent_system

# 运行迁移
alembic upgrade head
```

### 2. 运行初始化脚本

```bash
python scripts/init_c_language_kb.py
```

这个脚本会：
- 注册 C 语言文档资源（`res_doc_c_language`）
- 处理文档（分块、向量化）
- 注册 C 语言检索工作流（`res_workflow_c_language_search`）
- 创建工作流定义

### 3. 验证设置

```bash
# 检查资源是否创建成功
curl http://localhost:8000/v1/resources?type=DOC

# 测试 C 语言相关问题
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "如何修改 C 语言中的数组元素？",
    "context": {"tenant_id": "default"},
    "options": {"output_format": "steps"}
  }'
```

## 知识库内容

C 语言知识库包含以下内容：

1. **基础语法**：变量、数据类型、数组、指针
2. **函数**：定义、调用
3. **控制结构**：if-else、for、while 循环
4. **字符串操作**：声明、函数
5. **结构体**：定义和使用
6. **文件操作**：读写文件
7. **内存管理**：malloc、free、realloc
8. **常见修改操作**：
   - 修改数组元素
   - 修改字符串
   - 修改结构体成员
   - 修改指针指向的值
   - 修改文件内容
   - 修改动态数组大小
9. **错误处理**：返回值检查、空指针检查
10. **预处理器**：宏定义、条件编译
11. **常见问题**：包括多个关于修改操作的问题

## 工作流说明

C 语言检索工作流（`wf_c_language_search_v1`）用于：
- 检索 C 语言相关的文档内容
- 回答关于 C 语言修改、语法、函数等问题
- 返回相关的代码示例和说明

## 使用示例

### 示例 1：询问修改操作
```bash
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "如何修改 C 语言中的字符串？",
    "context": {"tenant_id": "default"}
  }'
```

### 示例 2：询问语法问题
```bash
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "C 语言中如何定义数组？",
    "context": {"tenant_id": "default"}
  }'
```

### 示例 3：询问修改相关问题
```bash
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "如何修改动态分配的数组大小？",
    "context": {"tenant_id": "default"}
  }'
```

## 注意事项

1. **OpenAI API Key**：确保已配置 `OPENAI_API_KEY` 环境变量，用于生成嵌入向量
2. **文档路径**：文档文件位于 `docs/c_language_guide.md`
3. **向量存储**：向量数据存储在 `./data/chroma` 目录（自动创建）
4. **租户ID**：默认使用 `default` 作为租户ID

## 重新索引

如果需要重新处理文档（例如文档内容更新）：

```bash
curl -X POST http://localhost:8000/v1/resources/res_doc_c_language/reindex
```

## 扩展知识库

要添加更多 C 语言内容：

1. 编辑 `docs/c_language_guide.md` 文件
2. 运行重新索引：
   ```bash
   curl -X POST http://localhost:8000/v1/resources/res_doc_c_language/reindex
   ```

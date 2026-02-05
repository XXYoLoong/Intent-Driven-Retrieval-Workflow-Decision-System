"""
初始化 C 语言知识库脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.resource_registry.service import ResourceService, WorkflowService
from services.resource_registry.doc_processor import DocProcessor
from services.resource_registry.database import init_db


def init_c_language_knowledge_base():
    """初始化 C 语言知识库"""
    print("开始初始化 C 语言知识库...")
    
    tenant_id = "default"
    
    # 1. 注册 C 语言文档资源
    print("1. 注册 C 语言文档资源...")
    doc_resource_data = {
        "id": "res_doc_c_language",
        "type": "DOC",
        "title": "C 语言编程指南",
        "capabilities": ["知识问答", "代码示例"],
        "when_to_use": "回答 C 语言相关问题，包括语法、函数、数据结构、修改操作等",
        "tags": ["C语言", "编程", "语法", "修改"],
        "owner": "system",
        "version": "1.0.0",
        "status": "active",
        "retrieval": {
            "keyword_enabled": True,
            "embedding_enabled": True,
            "structured_enabled": False
        },
        "pointers": {
            "doc_uri": str(project_root / "docs" / "c_language_guide.md")
        }
    }
    
    # 检查资源是否已存在
    existing = ResourceService.get_resource("res_doc_c_language", tenant_id)
    if existing:
        print("  文档资源已存在，跳过创建")
    else:
        ResourceService.create_resource(doc_resource_data, tenant_id)
        print("  ✓ 文档资源创建成功")
    
    # 2. 处理文档（分块、向量化）
    print("2. 处理文档（分块、向量化）...")
    processor = DocProcessor()
    try:
        chunks = processor.process_document(
            resource_id="res_doc_c_language",
            doc_path=str(project_root / "docs" / "c_language_guide.md")
        )
        print(f"  ✓ 文档处理成功，共 {len(chunks)} 个分块")
    except Exception as e:
        print(f"  ✗ 文档处理失败: {e}")
        return False
    
    # 3. 注册 C 语言检索工作流
    print("3. 注册 C 语言检索工作流...")
    workflow_resource_data = {
        "id": "res_workflow_c_language_search",
        "type": "WORKFLOW",
        "title": "C 语言知识检索工作流",
        "capabilities": ["检索", "知识问答"],
        "when_to_use": "检索和回答关于 C 语言修改、语法、函数等相关问题",
        "tags": ["C语言", "检索", "知识库"],
        "owner": "system",
        "version": "1.0.0",
        "status": "active",
        "io_schema": {
            "input_json_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "用户查询问题"
                    },
                    "focus": {
                        "type": "string",
                        "description": "关注点：修改、语法、函数等",
                        "enum": ["修改", "语法", "函数", "全部"]
                    }
                },
                "required": ["query"]
            },
            "output_json_schema": {
                "type": "object",
                "properties": {
                    "answer": {"type": "string"},
                    "sources": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            }
        },
        "pointers": {
            "executor_uri": "wf_c_language_search_v1"
        }
    }
    
    existing_workflow = ResourceService.get_resource("res_workflow_c_language_search", tenant_id)
    if existing_workflow:
        print("  工作流资源已存在，跳过创建")
    else:
        ResourceService.create_resource(workflow_resource_data, tenant_id)
        print("  ✓ 工作流资源创建成功")
    
    # 4. 创建工作流定义
    print("4. 创建工作流定义...")
    workflow_def_data = {
        "workflow_id": "wf_c_language_search_v1",
        "workflow_json": {
            "workflow_id": "wf_c_language_search_v1",
            "version": "1.0.0",
            "steps": [
                {
                    "type": "RETRIEVE",
                    "target": "DOC",
                    "query_template": "{{query}}",
                    "filters": {
                        "tags": ["C语言"],
                        "resource_status": ["active"]
                    },
                    "top_k": 5
                },
                {
                    "type": "TRANSFORM",
                    "fn": "format_answer",
                    "input": "step_0.result"
                }
            ]
        },
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "focus": {"type": "string", "default": "全部"}
            },
            "required": ["query"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "answer": {"type": "string"},
                "sources": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        },
        "ttl_seconds": 3600,
        "timeout_seconds": 30,
        "retry_policy": {
            "max_retries": 2,
            "backoff": "exponential"
        },
        "side_effects": [],
        "permissions": {
            "tenant_id": "*",
            "roles": ["user", "admin"]
        }
    }
    
    # 检查工作流定义是否已存在
    from services.resource_registry.service import WorkflowService
    existing_def = WorkflowService.get_workflow("wf_c_language_search_v1", tenant_id)
    if existing_def:
        print("  工作流定义已存在，跳过创建")
    else:
        try:
            WorkflowService.create_workflow("res_workflow_c_language_search", workflow_def_data)
            print("  ✓ 工作流定义创建成功")
        except Exception as e:
            print(f"  ✗ 工作流定义创建失败: {e}")
            # 如果失败，尝试直接插入数据库
            try:
                with get_db_context() as db:
                    workflow_def = WorkflowDef(
                        resource_id="res_workflow_c_language_search",
                        workflow_id="wf_c_language_search_v1",
                        workflow_json=workflow_def_data["workflow_json"],
                        input_schema=workflow_def_data["input_schema"],
                        output_schema=workflow_def_data["output_schema"],
                        ttl_seconds=workflow_def_data["ttl_seconds"],
                        timeout_seconds=workflow_def_data["timeout_seconds"],
                        retry_policy=workflow_def_data["retry_policy"],
                        side_effects=workflow_def_data["side_effects"],
                        permissions=workflow_def_data["permissions"]
                    )
                    db.add(workflow_def)
                    db.commit()
                print("  ✓ 工作流定义创建成功（通过数据库）")
            except Exception as e2:
                print(f"  ✗ 数据库插入也失败: {e2}")
    
    print("\n✓ C 语言知识库初始化完成！")
    print("\n使用示例：")
    print('  curl -X POST http://localhost:8000/v1/chat \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"message": "如何修改 C 语言中的数组元素？", "context": {"tenant_id": "default"}}\'')
    
    return True


if __name__ == "__main__":
    # 确保数据库已初始化
    try:
        init_db()
        print("数据库连接成功")
    except Exception as e:
        print(f"数据库连接失败: {e}")
        print("请确保 PostgreSQL 已启动并创建了 intent_system 数据库")
        sys.exit(1)
    
    # 初始化知识库
    success = init_c_language_kb()
    if not success:
        sys.exit(1)

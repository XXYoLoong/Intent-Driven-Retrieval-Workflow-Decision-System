"""
资源注册表服务层
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from .models import Resource, ResourceDocChunk, WorkflowDef, Result, WorkflowRun
from .database import get_db_context
from datetime import datetime
import hashlib
import json


class ResourceService:
    """资源服务"""

    @staticmethod
    def create_resource(
        resource_data: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> Resource:
        """创建资源"""
        with get_db_context() as db:
            resource = Resource(
                id=resource_data["id"],
                type=resource_data["type"],
                title=resource_data["title"],
                capabilities=resource_data.get("capabilities", []),
                when_to_use=resource_data.get("when_to_use"),
                tags=resource_data.get("tags", []),
                owner=resource_data.get("owner"),
                version=resource_data.get("version", "1.0.0"),
                status=resource_data.get("status", "active"),
                cost=resource_data.get("cost"),
                risk=resource_data.get("risk"),
                io_schema=resource_data.get("io_schema"),
                retrieval=resource_data.get("retrieval"),
                freshness=resource_data.get("freshness"),
                pointers=resource_data.get("pointers"),
                tenant_id=tenant_id or resource_data.get("tenant_id"),
            )
            db.add(resource)
            db.flush()
            return resource

    @staticmethod
    def get_resource(resource_id: str, tenant_id: Optional[str] = None) -> Optional[Resource]:
        """获取资源"""
        with get_db_context() as db:
            query = db.query(Resource).filter(Resource.id == resource_id)
            if tenant_id:
                query = query.filter(Resource.tenant_id == tenant_id)
            return query.first()

    @staticmethod
    def list_resources(
        resource_type: Optional[str] = None,
        status: Optional[str] = None,
        tenant_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Resource]:
        """列出资源"""
        with get_db_context() as db:
            query = db.query(Resource)
            
            if resource_type:
                query = query.filter(Resource.type == resource_type)
            if status:
                query = query.filter(Resource.status == status)
            if tenant_id:
                query = query.filter(Resource.tenant_id == tenant_id)
            if tags:
                # JSON 数组包含查询
                for tag in tags:
                    query = query.filter(Resource.tags.contains([tag]))
            
            return query.order_by(Resource.updated_at.desc()).limit(limit).offset(offset).all()

    @staticmethod
    def update_resource(
        resource_id: str,
        updates: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> Optional[Resource]:
        """更新资源"""
        with get_db_context() as db:
            query = db.query(Resource).filter(Resource.id == resource_id)
            if tenant_id:
                query = query.filter(Resource.tenant_id == tenant_id)
            
            resource = query.first()
            if not resource:
                return None
            
            for key, value in updates.items():
                if hasattr(resource, key):
                    setattr(resource, key, value)
            
            resource.updated_at = datetime.utcnow()
            db.flush()
            return resource

    @staticmethod
    def delete_resource(resource_id: str, tenant_id: Optional[str] = None) -> bool:
        """删除资源"""
        with get_db_context() as db:
            query = db.query(Resource).filter(Resource.id == resource_id)
            if tenant_id:
                query = query.filter(Resource.tenant_id == tenant_id)
            
            resource = query.first()
            if not resource:
                return False
            
            db.delete(resource)
            return True


class WorkflowService:
    """工作流服务"""

    @staticmethod
    def create_workflow(
        resource_id: str,
        workflow_data: Dict[str, Any]
    ) -> WorkflowDef:
        """创建工作流定义"""
        with get_db_context() as db:
            workflow = WorkflowDef(
                resource_id=resource_id,
                workflow_id=workflow_data["workflow_id"],
                workflow_json=workflow_data["workflow_json"],
                input_schema=workflow_data.get("input_schema"),
                output_schema=workflow_data.get("output_schema"),
                ttl_seconds=workflow_data.get("ttl_seconds"),
                retry_policy=workflow_data.get("retry_policy"),
                timeout_seconds=workflow_data.get("timeout_seconds", 30),
                side_effects=workflow_data.get("side_effects"),
                permissions=workflow_data.get("permissions"),
            )
            db.add(workflow)
            db.flush()
            return workflow

    @staticmethod
    def get_workflow(workflow_id: str, tenant_id: Optional[str] = None) -> Optional[WorkflowDef]:
        """获取工作流定义"""
        with get_db_context() as db:
            query = db.query(WorkflowDef).join(Resource).filter(
                WorkflowDef.workflow_id == workflow_id
            )
            if tenant_id:
                query = query.filter(Resource.tenant_id == tenant_id)
            return query.first()


class ResultService:
    """结果服务"""

    @staticmethod
    def create_result(
        result_data: Dict[str, Any],
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Result:
        """创建执行结果"""
        with get_db_context() as db:
            result = Result(
                result_id=result_data["result_id"],
                resource_id=result_data["resource_id"],
                derived_from=result_data["derived_from"],
                subject_keys=result_data.get("subject_keys"),
                inputs_hash=result_data["inputs_hash"],
                fresh_until=result_data["fresh_until"],
                summary=result_data["summary"],
                payload=result_data["payload"],
                tenant_id=tenant_id,
                user_id=user_id,
            )
            db.add(result)
            db.flush()
            return result

    @staticmethod
    def get_result(
        result_id: str,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Optional[Result]:
        """获取结果"""
        with get_db_context() as db:
            query = db.query(Result).filter(Result.result_id == result_id)
            if tenant_id:
                query = query.filter(Result.tenant_id == tenant_id)
            if user_id:
                query = query.filter(Result.user_id == user_id)
            return query.first()

    @staticmethod
    def find_fresh_results(
        inputs_hash: Optional[str] = None,
        subject_keys: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Result]:
        """查找新鲜结果"""
        with get_db_context() as db:
            query = db.query(Result).filter(
                Result.fresh_until >= datetime.utcnow()
            )
            
            if tenant_id:
                query = query.filter(Result.tenant_id == tenant_id)
            if user_id:
                query = query.filter(Result.user_id == user_id)
            if inputs_hash:
                query = query.filter(Result.inputs_hash == inputs_hash)
            
            # subject_keys 匹配（简化版，实际可能需要更复杂的JSON查询）
            if subject_keys:
                # 这里简化处理，实际应该用PostgreSQL的JSON操作符
                pass
            
            return query.order_by(Result.fresh_until.desc()).limit(limit).all()

    @staticmethod
    def compute_inputs_hash(inputs: Dict[str, Any]) -> str:
        """计算输入哈希"""
        normalized = json.dumps(inputs, sort_keys=True)
        return hashlib.sha256(normalized.encode()).hexdigest()


class WorkflowRunService:
    """工作流执行服务"""

    @staticmethod
    def create_run(
        run_data: Dict[str, Any],
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> WorkflowRun:
        """创建执行记录"""
        with get_db_context() as db:
            run = WorkflowRun(
                run_id=run_data["run_id"],
                workflow_id=run_data["workflow_id"],
                resource_id=run_data.get("resource_id"),
                status=run_data.get("status", "running"),
                inputs=run_data["inputs"],
                outputs=run_data.get("outputs"),
                artifacts=run_data.get("artifacts"),
                errors=run_data.get("errors"),
                idempotency_key=run_data.get("idempotency_key"),
                tenant_id=tenant_id,
                user_id=user_id,
            )
            db.add(run)
            db.flush()
            return run

    @staticmethod
    def get_run(run_id: str, tenant_id: Optional[str] = None) -> Optional[WorkflowRun]:
        """获取执行记录"""
        with get_db_context() as db:
            query = db.query(WorkflowRun).filter(WorkflowRun.run_id == run_id)
            if tenant_id:
                query = query.filter(WorkflowRun.tenant_id == tenant_id)
            return query.first()

    @staticmethod
    def update_run_status(
        run_id: str,
        status: str,
        outputs: Optional[Dict[str, Any]] = None,
        errors: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[WorkflowRun]:
        """更新执行状态"""
        with get_db_context() as db:
            run = db.query(WorkflowRun).filter(WorkflowRun.run_id == run_id).first()
            if not run:
                return None
            
            run.status = status
            if outputs is not None:
                run.outputs = outputs
            if errors is not None:
                run.errors = errors
            if status in ["success", "failed", "partial"]:
                run.ended_at = datetime.utcnow()
            
            db.flush()
            return run

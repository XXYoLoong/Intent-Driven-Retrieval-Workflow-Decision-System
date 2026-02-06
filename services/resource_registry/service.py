# Copyright 2026 Jiacheng Ni
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
    ) -> Dict[str, Any]:
        """创建资源，返回字典避免脱离 Session 后访问报错"""
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
            return resource.to_dict()

    @staticmethod
    def get_resource(resource_id: str, tenant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取资源，返回字典避免脱离 Session 后访问报错"""
        with get_db_context() as db:
            query = db.query(Resource).filter(Resource.id == resource_id)
            if tenant_id:
                query = query.filter(Resource.tenant_id == tenant_id)
            resource = query.first()
            return resource.to_dict() if resource else None

    @staticmethod
    def list_resources(
        resource_type: Optional[str] = None,
        status: Optional[str] = None,
        tenant_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """列出资源，返回字典列表"""
        with get_db_context() as db:
            query = db.query(Resource)
            
            if resource_type:
                query = query.filter(Resource.type == resource_type)
            if status:
                query = query.filter(Resource.status == status)
            if tenant_id:
                query = query.filter(Resource.tenant_id == tenant_id)
            if tags:
                for tag in tags:
                    query = query.filter(Resource.tags.contains([tag]))
            
            rows = query.order_by(Resource.updated_at.desc()).limit(limit).offset(offset).all()
            return [r.to_dict() for r in rows]

    @staticmethod
    def update_resource(
        resource_id: str,
        updates: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """更新资源，返回字典"""
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
            return resource.to_dict()

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
    def get_workflow(workflow_id: str, tenant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """按 workflow_id 获取工作流定义，返回字典"""
        with get_db_context() as db:
            query = db.query(WorkflowDef).join(Resource).filter(
                WorkflowDef.workflow_id == workflow_id
            )
            if tenant_id:
                query = query.filter(Resource.tenant_id == tenant_id)
            w = query.first()
            return w.to_dict() if w else None

    @staticmethod
    def get_workflow_by_resource_id(resource_id: str, tenant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """按 resource_id 获取工作流定义，返回字典（供编排器根据执行资源查工作流）"""
        with get_db_context() as db:
            query = db.query(WorkflowDef).filter(WorkflowDef.resource_id == resource_id)
            if tenant_id:
                query = query.join(Resource, WorkflowDef.resource_id == Resource.id).filter(Resource.tenant_id == tenant_id)
            w = query.first()
            return w.to_dict() if w else None


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
    ) -> Optional[Dict[str, Any]]:
        """获取结果，返回字典"""
        with get_db_context() as db:
            query = db.query(Result).filter(Result.result_id == result_id)
            if tenant_id:
                query = query.filter(Result.tenant_id == tenant_id)
            if user_id:
                query = query.filter(Result.user_id == user_id)
            r = query.first()
            return r.to_dict() if r else None

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
    def get_run(run_id: str, tenant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取执行记录，返回字典"""
        with get_db_context() as db:
            query = db.query(WorkflowRun).filter(WorkflowRun.run_id == run_id)
            if tenant_id:
                query = query.filter(WorkflowRun.tenant_id == tenant_id)
            run = query.first()
            return run.to_dict() if run else None

    @staticmethod
    def update_run_status(
        run_id: str,
        status: str,
        outputs: Optional[Dict[str, Any]] = None,
        errors: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[Dict[str, Any]]:
        """更新执行状态；outputs 会做去循环引用处理再写入，避免 Circular reference detected"""
        def _break_cycles(obj: Any, seen: Optional[set] = None) -> Any:
            seen = seen or set()
            oid = id(obj)
            if oid in seen:
                return None
            if isinstance(obj, dict):
                seen.add(oid)
                try:
                    return {k: _break_cycles(v, seen) for k, v in obj.items()}
                finally:
                    seen.discard(oid)
            if isinstance(obj, list):
                seen.add(oid)
                try:
                    return [_break_cycles(i, seen) for i in obj]
                finally:
                    seen.discard(oid)
            if isinstance(obj, (str, int, float, bool)) or obj is None:
                return obj
            if hasattr(obj, "isoformat"):  # datetime
                return obj.isoformat()
            return str(obj)

        with get_db_context() as db:
            run = db.query(WorkflowRun).filter(WorkflowRun.run_id == run_id).first()
            if not run:
                return None
            
            run.status = status
            if outputs is not None:
                run.outputs = _break_cycles(outputs)
            if errors is not None:
                run.errors = _break_cycles(errors) if isinstance(errors, list) else errors
            if status in ["success", "failed", "partial"]:
                run.ended_at = datetime.utcnow()
            
            db.flush()
            return run.to_dict()

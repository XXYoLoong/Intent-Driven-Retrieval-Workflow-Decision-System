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
工作流执行引擎
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib
import json
import uuid
from services.resource_registry.service import WorkflowService, WorkflowRunService, ResultService, ResourceService
from services.resource_registry.models import WorkflowRun
from config.constants import ResourceType


class WorkflowEngine:
    """工作流执行引擎"""

    def __init__(self):
        pass

    def execute(
        self,
        workflow_id: str,
        inputs: Dict[str, Any],
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """执行工作流"""
        # 1. 获取工作流定义
        workflow_def = WorkflowService.get_workflow(workflow_id, tenant_id)
        if not workflow_def:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        # 2. 生成 run_id
        run_id = f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # 3. 生成 idempotency_key（如果未提供）
        if not idempotency_key:
            idempotency_key = self._generate_idempotency_key(
                workflow_id, inputs, tenant_id, user_id
            )
        
        # 4. 检查幂等性
        existing_run = self._check_idempotency(idempotency_key, tenant_id)
        if existing_run and existing_run.status == "success":
            return {
                "run_id": existing_run.run_id,
                "workflow_id": workflow_id,
                "status": "success",
                "outputs": existing_run.outputs,
                "from_cache": True
            }
        
        # 5. 创建执行记录
        run_data = {
            "run_id": run_id,
            "workflow_id": workflow_id,
            "resource_id": workflow_def.resource_id,
            "status": "running",
            "inputs": inputs,
            "idempotency_key": idempotency_key
        }
        run = WorkflowRunService.create_run(run_data, tenant_id, user_id)
        
        # 6. 执行工作流步骤
        try:
            outputs, errors = self._execute_steps(
                workflow_def.workflow_json,
                inputs,
                workflow_def.timeout_seconds or 30
            )
            
            # 7. 更新执行记录
            status = "success" if not errors else "partial" if outputs else "failed"
            WorkflowRunService.update_run_status(
                run_id,
                status,
                outputs=outputs,
                errors=errors
            )
            
            # 8. 生成 RESULT（如果成功）
            if status == "success" and outputs:
                self._create_result(
                    workflow_def,
                    run_id,
                    inputs,
                    outputs,
                    tenant_id,
                    user_id
                )
            
            return {
                "run_id": run_id,
                "workflow_id": workflow_id,
                "status": status,
                "outputs": outputs,
                "errors": errors,
                "from_cache": False
            }
        
        except Exception as e:
            # 更新为失败
            WorkflowRunService.update_run_status(
                run_id,
                "failed",
                errors=[{"step": "unknown", "code": "EXCEPTION", "message": str(e)}]
            )
            raise

    def _execute_steps(
        self,
        workflow_json: Dict[str, Any],
        inputs: Dict[str, Any],
        timeout_seconds: int
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """执行工作流步骤"""
        steps = workflow_json.get("steps", [])
        context = {"inputs": inputs, "outputs": {}}
        errors = []
        
        for i, step in enumerate(steps):
            try:
                step_type = step.get("type")
                
                if step_type == "TOOL":
                    result = self._execute_tool(step, context)
                    context["outputs"][f"step_{i}"] = result
                
                elif step_type == "CONDITION":
                    condition_result = self._execute_condition(step, context)
                    context["outputs"][f"step_{i}"] = condition_result
                    # 根据条件决定是否跳过后续步骤
                    if not condition_result.get("result", False):
                        break
                
                elif step_type == "TRANSFORM":
                    result = self._execute_transform(step, context)
                    context["outputs"][f"step_{i}"] = result
                
                elif step_type == "RETRIEVE":
                    result = self._execute_retrieve(step, context)
                    context["outputs"][f"step_{i}"] = result
                
                elif step_type == "PARALLEL":
                    result = self._execute_parallel(step, context)
                    context["outputs"][f"step_{i}"] = result
                
                else:
                    errors.append({
                        "step": i,
                        "code": "UNKNOWN_STEP_TYPE",
                        "message": f"Unknown step type: {step_type}"
                    })
            
            except Exception as e:
                errors.append({
                    "step": i,
                    "code": "EXECUTION_ERROR",
                    "message": str(e)
                })
        
        # 合并所有步骤输出
        final_outputs = {}
        for key, value in context["outputs"].items():
            if isinstance(value, dict):
                final_outputs.update(value)
            else:
                final_outputs[key] = value
        
        return final_outputs, errors

    def _execute_tool(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具步骤"""
        tool_id = step.get("tool_id")
        args_template = step.get("args_template", {})
        
        # 渲染参数模板（简化版）
        args = self._render_template(args_template, context)
        
        # TODO: 调用实际工具适配器
        # 这里简化返回
        return {
            "tool_id": tool_id,
            "args": args,
            "result": {"status": "success", "data": {}}
        }

    def _execute_condition(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行条件步骤"""
        condition = step.get("condition", {})
        # 简化：评估条件表达式
        # 实际应该使用安全的表达式求值器
        return {"result": True}

    def _execute_transform(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行变换步骤"""
        fn = step.get("fn")
        # TODO: 实现数据变换
        return {"result": context.get("outputs", {})}

    def _execute_retrieve(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行检索步骤"""
        # TODO: 调用检索器
        return {"result": []}

    def _execute_parallel(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行并行步骤"""
        sub_steps = step.get("steps", [])
        # TODO: 实现并行执行
        return {"results": []}

    def _render_template(self, template: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """渲染参数模板"""
        # 简化版：直接返回模板（实际应该支持变量替换）
        return template

    def _generate_idempotency_key(
        self,
        workflow_id: str,
        inputs: Dict[str, Any],
        tenant_id: Optional[str],
        user_id: Optional[str]
    ) -> str:
        """生成幂等性键"""
        normalized = json.dumps({
            "workflow_id": workflow_id,
            "inputs": inputs,
            "tenant_id": tenant_id,
            "user_id": user_id
        }, sort_keys=True)
        return hashlib.sha256(normalized.encode()).hexdigest()

    def _check_idempotency(
        self,
        idempotency_key: str,
        tenant_id: Optional[str]
    ) -> Optional[WorkflowRun]:
        """检查幂等性"""
        # TODO: 从数据库查询
        return None

    def _create_result(
        self,
        workflow_def,
        run_id: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        tenant_id: Optional[str],
        user_id: Optional[str]
    ) -> None:
        """创建 RESULT 资源"""
        # 计算 inputs_hash
        inputs_hash = ResultService.compute_inputs_hash(inputs)
        
        # 计算 TTL
        ttl_seconds = workflow_def.ttl_seconds
        if not ttl_seconds:
            from config.constants import RESULT_TTL
            ttl_seconds = RESULT_TTL["default_ttl_seconds"]
        
        from datetime import timedelta
        fresh_until = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        
        # 生成 summary（简化）
        summary = f"工作流 {workflow_def.workflow_id} 执行结果"
        
        # 创建 RESULT 资源
        result_id = f"res_result_{run_id}"
        result_data = {
            "result_id": result_id,
            "resource_id": result_id,  # RESULT 资源ID
            "derived_from": {
                "resource_id": workflow_def.resource_id,
                "run_id": run_id,
                "inputs_hash": inputs_hash
            },
            "subject_keys": {
                "user_id": user_id,
                "entity_ids": [],
                "time_range": {}
            },
            "inputs_hash": inputs_hash,
            "fresh_until": fresh_until,
            "summary": summary,
            "payload": outputs
        }
        
        ResultService.create_result(result_data, tenant_id, user_id)
        
        # 同时创建对应的 Resource 记录
        resource_data = {
            "id": result_id,
            "type": ResourceType.RESULT,
            "title": summary,
            "capabilities": [],
            "tags": ["execution_result"],
            "version": "1.0.0",
            "status": "active",
            "pointers": {
                "result_uri": result_id
            }
        }
        ResourceService.create_resource(resource_data, tenant_id)

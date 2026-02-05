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
工作流 API
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any
from services.executor.workflow_engine import WorkflowEngine
from services.resource_registry.service import WorkflowRunService

router = APIRouter(prefix="/v1/workflows", tags=["workflows"])

workflow_engine = WorkflowEngine()


class WorkflowRunRequest(BaseModel):
    inputs: Dict[str, Any]
    idempotency_key: Optional[str] = None


@router.post("/{workflow_id}/run")
async def run_workflow(
    workflow_id: str,
    request: WorkflowRunRequest,
    tenant_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None)
):
    """执行工作流"""
    try:
        result = workflow_engine.execute(
            workflow_id=workflow_id,
            inputs=request.inputs,
            tenant_id=tenant_id,
            user_id=user_id,
            idempotency_key=request.idempotency_key
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    tenant_id: Optional[str] = Query(None)
):
    """获取执行记录"""
    run = WorkflowRunService.get_run(run_id, tenant_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return {
        "run_id": run.run_id,
        "workflow_id": run.workflow_id,
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "ended_at": run.ended_at.isoformat() if run.ended_at else None,
        "inputs": run.inputs,
        "outputs": run.outputs,
        "artifacts": run.artifacts,
        "errors": run.errors
    }

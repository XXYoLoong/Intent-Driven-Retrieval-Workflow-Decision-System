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
资源注册表 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from .service import ResourceService, WorkflowService, ResultService, WorkflowRunService
from .database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/v1/resources", tags=["resources"])


# Pydantic 模型
class ResourceCreate(BaseModel):
    id: str
    type: str
    title: str
    capabilities: List[str] = []
    when_to_use: Optional[str] = None
    tags: List[str] = []
    owner: Optional[str] = None
    version: str = "1.0.0"
    status: str = "active"
    cost: Optional[Dict[str, Any]] = None
    risk: Optional[Dict[str, Any]] = None
    io_schema: Optional[Dict[str, Any]] = None
    retrieval: Optional[Dict[str, Any]] = None
    freshness: Optional[Dict[str, Any]] = None
    pointers: Optional[Dict[str, Any]] = None
    tenant_id: Optional[str] = None


class ResourceUpdate(BaseModel):
    title: Optional[str] = None
    capabilities: Optional[List[str]] = None
    when_to_use: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None
    cost: Optional[Dict[str, Any]] = None
    risk: Optional[Dict[str, Any]] = None
    io_schema: Optional[Dict[str, Any]] = None
    retrieval: Optional[Dict[str, Any]] = None
    freshness: Optional[Dict[str, Any]] = None
    pointers: Optional[Dict[str, Any]] = None


class ResourceResponse(BaseModel):
    id: str
    type: str
    title: str
    capabilities: List[str]
    when_to_use: Optional[str]
    tags: List[str]
    owner: Optional[str]
    version: str
    status: str
    cost: Optional[Dict[str, Any]]
    risk: Optional[Dict[str, Any]]
    io_schema: Optional[Dict[str, Any]]
    retrieval: Optional[Dict[str, Any]]
    freshness: Optional[Dict[str, Any]]
    pointers: Optional[Dict[str, Any]]
    tenant_id: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


@router.post("", response_model=ResourceResponse, status_code=201)
async def create_resource(
    resource: ResourceCreate,
    tenant_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """注册资源"""
    try:
        created = ResourceService.create_resource(
            resource.dict(),
            tenant_id=tenant_id
        )
        return created.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(
    resource_id: str,
    tenant_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """获取资源"""
    resource = ResourceService.get_resource(resource_id, tenant_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return resource.to_dict()


@router.get("", response_model=List[ResourceResponse])
async def list_resources(
    type: Optional[str] = Query(None, alias="type"),
    status: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    tags: Optional[List[str]] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """列出资源"""
    resources = ResourceService.list_resources(
        resource_type=type,
        status=status,
        tenant_id=tenant_id,
        tags=tags,
        limit=limit,
        offset=offset
    )
    return [r.to_dict() for r in resources]


@router.put("/{resource_id}", response_model=ResourceResponse)
async def update_resource(
    resource_id: str,
    updates: ResourceUpdate,
    tenant_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """更新资源"""
    update_dict = {k: v for k, v in updates.dict().items() if v is not None}
    resource = ResourceService.update_resource(resource_id, update_dict, tenant_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return resource.to_dict()


@router.delete("/{resource_id}", status_code=204)
async def delete_resource(
    resource_id: str,
    tenant_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """删除资源"""
    success = ResourceService.delete_resource(resource_id, tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Resource not found")


@router.post("/{resource_id}/reindex", status_code=202)
async def reindex_resource(
    resource_id: str,
    tenant_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """重建索引（向量/关键词）"""
    from services.resource_registry.doc_processor import DocProcessor
    
    processor = DocProcessor()
    success = processor.reindex_resource(resource_id)
    
    if success:
        return {"message": "Reindexing completed", "resource_id": resource_id}
    else:
        raise HTTPException(status_code=400, detail="Reindexing failed")

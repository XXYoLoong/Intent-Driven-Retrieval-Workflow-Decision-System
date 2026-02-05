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
资源注册表数据模型
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, JSON, Text, Index,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import json

Base = declarative_base()


class Resource(Base):
    """资源主表"""
    __tablename__ = "resources"

    id = Column(String(64), primary_key=True)  # res_xxx
    type = Column(String(20), nullable=False, index=True)  # DOC, WORKFLOW, TOOL, RESULT
    title = Column(String(512), nullable=False)
    capabilities = Column(JSON, nullable=False, default=list)  # [string, ...]
    when_to_use = Column(Text, nullable=True)
    tags = Column(JSON, nullable=False, default=list)  # [string, ...]
    owner = Column(String(128), nullable=True)  # team/service
    version = Column(String(32), nullable=False, default="1.0.0")  # semver
    status = Column(String(20), nullable=False, default="active", index=True)  # active/disabled/deprecated
    cost = Column(JSON, nullable=True)  # {latency_ms, usd, token}
    risk = Column(JSON, nullable=True)  # {level, notes}
    io_schema = Column(JSON, nullable=True)  # {input_json_schema, output_json_schema}
    retrieval = Column(JSON, nullable=True)  # {keyword_enabled, embedding_enabled, structured_enabled}
    freshness = Column(JSON, nullable=True)  # {ttl_seconds, expires_at}
    pointers = Column(JSON, nullable=True)  # {doc_uri, executor_uri, result_uri}
    tenant_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    doc_chunks = relationship("ResourceDocChunk", back_populates="resource", cascade="all, delete-orphan")
    workflow_def = relationship("WorkflowDef", back_populates="resource", uselist=False, cascade="all, delete-orphan")
    results = relationship("Result", back_populates="resource", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_resource_type_status", "type", "status"),
        Index("idx_resource_tenant", "tenant_id", "type"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "capabilities": self.capabilities,
            "when_to_use": self.when_to_use,
            "tags": self.tags,
            "owner": self.owner,
            "version": self.version,
            "status": self.status,
            "cost": self.cost,
            "risk": self.risk,
            "io_schema": self.io_schema,
            "retrieval": self.retrieval,
            "freshness": self.freshness,
            "pointers": self.pointers,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ResourceDocChunk(Base):
    """文档分块表"""
    __tablename__ = "resource_docs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_id = Column(String(64), ForeignKey("resources.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id = Column(String(64), nullable=False)  # chunk_xxx
    content_uri = Column(String(512), nullable=True)
    content_hash = Column(String(64), nullable=True)
    content_text = Column(Text, nullable=True)
    chunk_index = Column(Integer, nullable=False, default=0)
    metadata = Column(JSON, nullable=True)  # {start_pos, end_pos, page_num, etc}
    embedding_id = Column(String(64), nullable=True)  # 向量库中的ID
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    resource = relationship("Resource", back_populates="doc_chunks")

    __table_args__ = (
        Index("idx_doc_resource_chunk", "resource_id", "chunk_id"),
    )


class WorkflowDef(Base):
    """工作流定义表"""
    __tablename__ = "workflow_defs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_id = Column(String(64), ForeignKey("resources.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    workflow_id = Column(String(128), nullable=False, index=True)  # wf_xxx
    workflow_json = Column(JSON, nullable=False)  # 完整工作流定义
    input_schema = Column(JSON, nullable=True)
    output_schema = Column(JSON, nullable=True)
    ttl_seconds = Column(Integer, nullable=True)  # 结果TTL
    retry_policy = Column(JSON, nullable=True)
    timeout_seconds = Column(Integer, nullable=True, default=30)
    side_effects = Column(JSON, nullable=True)  # [string, ...]
    permissions = Column(JSON, nullable=True)  # {tenant_id, roles, ...}
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    resource = relationship("Resource", back_populates="workflow_def")

    __table_args__ = (
        Index("idx_workflow_id", "workflow_id", "resource_id"),
    )


class Result(Base):
    """执行结果表（RESULT类型资源）"""
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    result_id = Column(String(64), nullable=False, unique=True, index=True)  # res_result_xxx
    resource_id = Column(String(64), ForeignKey("resources.id", ondelete="CASCADE"), nullable=False, index=True)
    derived_from = Column(JSON, nullable=False)  # {resource_id, run_id, inputs_hash}
    subject_keys = Column(JSON, nullable=True)  # {user_id, entity_ids, time_range}
    inputs_hash = Column(String(64), nullable=False, index=True)  # SHA256 hash
    fresh_until = Column(DateTime, nullable=False, index=True)
    summary = Column(Text, nullable=False)  # 用于检索的短摘要
    payload = Column(JSON, nullable=False)  # 实际结果数据
    tenant_id = Column(String(64), nullable=True, index=True)
    user_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    resource = relationship("Resource", back_populates="results")

    __table_args__ = (
        Index("idx_result_freshness", "fresh_until", "tenant_id"),
        Index("idx_result_subject", "tenant_id", "user_id"),
        Index("idx_result_inputs_hash", "inputs_hash", "tenant_id"),
    )


class WorkflowRun(Base):
    """工作流执行记录"""
    __tablename__ = "workflow_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), nullable=False, unique=True, index=True)  # run_xxx
    workflow_id = Column(String(128), nullable=False, index=True)
    resource_id = Column(String(64), ForeignKey("resources.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), nullable=False, default="running", index=True)  # success/failed/partial/running
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    ended_at = Column(DateTime, nullable=True)
    inputs = Column(JSON, nullable=False)
    outputs = Column(JSON, nullable=True)
    artifacts = Column(JSON, nullable=True)  # [{type, uri}, ...]
    errors = Column(JSON, nullable=True)  # [{step, code, message}, ...]
    idempotency_key = Column(String(64), nullable=True, index=True)
    tenant_id = Column(String(64), nullable=True, index=True)
    user_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_run_workflow_tenant", "workflow_id", "tenant_id", "started_at"),
        Index("idx_run_idempotency", "idempotency_key", "tenant_id"),
    )

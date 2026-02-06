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
回放接口
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
from services.observability.tracing import TraceLogger
import json

router = APIRouter(prefix="/v1", tags=["replay"])


@router.get("/traces/{trace_id}")
async def get_trace(trace_id: str):
    """获取追踪信息"""
    # TODO: 从存储中获取 trace
    return {
        "trace_id": trace_id,
        "status": "not_implemented",
        "message": "Trace storage not implemented yet"
    }


@router.post("/replay")
async def replay(
    trace_id: str,
    mode: str = Query("readonly", pattern="^(readonly|execute)$")
):
    """重放追踪（只读或执行模式）"""
    # TODO: 实现回放逻辑
    return {
        "trace_id": trace_id,
        "mode": mode,
        "status": "not_implemented",
        "message": "Replay not implemented yet"
    }

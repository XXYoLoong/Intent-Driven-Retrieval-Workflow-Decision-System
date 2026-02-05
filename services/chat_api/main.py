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
Chat API 服务
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import json
import asyncio
from services.orchestrator.orchestrator import Orchestrator
from services.chat_api.workflow_api import router as workflow_router
from services.chat_api.replay import router as replay_router
from services.resource_registry.api import router as resource_router

app = FastAPI(title="Intent-Driven Retrieval & Workflow Decision System")

# 注册路由
app.include_router(workflow_router)
app.include_router(replay_router)
app.include_router(resource_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化编排器
orchestrator = Orchestrator()


# Pydantic 模型
class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    message: str = Field(..., min_length=1)
    context: Optional[Dict[str, Any]] = {}
    options: Optional[Dict[str, Any]] = {
        "debug": False,
        "show_routing": False,
        "output_format": "steps"
    }


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    meta: Dict[str, Any]


@app.post("/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """同步聊天接口"""
    try:
        # 构建 context
        context = {
            "session_id": request.session_id,
            "user_id": request.user_id,
            "tenant_id": request.context.get("tenant_id"),
            "output_format": request.options.get("output_format", "steps")
        }
        
        # 调用编排器
        result = orchestrator.process(
            user_message=request.message,
            conversation_context=request.context,
            context=context
        )
        
        # 根据 options 决定返回内容
        if request.options.get("show_routing", False):
            return ChatResponse(
                session_id=result.get("session_id", ""),
                answer=result.get("answer", ""),
                meta={
                    **result.get("meta", {}),
                    "plan": result.get("plan"),
                    "action": result.get("action"),
                    "candidates_count": result.get("candidates_count", 0)
                }
            )
        else:
            return ChatResponse(
                session_id=result.get("session_id", ""),
                answer=result.get("answer", ""),
                meta=result.get("meta", {})
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/chat/stream")
async def chat_stream(request: ChatRequest):
    """流式聊天接口（SSE）"""
    async def generate():
        try:
            # 发送 routing_plan 事件
            yield f"event: routing_plan\n"
            yield f"data: {json.dumps({'status': 'planning'})}\n\n"
            
            # 构建 context
            context = {
                "session_id": request.session_id,
                "user_id": request.user_id,
                "tenant_id": request.context.get("tenant_id"),
                "output_format": request.options.get("output_format", "steps")
            }
            
            # 调用编排器
            result = orchestrator.process(
                user_message=request.message,
                conversation_context=request.context,
                context=context
            )
            
            # 发送 decision 事件
            yield f"event: decision\n"
            yield f"data: {json.dumps({'action_type': result.get('meta', {}).get('action_type')})}\n\n"
            
            # 流式输出答案（简化版：分块发送）
            answer = result.get("answer", "")
            chunk_size = 50
            for i in range(0, len(answer), chunk_size):
                chunk = answer[i:i+chunk_size]
                yield f"event: delta_answer\n"
                yield f"data: {json.dumps({'delta': chunk})}\n\n"
                await asyncio.sleep(0.1)  # 模拟流式
            
            # 发送 final 事件
            yield f"event: final\n"
            yield f"data: {json.dumps({'answer': answer, 'meta': result.get('meta', {})})}\n\n"
        
        except Exception as e:
            yield f"event: error\n"
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


@app.get("/v1/health")
async def health():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

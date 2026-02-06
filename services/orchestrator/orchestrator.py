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
编排器（Orchestrator）
"""
from typing import Dict, Any, List, Optional
from .router import IntentRouter
from .decider import Decider
from .answerer import Answerer
from services.retrieval.doc_retriever import DocRetriever
from services.retrieval.workflow_retriever import WorkflowRetriever
from services.retrieval.result_retriever import ResultRetriever
from services.retrieval.vector_store import VectorStore
from services.retrieval.embedding import EmbeddingService
from services.executor.workflow_engine import WorkflowEngine
from services.resource_registry.service import ResourceService, ResultService
from config.constants import ResourceType, ActionType
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class Orchestrator:
    """编排器（驱动全流程）"""

    def __init__(self):
        # 初始化组件
        self.vector_store = VectorStore()
        self.embedding_service = EmbeddingService()
        
        self.router = IntentRouter()
        self.decider = Decider()
        self.answerer = Answerer()
        
        self.doc_retriever = DocRetriever(self.vector_store, self.embedding_service)
        self.workflow_retriever = WorkflowRetriever(self.vector_store, self.embedding_service)
        self.result_retriever = ResultRetriever(self.vector_store, self.embedding_service)
        
        self.workflow_engine = WorkflowEngine()

    def process(
        self,
        user_message: str,
        conversation_context: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """处理用户消息（完整流程）"""
        session_id = context.get("session_id") if context else None
        tenant_id = context.get("tenant_id") if context else None
        user_id = context.get("user_id") if context else None
        
        trace_id = f"trace_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        # 单请求内按 resource_id 缓存，减少 N+1 查询
        resource_cache = {}
        if context is None:
            context = {}
        context = {**context, "resource_cache": resource_cache}
        
        try:
            # 1. Router: 生成检索计划
            plan = self.router.route(
                user_message=user_message,
                conversation_context=conversation_context,
                available_search_scopes=[ResourceType.DOC, ResourceType.WORKFLOW, ResourceType.RESULT, ResourceType.STRUCTURED]
            )
            
            # 2. Retrieval: 执行多库检索（保证 search_plan 为可迭代列表，避免 bool 等导致 'X' object is not iterable）
            all_candidates = []
            search_plan = plan.get("search_plan")
            if not isinstance(search_plan, list):
                search_plan = []
            for search_item in search_plan:
                target = search_item.get("target")
                query = search_item.get("query", user_message)
                filters = search_item.get("filters", {})
                top_k = search_item.get("top_k", 10)
                
                retrieval_context = {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "resource_cache": resource_cache,
                }
                
                if target == ResourceType.DOC:
                    candidates = self.doc_retriever.retrieve(
                        query=query,
                        filters=filters,
                        top_k=top_k,
                        context=retrieval_context
                    )
                    if isinstance(candidates, list):
                        all_candidates.extend(candidates)
                
                elif target == ResourceType.WORKFLOW:
                    candidates = self.workflow_retriever.retrieve(
                        query=query,
                        filters=filters,
                        top_k=top_k,
                        context=retrieval_context
                    )
                    if isinstance(candidates, list):
                        all_candidates.extend(candidates)
                
                elif target == ResourceType.RESULT:
                    candidates = self.result_retriever.retrieve(
                        query=query,
                        filters=filters,
                        top_k=top_k,
                        context=retrieval_context
                    )
                    if isinstance(candidates, list):
                        all_candidates.extend(candidates)
            
            # 3. Decider: 决策
            policy = {}  # TODO: 从配置加载
            action = self.decider.decide(
                user_message=user_message,
                plan=plan,
                candidates=all_candidates,
                policy=policy,
                available_context=context
            )
            
            # 4. Execute: 如果需要执行工作流
            exec_result = None
            if action.get("action_type") == ActionType.EXECUTE_WORKFLOW:
                execution = action.get("execution", {})
                executor_resource_id = execution.get("executor_resource_id")
                exec_inputs = execution.get("input", {})
                idempotency_key = execution.get("idempotency_key")
                
                # 获取 workflow_id（resource / workflow_def 均为字典，避免脱离 Session 报错）
                resource = ResourceService.get_resource(executor_resource_id, tenant_id)
                if resource:
                    from services.resource_registry.service import WorkflowService
                    workflow_def = WorkflowService.get_workflow_by_resource_id(resource["id"], tenant_id)
                    if workflow_def:
                        exec_result = self.workflow_engine.execute(
                            workflow_id=workflow_def["workflow_id"],
                            inputs=exec_inputs,
                            tenant_id=tenant_id,
                            user_id=user_id,
                            idempotency_key=idempotency_key
                        )
            
            # 5. 组装 evidence
            evidence = self._assemble_evidence(
                action=action,
                candidates=all_candidates,
                exec_result=exec_result,
                context=context
            )
            
            # 6. Answerer: 生成最终回答
            selected_resource = action.get("selected", {})
            output_constraints = plan.get("constraints", {})
            
            answer = self.answerer.generate(
                user_message=user_message,
                intent=plan.get("intent", {}),
                selected_resource=selected_resource,
                evidence=evidence,
                output_constraints=output_constraints
            )
            
            # 7. 返回结果（session_id 保证为字符串，避免 ChatResponse 校验失败）
            return {
                "session_id": session_id or "",
                "trace_id": trace_id,
                "answer": answer,
                "meta": {
                    "intent": plan.get("intent", {}).get("name"),
                    "action_type": action.get("action_type"),
                    "selected_resource_id": selected_resource.get("resource_id"),
                    "run_id": exec_result.get("run_id") if exec_result else None,
                    "citations": self._extract_citations(evidence)
                },
                "plan": plan,
                "action": action,
                "candidates_count": len(all_candidates)
            }
        
        except Exception as e:
            # 记录完整 traceback 便于排查；对用户只返回通用提示（不暴露内部错误）
            logger.exception("orchestrator process failed")
            return {
                "session_id": session_id or "",
                "trace_id": trace_id,
                "answer": "处理时发生错误，请稍后重试。",
                "meta": {
                    "intent": "OTHER",
                    "action_type": ActionType.FALLBACK,
                    "error": str(e)
                }
            }

    def _assemble_evidence(
        self,
        action: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        exec_result: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """组装证据包"""
        evidence = []
        selected = action.get("selected", {})
        resource_id = selected.get("resource_id")
        if not isinstance(candidates, list):
            candidates = []
        # 从 candidates 中找到选中的资源
        selected_candidate = None
        for cand in candidates:
            if cand.get("resource_id") == resource_id:
                selected_candidate = cand
                break
        
        if selected_candidate:
            resource_type = selected_candidate.get("resource_type")
            
            if resource_type == ResourceType.DOC:
                # DOC: 使用 snippet
                evidence.append({
                    "resource_id": resource_id,
                    "type": "DOC",
                    "content": selected_candidate.get("snippet", ""),
                    "citation": {
                        "source": f"doc://{resource_id}#chunk",
                        "id": selected_candidate.get("metadata", {}).get("chunk_id", ""),
                        "span": None
                    }
                })
            
            elif resource_type == ResourceType.RESULT:
                # RESULT: 获取完整 payload
                result = ResultService.get_result(
                    resource_id,
                    context.get("tenant_id") if context else None,
                    context.get("user_id") if context else None
                )
                if result:
                    evidence.append({
                        "resource_id": resource_id,
                        "type": "RESULT",
                        "content": str(result.get("payload")),  # 简化：转为字符串
                        "citation": {
                            "source": f"result://{resource_id}",
                            "id": result.get("result_id", ""),
                            "span": None
                        }
                    })
            
            elif resource_type == ResourceType.WORKFLOW:
                # WORKFLOW: 使用描述
                evidence.append({
                    "resource_id": resource_id,
                    "type": "WORKFLOW",
                    "content": selected_candidate.get("snippet", ""),
                    "citation": {
                        "source": f"workflow://{resource_id}",
                        "id": resource_id,
                        "span": None
                    }
                })
        
        # 如果执行了工作流，添加执行结果
        if exec_result and exec_result.get("outputs"):
            evidence.append({
                "resource_id": exec_result.get("run_id"),
                "type": "RESULT",
                "content": str(exec_result.get("outputs", {})),
                "citation": {
                    "source": f"result://run_{exec_result.get('run_id')}",
                    "id": exec_result.get("run_id"),
                    "span": None
                }
            })
        
        return evidence

    def _extract_citations(self, evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """提取引用"""
        citations = []
        if not isinstance(evidence, list):
            evidence = []
        for ev in evidence:
            citation = ev.get("citation", {})
            if citation.get("source"):
                citations.append({
                    "source": citation.get("source"),
                    "id": citation.get("id"),
                    "span": citation.get("span")
                })
        return citations

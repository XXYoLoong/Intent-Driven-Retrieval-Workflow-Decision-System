"""
工作流检索器（WORKFLOW Retriever）
"""
from typing import List, Dict, Any, Optional
from .vector_store import VectorStore
from .embedding import EmbeddingService
from services.resource_registry.service import ResourceService, WorkflowService
from config.constants import ResourceType


class WorkflowRetriever:
    """工作流检索器"""

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_service: EmbeddingService
    ):
        self.vector_store = vector_store
        self.embedding_service = embedding_service

    def retrieve(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """检索工作流"""
        tenant_id = context.get("tenant_id") if context else None

        # 1. 向量检索资源摘要
        query_embedding = self.embedding_service.embed_text(query)
        vector_candidates = self.vector_store.search_resource_briefs(
            query_embedding=query_embedding,
            resource_type=ResourceType.WORKFLOW,
            top_k=top_k * 2,
            filters=filters
        )

        # 2. 关键词匹配（在 capabilities, tags, title 中）
        keyword_candidates = self._keyword_match(query, vector_candidates)

        # 3. 融合打分
        candidates = self._merge_and_score(
            vector_candidates,
            keyword_candidates,
            top_k
        )

        # 4. 格式化为统一格式
        return self._format_candidates(candidates, filters, tenant_id)

    def _keyword_match(
        self,
        query: str,
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """关键词匹配"""
        query_lower = query.lower()
        query_terms = set(query_lower.split())
        
        scored = []
        for cand in candidates:
            resource_id = cand.get("resource_id")
            if not resource_id:
                continue
            
            resource = ResourceService.get_resource(resource_id)
            if not resource:
                continue
            
            # 匹配 capabilities, tags, title
            title_match = query_lower in resource.title.lower()
            capabilities_text = " ".join(resource.capabilities).lower()
            tags_text = " ".join(resource.tags).lower()
            
            capabilities_match = any(term in capabilities_text for term in query_terms)
            tags_match = any(term in tags_text for term in query_terms)
            
            keyword_score = 0.0
            if title_match:
                keyword_score += 0.5
            if capabilities_match:
                keyword_score += 0.3
            if tags_match:
                keyword_score += 0.2
            
            scored.append({
                **cand,
                "keyword_score": min(keyword_score, 1.0),
                "resource": resource
            })
        
        return scored

    def _merge_and_score(
        self,
        vector_candidates: List[Dict[str, Any]],
        keyword_candidates: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """融合分数"""
        candidate_dict = {}
        
        for cand in vector_candidates:
            resource_id = cand.get("resource_id")
            if resource_id:
                candidate_dict[resource_id] = {
                    **cand,
                    "semantic_score": cand.get("score", 0.0),
                    "keyword_score": 0.0
                }
        
        for cand in keyword_candidates:
            resource_id = cand.get("resource_id")
            if resource_id and resource_id in candidate_dict:
                candidate_dict[resource_id]["keyword_score"] = cand.get("keyword_score", 0.0)
                candidate_dict[resource_id]["resource"] = cand.get("resource")
        
        # 计算总分
        scored = []
        for cand in candidate_dict.values():
            semantic = cand.get("semantic_score", 0.0)
            keyword = cand.get("keyword_score", 0.0)
            total = 0.4 * semantic + 0.3 * keyword + 0.3 * 1.0  # 简化权重
            cand["total_score"] = total
            scored.append(cand)
        
        scored.sort(key=lambda x: x.get("total_score", 0.0), reverse=True)
        return scored[:top_k]

    def _format_candidates(
        self,
        candidates: List[Dict[str, Any]],
        filters: Optional[Dict[str, Any]],
        tenant_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """格式化候选"""
        formatted = []
        
        for cand in candidates:
            resource = cand.get("resource")
            if not resource:
                continue
            
            # 检查租户隔离
            if tenant_id and resource.tenant_id and resource.tenant_id != tenant_id:
                continue
            
            # 检查状态
            if filters and "resource_status" in filters:
                if resource.status not in filters["resource_status"]:
                    continue
            
            # 检查是否 deprecated/disabled
            if resource.status in ["deprecated", "disabled"]:
                continue
            
            formatted.append({
                "resource_id": resource.id,
                "resource_type": "WORKFLOW",
                "title": resource.title,
                "snippet": f"{resource.title}. {resource.when_to_use or ''}",
                "scores": {
                    "semantic": cand.get("semantic_score", 0.0),
                    "keyword": cand.get("keyword_score", 0.0),
                    "freshness": 0.0,
                    "policy": 1.0,
                    "total": cand.get("total_score", 0.0)
                },
                "metadata": {
                    "tags": resource.tags,
                    "version": resource.version,
                    "capabilities": resource.capabilities,
                    "updated_at": resource.updated_at.isoformat() if resource.updated_at else None,
                }
            })
        
        return formatted

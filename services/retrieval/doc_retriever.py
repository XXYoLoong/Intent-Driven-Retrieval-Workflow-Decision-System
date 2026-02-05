"""
文档检索器（DOC Retriever）
"""
from typing import List, Dict, Any, Optional
from .vector_store import VectorStore
from .embedding import EmbeddingService
from services.resource_registry.service import ResourceService
from services.resource_registry.models import ResourceDocChunk
import re


class DocRetriever:
    """文档检索器（混合搜索：向量 + 关键词）"""

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
        """检索文档"""
        # 1. 向量检索
        query_embedding = self.embedding_service.embed_text(query)
        vector_candidates = self.vector_store.search_doc_chunks(
            query_embedding=query_embedding,
            top_k=top_k * 2,  # 多取一些用于融合
            filters=filters
        )

        # 2. 关键词检索（简化版：在 snippet 中搜索）
        keyword_candidates = self._keyword_search(query, vector_candidates)

        # 3. 融合打分
        candidates = self._merge_and_score(
            vector_candidates,
            keyword_candidates,
            query,
            top_k
        )

        # 4. 转换为统一格式
        return self._format_candidates(candidates, filters)

    def _keyword_search(
        self,
        query: str,
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """关键词搜索（简化版）"""
        query_terms = set(re.findall(r'\w+', query.lower()))
        scored = []
        
        for candidate in candidates:
            snippet = candidate.get("snippet", "").lower()
            snippet_terms = set(re.findall(r'\w+', snippet))
            
            # 计算关键词匹配度
            matches = len(query_terms & snippet_terms)
            total_terms = len(query_terms) if query_terms else 1
            keyword_score = matches / total_terms
            
            scored.append({
                **candidate,
                "keyword_score": keyword_score
            })
        
        return scored

    def _merge_and_score(
        self,
        vector_candidates: List[Dict[str, Any]],
        keyword_candidates: List[Dict[str, Any]],
        query: str,
        top_k: int
    ) -> List[Dict[str, Any]]:
        """融合向量和关键词分数"""
        # 创建候选字典（按 chunk_id）
        candidate_dict = {}
        
        for cand in vector_candidates:
            chunk_id = cand.get("chunk_id")
            if chunk_id:
                candidate_dict[chunk_id] = {
                    **cand,
                    "semantic_score": cand.get("score", 0.0),
                    "keyword_score": 0.0
                }
        
        # 合并关键词分数
        for cand in keyword_candidates:
            chunk_id = cand.get("chunk_id")
            if chunk_id and chunk_id in candidate_dict:
                candidate_dict[chunk_id]["keyword_score"] = cand.get("keyword_score", 0.0)
        
        # 计算总分（使用配置权重，这里简化）
        scored = []
        for cand in candidate_dict.values():
            semantic = cand.get("semantic_score", 0.0)
            keyword = cand.get("keyword_score", 0.0)
            total = 0.5 * semantic + 0.3 * keyword  # 简化权重
            cand["total_score"] = total
            scored.append(cand)
        
        # 排序并返回 top_k
        scored.sort(key=lambda x: x.get("total_score", 0.0), reverse=True)
        return scored[:top_k]

    def _format_candidates(
        self,
        candidates: List[Dict[str, Any]],
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """格式化为统一候选格式"""
        formatted = []
        
        for cand in candidates:
            # 获取资源信息
            resource_id = cand.get("resource_id")
            resource = None
            if resource_id:
                resource = ResourceService.get_resource(resource_id)
            
            if not resource:
                continue
            
            # 检查状态过滤
            if filters and "resource_status" in filters:
                if resource.status not in filters["resource_status"]:
                    continue
            
            formatted.append({
                "resource_id": resource_id,
                "resource_type": "DOC",
                "title": resource.title,
                "snippet": cand.get("snippet", ""),
                "scores": {
                    "semantic": cand.get("semantic_score", 0.0),
                    "keyword": cand.get("keyword_score", 0.0),
                    "freshness": 0.0,  # DOC 不考虑新鲜度
                    "policy": 1.0,  # 默认通过
                    "total": cand.get("total_score", 0.0)
                },
                "metadata": {
                    "tags": resource.tags,
                    "version": resource.version,
                    "updated_at": resource.updated_at.isoformat() if resource.updated_at else None,
                    "chunk_id": cand.get("chunk_id"),
                }
            })
        
        return formatted

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
结果检索器（RESULT Retriever）
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from .vector_store import VectorStore
from .embedding import EmbeddingService
from services.resource_registry.service import ResultService, ResourceService
from config.constants import ResourceType
import json


class ResultRetriever:
    """结果检索器（考虑新鲜度和 subject_keys 匹配）"""

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
        """检索结果"""
        tenant_id = context.get("tenant_id") if context else None
        user_id = context.get("user_id") if context else None
        
        freshness_required = filters.get("freshness_required", False) if filters else False

        # 1. 向量检索（基于 summary）
        query_embedding = self.embedding_service.embed_text(query)
        vector_candidates = self.vector_store.search_resource_briefs(
            query_embedding=query_embedding,
            resource_type=ResourceType.RESULT,
            top_k=top_k * 2,
            filters=filters
        )

        # 2. 从数据库获取完整结果信息
        db_results = []
        for cand in vector_candidates:
            result_id = cand.get("resource_id")
            if not result_id:
                continue
            
            result = ResultService.get_result(result_id, tenant_id, user_id)
            if not result:
                continue
            
            # 检查新鲜度
            if freshness_required:
                if result.fresh_until < datetime.utcnow():
                    continue  # 过期，跳过
            
            db_results.append({
                **cand,
                "result": result,
                "freshness_score": self._compute_freshness_score(result.fresh_until)
            })

        # 3. 匹配 inputs_hash 和 subject_keys
        if context:
            inputs = context.get("inputs")
            if inputs:
                inputs_hash = ResultService.compute_inputs_hash(inputs)
                # 优先匹配相同 inputs_hash
                for r in db_results:
                    if r["result"].inputs_hash == inputs_hash:
                        r["inputs_match"] = True
                        r["subject_match_score"] = 1.0
                    else:
                        r["inputs_match"] = False
                        r["subject_match_score"] = self._match_subject_keys(
                            r["result"].subject_keys,
                            context
                        )

        # 4. 融合打分
        candidates = self._merge_and_score(db_results, top_k)

        # 5. 格式化
        return self._format_candidates(candidates, filters)

    def _compute_freshness_score(self, fresh_until: datetime) -> float:
        """计算新鲜度分数"""
        now = datetime.utcnow()
        if fresh_until < now:
            return 0.0  # 已过期
        
        # 计算剩余时间比例
        ttl_seconds = (fresh_until - now).total_seconds()
        # 假设最大 TTL 为 24 小时
        max_ttl = 86400
        return min(ttl_seconds / max_ttl, 1.0)

    def _match_subject_keys(
        self,
        result_subject_keys: Optional[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> float:
        """匹配 subject_keys"""
        if not result_subject_keys:
            return 0.5  # 无 subject_keys，给中等分数
        
        score = 0.0
        matches = 0
        total = 0
        
        # 匹配 user_id
        if "user_id" in result_subject_keys and "user_id" in context:
            total += 1
            if result_subject_keys["user_id"] == context["user_id"]:
                matches += 1
        
        # 匹配 entity_ids
        if "entity_ids" in result_subject_keys and "entity_ids" in context:
            total += 1
            result_entities = set(result_subject_keys.get("entity_ids", []))
            context_entities = set(context.get("entity_ids", []))
            if result_entities & context_entities:
                matches += 1
        
        # 匹配 time_range（简化）
        if "time_range" in result_subject_keys and "time_range" in context:
            total += 1
            # 简化：如果有重叠就匹配
            matches += 0.5
        
        if total > 0:
            score = matches / total
        else:
            score = 0.5
        
        return score

    def _merge_and_score(
        self,
        candidates: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """融合分数"""
        scored = []
        
        for cand in candidates:
            semantic = cand.get("score", 0.0)
            freshness = cand.get("freshness_score", 0.0)
            subject_match = cand.get("subject_match_score", 0.5)
            inputs_match = 1.0 if cand.get("inputs_match", False) else 0.5
            
            # 权重：semantic 0.3, freshness 0.4, subject 0.1, inputs 0.2
            total = (
                0.3 * semantic +
                0.4 * freshness +
                0.1 * subject_match +
                0.2 * inputs_match
            )
            
            cand["total_score"] = total
            scored.append(cand)
        
        scored.sort(key=lambda x: x.get("total_score", 0.0), reverse=True)
        return scored[:top_k]

    def _format_candidates(
        self,
        candidates: List[Dict[str, Any]],
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """格式化候选"""
        formatted = []
        
        for cand in candidates:
            result = cand.get("result")
            if not result:
                continue
            
            resource = ResourceService.get_resource(result.resource_id)
            if not resource:
                continue
            
            formatted.append({
                "resource_id": result.result_id,
                "resource_type": "RESULT",
                "title": resource.title,
                "snippet": result.summary,
                "scores": {
                    "semantic": cand.get("score", 0.0),
                    "keyword": 0.0,
                    "freshness": cand.get("freshness_score", 0.0),
                    "policy": 1.0,
                    "total": cand.get("total_score", 0.0)
                },
                "metadata": {
                    "tags": resource.tags,
                    "version": resource.version,
                    "fresh_until": result.fresh_until.isoformat(),
                    "derived_from": result.derived_from,
                    "subject_keys": result.subject_keys,
                }
            })
        
        return formatted

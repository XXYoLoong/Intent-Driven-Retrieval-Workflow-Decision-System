"""
向量存储服务
"""
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
import os
from pathlib import Path


class VectorStore:
    """向量存储（使用 ChromaDB）"""

    def __init__(self, persist_directory: Optional[str] = None):
        """初始化向量存储"""
        if persist_directory is None:
            persist_directory = os.getenv(
                "VECTOR_STORE_PATH",
                str(Path(__file__).parent.parent.parent / "data" / "chroma")
            )
        
        Path(persist_directory).mkdir(parents=True, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # 集合：doc_chunks（文档分块）
        self.doc_chunks_collection = self.client.get_or_create_collection(
            name="doc_chunks",
            metadata={"description": "Document chunks embeddings"}
        )
        
        # 集合：resource_briefs（资源摘要）
        self.resource_briefs_collection = self.client.get_or_create_collection(
            name="resource_briefs",
            metadata={"description": "Resource briefs embeddings"}
        )

    def add_doc_chunks(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> None:
        """添加文档分块"""
        if not chunks or not embeddings:
            return
        
        ids = [chunk["chunk_id"] for chunk in chunks]
        texts = [chunk.get("content_text", "") for chunk in chunks]
        metadatas = [
            {
                "resource_id": chunk.get("resource_id"),
                "chunk_index": chunk.get("chunk_index", 0),
                "title": chunk.get("title", ""),
            }
            for chunk in chunks
        ]
        
        self.doc_chunks_collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )

    def search_doc_chunks(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """搜索文档分块"""
        where = {}
        if filters:
            if "resource_id" in filters:
                where["resource_id"] = filters["resource_id"]
            if "tags" in filters:
                # ChromaDB 不支持数组包含查询，需要预处理
                pass
        
        results = self.doc_chunks_collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where if where else None
        )
        
        candidates = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for i, doc_id in enumerate(results["ids"][0]):
                candidates.append({
                    "chunk_id": doc_id,
                    "resource_id": results["metadatas"][0][i].get("resource_id"),
                    "snippet": results["documents"][0][i],
                    "score": 1.0 - results["distances"][0][i] if results["distances"] else 0.0,
                    "metadata": results["metadatas"][0][i]
                })
        
        return candidates

    def add_resource_briefs(
        self,
        resources: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> None:
        """添加资源摘要"""
        if not resources or not embeddings:
            return
        
        ids = [r["resource_id"] for r in resources]
        texts = [
            f"{r.get('title', '')} {r.get('summary', '')} {' '.join(r.get('tags', []))}"
            for r in resources
        ]
        metadatas = [
            {
                "resource_id": r["resource_id"],
                "type": r.get("type"),
                "title": r.get("title", ""),
                "tags": ",".join(r.get("tags", [])),
            }
            for r in resources
        ]
        
        self.resource_briefs_collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )

    def search_resource_briefs(
        self,
        query_embedding: List[float],
        resource_type: Optional[str] = None,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """搜索资源摘要"""
        where = {}
        if resource_type:
            where["type"] = resource_type
        if filters:
            if "tags" in filters:
                # 简化处理
                pass
        
        results = self.resource_briefs_collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where if where else None
        )
        
        candidates = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for i, resource_id in enumerate(results["ids"][0]):
                candidates.append({
                    "resource_id": resource_id,
                    "type": results["metadatas"][0][i].get("type"),
                    "title": results["metadatas"][0][i].get("title"),
                    "snippet": results["documents"][0][i],
                    "score": 1.0 - results["distances"][0][i] if results["distances"] else 0.0,
                    "metadata": results["metadatas"][0][i]
                })
        
        return candidates

    def delete_by_resource_id(self, resource_id: str) -> None:
        """删除资源相关的所有向量"""
        # 删除文档分块
        self.doc_chunks_collection.delete(
            where={"resource_id": resource_id}
        )
        
        # 删除资源摘要
        self.resource_briefs_collection.delete(
            ids=[resource_id]
        )

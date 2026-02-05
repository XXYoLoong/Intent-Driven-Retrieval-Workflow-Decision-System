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
文档处理服务：解析文档、分块、向量化
"""
from typing import List, Dict, Any
from pathlib import Path
import hashlib
from services.retrieval.embedding import EmbeddingService
from services.retrieval.vector_store import VectorStore
from services.resource_registry.service import ResourceService
from services.resource_registry.models import ResourceDocChunk
from services.resource_registry.database import get_db_context


class DocProcessor:
    """文档处理器"""

    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()

    def process_document(
        self,
        resource_id: str,
        doc_path: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ) -> List[Dict[str, Any]]:
        """处理文档：读取、分块、向量化、存储"""
        # 1. 读取文档
        doc_path_obj = Path(doc_path)
        if not doc_path_obj.exists():
            raise FileNotFoundError(f"文档不存在: {doc_path}")
        
        content = doc_path_obj.read_text(encoding="utf-8")
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        # 2. 分块
        chunks = self._chunk_text(content, chunk_size, chunk_overlap)
        
        # 3. 生成嵌入向量
        chunk_texts = [chunk["text"] for chunk in chunks]
        embeddings = self.embedding_service.embed_batch(chunk_texts)
        
        # 4. 准备数据
        doc_chunks = []
        vector_chunks = []
        
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"{resource_id}_chunk_{i}"
            
            # 数据库记录
            doc_chunks.append({
                "resource_id": resource_id,
                "chunk_id": chunk_id,
                "content_uri": doc_path,
                "content_hash": content_hash,
                "content_text": chunk["text"],
                "chunk_index": i,
                "chunk_metadata": {
                    "start_pos": chunk.get("start_pos", 0),
                    "end_pos": chunk.get("end_pos", len(chunk["text"]))
                }
            })
            
            # 向量库记录
            vector_chunks.append({
                "chunk_id": chunk_id,
                "resource_id": resource_id,
                "chunk_index": i,
                "title": chunk.get("title", ""),
                "content_text": chunk["text"]
            })
        
        # 5. 存储到数据库
        with get_db_context() as db:
            # 删除旧的 chunks
            db.query(ResourceDocChunk).filter(
                ResourceDocChunk.resource_id == resource_id
            ).delete()
            
            # 插入新的 chunks
            for chunk_data in doc_chunks:
                chunk = ResourceDocChunk(**chunk_data)
                db.add(chunk)
            
            db.commit()
        
        # 6. 存储到向量库
        vector_embeddings = embeddings
        self.vector_store.add_doc_chunks(vector_chunks, vector_embeddings)
        
        return doc_chunks

    def _chunk_text(
        self,
        text: str,
        chunk_size: int,
        chunk_overlap: int
    ) -> List[Dict[str, Any]]:
        """文本分块（按段落和大小）"""
        # 按段落分割
        paragraphs = text.split("\n\n")
        
        chunks = []
        current_chunk = ""
        current_pos = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # 如果当前块加上新段落超过大小，保存当前块
            if len(current_chunk) + len(para) > chunk_size and current_chunk:
                chunks.append({
                    "text": current_chunk.strip(),
                    "start_pos": current_pos,
                    "end_pos": current_pos + len(current_chunk)
                })
                
                # 重叠处理：保留最后一部分
                if chunk_overlap > 0 and len(current_chunk) > chunk_overlap:
                    overlap_text = current_chunk[-chunk_overlap:]
                    current_chunk = overlap_text + "\n\n" + para
                    current_pos = current_pos + len(current_chunk) - len(overlap_text) - len(para)
                else:
                    current_chunk = para
                    current_pos = current_pos + len(current_chunk)
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
            
            # 如果单个段落就超过大小，强制分割
            if len(current_chunk) > chunk_size * 1.5:
                # 按句子分割
                sentences = current_chunk.split("。")
                temp_chunk = ""
                for sent in sentences:
                    if len(temp_chunk) + len(sent) > chunk_size:
                        if temp_chunk:
                            chunks.append({
                                "text": temp_chunk.strip(),
                                "start_pos": current_pos,
                                "end_pos": current_pos + len(temp_chunk)
                            })
                            current_pos += len(temp_chunk)
                        temp_chunk = sent
                    else:
                        temp_chunk += sent + "。"
                current_chunk = temp_chunk
        
        # 保存最后一个块
        if current_chunk:
            chunks.append({
                "text": current_chunk.strip(),
                "start_pos": current_pos,
                "end_pos": current_pos + len(current_chunk)
            })
        
        return chunks

    def reindex_resource(self, resource_id: str) -> bool:
        """重新索引资源"""
        resource = ResourceService.get_resource(resource_id)
        if not resource:
            return False
        
        if resource.type != "DOC":
            return False
        
        pointers = resource.pointers or {}
        doc_uri = pointers.get("doc_uri")
        
        if not doc_uri:
            return False
        
        # 处理文档
        try:
            self.process_document(resource_id, doc_uri)
            return True
        except Exception as e:
            print(f"重新索引失败: {e}")
            return False

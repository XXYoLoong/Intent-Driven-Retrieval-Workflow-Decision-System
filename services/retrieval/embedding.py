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
嵌入向量生成服务
支持 OpenAI、Qianwen（通义），优先使用 .env 中配置的密钥。
（DeepSeek 官方 API 暂无 embeddings 端点，使用 DeepSeek 做 LLM 时需单独配置 OPENAI 或 Qianwen 做嵌入。）
"""
from typing import List, Optional
from openai import OpenAI

from config.llm_config import (
    get_embedding_provider,
    get_embedding_api_key_and_base,
    get_embedding_model,
)

# 各提供商嵌入维度（用于 ChromaDB 等）
EMBEDDING_DIMENSIONS = {
    "openai": {"text-embedding-3-small": 1536, "text-embedding-3-large": 3072, "text-embedding-ada-002": 1536},
    "qianwen": {"text-embedding-v3": 1536, "text-embedding-v2": 1536},
}


class EmbeddingService:
    """嵌入向量服务（OpenAI / Qianwen）"""

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """初始化嵌入服务，优先使用 .env 中配置的密钥。"""
        self._provider = provider or get_embedding_provider()
        key, default_base = get_embedding_api_key_and_base()
        self._api_key = api_key or key
        self._base_url = base_url or default_base
        self._model = model or get_embedding_model()
        self.client = OpenAI(
            api_key=self._api_key,
            base_url=self._base_url.rstrip("/") if self._base_url else None,
        )
        dims = EMBEDDING_DIMENSIONS.get(self._provider, EMBEDDING_DIMENSIONS["openai"])
        self.dimension = dims.get(self._model, 1536)

    @property
    def model(self) -> str:
        return self._model

    def embed_text(self, text: str) -> List[float]:
        """生成单个文本的嵌入向量"""
        response = self.client.embeddings.create(
            model=self._model,
            input=text,
        )
        return response.data[0].embedding

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量生成嵌入向量"""
        if not texts:
            return []
        response = self.client.embeddings.create(
            model=self._model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    def get_dimension(self) -> int:
        """获取向量维度"""
        return self.dimension

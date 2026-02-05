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
LLM 提供商配置：从 .env 读取，优先使用已配置的密钥
支持：OpenAI、DeepSeek、Claude、Qianwen（通义千问）
"""
import os
from typing import Optional, Tuple

# 环境变量键（优先使用 .env 中设置好的密钥）
ENV_LLM_PROVIDER = "LLM_PROVIDER"
ENV_OPENAI_API_KEY = "OPENAI_API_KEY"
ENV_OPENAI_BASE_URL = "OPENAI_API_BASE"
ENV_DEEPSEEK_API_KEY = "DEEPSEEK_API_KEY"
ENV_ANTHROPIC_API_KEY = "ANTHROPIC_API_KEY"
ENV_DASHSCOPE_API_KEY = "DASHSCOPE_API_KEY"  # 通义千问 / Qianwen
ENV_DASHSCOPE_BASE_URL = "DASHSCOPE_BASE_URL"

# 模型默认值
DEFAULT_MODELS = {
    "openai": "gpt-4-turbo-preview",
    "deepseek": "deepseek-chat",
    "claude": "claude-3-5-sonnet-20241022",
    "qianwen": "qwen-plus",
}

# 各提供商 Base URL（当 .env 未指定时使用）
DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com",
    "qianwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
}


def get_llm_provider() -> str:
    """
    获取当前 LLM 提供商。
    优先级：.env 中 LLM_PROVIDER > 有密钥的第一个提供商 > openai
    """
    provider = (os.getenv(ENV_LLM_PROVIDER) or "").strip().lower()
    if provider in ("openai", "deepseek", "claude", "qianwen"):
        return provider
    # 按优先级检测已配置的密钥
    if os.getenv(ENV_OPENAI_API_KEY):
        return "openai"
    if os.getenv(ENV_DEEPSEEK_API_KEY):
        return "deepseek"
    if os.getenv(ENV_ANTHROPIC_API_KEY):
        return "claude"
    if os.getenv(ENV_DASHSCOPE_API_KEY):
        return "qianwen"
    return "openai"


def get_llm_api_key_and_base(provider: Optional[str] = None) -> Tuple[str, str]:
    """
    返回 (api_key, base_url)。
    优先使用 .env 中设置好的密钥；base_url 仅在 openai/deepseek/qianwen 时使用。
    """
    provider = provider or get_llm_provider()
    base_url = ""
    if provider == "openai":
        key = os.getenv(ENV_OPENAI_API_KEY) or ""
        base_url = os.getenv(ENV_OPENAI_BASE_URL) or DEFAULT_BASE_URLS["openai"]
        return key, base_url
    if provider == "deepseek":
        key = os.getenv(ENV_DEEPSEEK_API_KEY) or ""
        base_url = DEFAULT_BASE_URLS["deepseek"]
        return key, base_url
    if provider == "claude":
        key = os.getenv(ENV_ANTHROPIC_API_KEY) or ""
        return key, base_url
    if provider == "qianwen":
        key = os.getenv(ENV_DASHSCOPE_API_KEY) or ""
        base_url = os.getenv(ENV_DASHSCOPE_BASE_URL) or DEFAULT_BASE_URLS["qianwen"]
        return key, base_url
    key = os.getenv(ENV_OPENAI_API_KEY) or ""
    base_url = os.getenv(ENV_OPENAI_BASE_URL) or DEFAULT_BASE_URLS["openai"]
    return key, base_url


def get_llm_model(provider: Optional[str] = None, role: str = "chat") -> str:
    """
    获取当前提供商使用的模型名。
    role: chat | router | decider | answerer
    可通过环境变量覆盖：LLM_MODEL、LLM_ROUTER_MODEL、LLM_DECIDER_MODEL、LLM_ANSWERER_MODEL
    """
    provider = provider or get_llm_provider()
    env_key = f"LLM_{role.upper()}_MODEL"
    model = os.getenv(env_key) or os.getenv("LLM_MODEL") or DEFAULT_MODELS.get(provider, DEFAULT_MODELS["openai"])
    return model.strip() if isinstance(model, str) else DEFAULT_MODELS["openai"]


def get_embedding_provider() -> str:
    """嵌入模型提供商：openai | deepseek | qianwen，优先 .env 中 EMBEDDING_PROVIDER。"""
    p = (os.getenv("EMBEDDING_PROVIDER") or "").strip().lower()
    if p in ("openai", "deepseek", "qianwen"):
        return p
    if os.getenv(ENV_DASHSCOPE_API_KEY):
        return "qianwen"
    if os.getenv(ENV_DEEPSEEK_API_KEY) or (os.getenv(ENV_LLM_PROVIDER) or "").strip().lower() == "deepseek":
        return "deepseek"
    return "openai"


def get_embedding_api_key_and_base() -> Tuple[str, str]:
    """嵌入服务 (api_key, base_url)。"""
    provider = get_embedding_provider()
    if provider == "qianwen":
        key = os.getenv(ENV_DASHSCOPE_API_KEY) or ""
        base = os.getenv(ENV_DASHSCOPE_BASE_URL) or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        return key, base
    if provider == "deepseek":
        key = os.getenv(ENV_DEEPSEEK_API_KEY) or ""
        base = DEFAULT_BASE_URLS["deepseek"]
        return key, base
    key = os.getenv(ENV_OPENAI_API_KEY) or ""
    base = os.getenv(ENV_OPENAI_BASE_URL) or DEFAULT_BASE_URLS["openai"]
    return key, base


def get_embedding_model() -> str:
    """嵌入模型名。可通过 EMBEDDING_MODEL 覆盖。"""
    default = {
        "openai": "text-embedding-3-small",
        "deepseek": "deepseek-embedding",
        "qianwen": "text-embedding-v3",
    }.get(get_embedding_provider(), "text-embedding-3-small")
    return os.getenv("EMBEDDING_MODEL") or default

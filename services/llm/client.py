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
统一 LLM 客户端：支持 OpenAI、DeepSeek、Claude、Qianwen。
优先使用 .env 中配置的密钥与提供商。
"""
from typing import Any, Dict, List, Optional
import os
from openai import OpenAI

from config.llm_config import (
    get_llm_provider,
    get_llm_api_key_and_base,
    get_llm_model,
)


class UnifiedLLMClient:
    """
    统一 Chat 接口，对外与 OpenAI Chat Completions 兼容。
    内部根据 LLM_PROVIDER 选择 OpenAI 兼容接口或 Claude（Anthropic）并适配返回格式。
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self._provider = provider or get_llm_provider()
        key, default_base = get_llm_api_key_and_base(self._provider)
        self._api_key = api_key or key
        self._base_url = base_url or default_base
        self._model = model or get_llm_model(self._provider, "chat")

        self._openai_client: Optional[OpenAI] = None
        self._anthropic_client: Any = None

        if self._provider == "claude":
            self._init_anthropic()
        else:
            self._init_openai_compatible()

    def _init_openai_compatible(self) -> None:
        """OpenAI / DeepSeek / Qianwen 使用 OpenAI SDK + base_url."""
        self._openai_client = OpenAI(
            api_key=self._api_key,
            base_url=self._base_url.rstrip("/") if self._base_url else None,
        )

    def _init_anthropic(self) -> None:
        try:
            from anthropic import Anthropic
            self._anthropic_client = Anthropic(api_key=self._api_key)
        except ImportError:
            raise RuntimeError(
                "使用 Claude 请安装: pip install anthropic"
            )

    @property
    def model(self) -> str:
        return self._model

    @model.setter
    def model(self, value: str) -> None:
        self._model = value

    def chat_completions_create(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.1,
        response_format: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Any:
        """
        与 OpenAI client.chat.completions.create 兼容的返回结构：
        response.choices[0].message.content
        """
        model = model or self._model
        if self._provider == "claude":
            return self._chat_claude(messages, model, temperature, response_format, **kwargs)
        return self._chat_openai_compatible(messages, model, temperature, response_format, **kwargs)

    def _is_qwen_omni_model(self, model: str) -> bool:
        """Qwen-Omni（qwen3-omni-*）仅支持流式调用，需特殊处理。"""
        return bool(model and str(model).strip().lower().startswith("qwen3-omni-"))

    def _chat_openai_compatible(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        response_format: Optional[Dict[str, str]],
        **kwargs: Any,
    ) -> Any:
        """OpenAI / DeepSeek / Qianwen：直接调用 OpenAI SDK。Qwen-Omni 强制流式并聚合成单次响应。"""
        if self._provider == "qianwen" and self._is_qwen_omni_model(model):
            return self._chat_qwen_omni_non_stream(
                messages, model, temperature, response_format, **kwargs
            )
        params: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            **kwargs,
        }
        if response_format is not None and self._provider in ("openai", "deepseek"):
            params["response_format"] = response_format
        elif response_format is not None and self._provider == "qianwen":
            try:
                params["response_format"] = response_format
            except Exception:
                pass
        return self._openai_client.chat.completions.create(**params)

    def _chat_qwen_omni_non_stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        response_format: Optional[Dict[str, str]],
        **kwargs: Any,
    ) -> Any:
        """Qwen-Omni 仅支持 stream=True，内部流式调用后聚合成与 create() 相同的返回结构。"""
        params: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
            "modalities": ["text"],
            **{k: v for k, v in kwargs.items() if k not in ("stream", "stream_options", "modalities")},
        }
        if response_format is not None:
            try:
                params["response_format"] = response_format
            except Exception:
                pass
        stream = self._openai_client.chat.completions.create(**params)
        content_parts: List[str] = []
        for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    content_parts.append(delta.content)
        text = "".join(content_parts)

        class _Choice:
            class _Message:
                def __init__(self, content: str):
                    self.content = content
            def __init__(self, content: str):
                self.message = self._Message(content)
        class _Response:
            def __init__(self, content: str):
                self.choices = [_Choice(content)]
        return _Response(text)

    def _chat_claude(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        response_format: Optional[Dict[str, str]],
        **kwargs: Any,
    ) -> Any:
        """Claude：调用 Anthropic，返回 OpenAI 兼容结构。"""
        system = ""
        chat_messages: List[Dict[str, str]] = []
        for m in messages:
            role = (m.get("role") or "user").lower()
            content = (m.get("content") or "").strip()
            if role == "system":
                system = content
            else:
                chat_messages.append({"role": role, "content": content})

        if response_format and response_format.get("type") == "json_object":
            if system:
                system += "\n\n请只输出合法 JSON，不要包含其他文字或 markdown 代码块。"
            else:
                system = "请只输出合法 JSON，不要包含其他文字或 markdown 代码块。"

        resp = self._anthropic_client.messages.create(
            model=model,
            max_tokens=kwargs.get("max_tokens", 4096),
            system=system or None,
            messages=chat_messages,
            temperature=temperature,
        )
        text = ""
        if resp.content and len(resp.content) > 0:
            block = resp.content[0]
            if hasattr(block, "text"):
                text = block.text
            elif isinstance(block, dict) and "text" in block:
                text = block["text"]

        # 适配为 OpenAI 风格
        class _Choice:
            class _Message:
                def __init__(self, content: str):
                    self.content = content
            def __init__(self, content: str):
                self.message = self._Message(content)
        class _Response:
            def __init__(self, content: str):
                self.choices = [_Choice(content)]
        return _Response(text)


def create_llm_client(
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> UnifiedLLMClient:
    """工厂方法：优先使用传入参数，否则从 .env 读取。"""
    return UnifiedLLMClient(
        provider=provider,
        api_key=api_key,
        base_url=base_url,
        model=model,
    )


class _ChatCompletionsAdapter:
    """适配器：提供与 OpenAI client.chat.completions 相同的 create 接口。"""

    def __init__(self, unified_client: UnifiedLLMClient):
        self._client = unified_client

    def create(self, **kwargs: Any) -> Any:
        messages = kwargs.pop("messages", [])
        model = kwargs.pop("model", self._client.model)
        temperature = kwargs.pop("temperature", 0.1)
        response_format = kwargs.pop("response_format", None)
        return self._client.chat_completions_create(
            messages=messages,
            model=model,
            temperature=temperature,
            response_format=response_format,
            **kwargs,
        )


class _ChatAdapter:
    def __init__(self, unified_client: UnifiedLLMClient):
        self.completions = _ChatCompletionsAdapter(unified_client)


def get_openai_compatible_client(
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> Any:
    """
    返回与 OpenAI 客户端兼容的对象，支持 client.chat.completions.create(...)。
    供 Router、Decider、Answerer 直接替换 self.client 使用。
    优先使用 .env 中配置的密钥。
    """
    unified = create_llm_client(
        provider=provider,
        api_key=api_key,
        base_url=base_url,
        model=model,
    )
    adapter = _ChatAdapter(unified)
    adapter.model = unified.model
    adapter._unified_client = unified
    return adapter

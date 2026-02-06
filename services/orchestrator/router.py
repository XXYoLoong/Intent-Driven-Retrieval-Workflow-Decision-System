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
意图路由器（Router）
支持 OpenAI、DeepSeek、Claude、Qianwen，优先使用 .env 中配置的密钥。
"""
from typing import Dict, Any, Optional
import json
from pathlib import Path
from config.constants import Intent
from config.llm_config import get_llm_model
from services.llm.client import get_openai_compatible_client


class IntentRouter:
    """意图路由器（LLM-1）"""

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.client = get_openai_compatible_client(
            provider=provider,
            api_key=api_key,
            base_url=base_url,
            model=model,
        )
        self.model = model or get_llm_model(None, "router") or self.client.model
        self.prompt_template = self._load_prompt()

    def _load_prompt(self) -> str:
        """加载 prompt 模板"""
        prompt_path = Path(__file__).parent.parent.parent / "prompts" / "router_v1.md"
        if prompt_path.exists():
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def route(
        self,
        user_message: str,
        conversation_context: Optional[Dict[str, Any]] = None,
        available_search_scopes: Optional[list] = None,
        resource_briefs: Optional[list] = None
    ) -> Dict[str, Any]:
        """生成检索计划"""
        # 构建 prompt
        system_prompt = self.prompt_template
        
        user_prompt = f"""用户消息：{user_message}

可用检索库：{available_search_scopes or ['DOC', 'WORKFLOW', 'RESULT', 'STRUCTURED']}

请生成检索计划（严格 JSON 格式）。"""

        # 调用 LLM（最多重试2次）
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"},
                )
                content = getattr(response.choices[0].message, "content", None) or ""
                plan_json = json.loads(content)
                
                # 验证 schema
                if self._validate_plan(plan_json):
                    return plan_json
                else:
                    if attempt < max_retries - 1:
                        # 重试时添加纠正提示
                        user_prompt += "\n\n你的输出不符合 schema，请严格输出 JSON，确保所有必需字段都存在。"
                        continue
                    else:
                        # 降级：返回默认计划
                        return self._default_plan(user_message)
            
            except json.JSONDecodeError:
                if attempt < max_retries - 1:
                    user_prompt += "\n\n你的输出不是有效的 JSON，请重新输出。"
                    continue
                else:
                    return self._default_plan(user_message)
            except Exception as e:
                if attempt < max_retries - 1:
                    continue
                else:
                    return self._default_plan(user_message)
        
        return self._default_plan(user_message)

    def _validate_plan(self, plan: Dict[str, Any]) -> bool:
        """验证计划 schema"""
        required_fields = ["intent", "search_plan", "decision_goal", "constraints"]
        for field in required_fields:
            if field not in plan:
                return False
        
        # 验证 intent
        if "name" not in plan["intent"]:
            return False
        
        # 验证 search_plan 为非空列表（避免 LLM 返回 true 导致后续 'bool' object is not iterable）
        search_plan = plan.get("search_plan")
        if not isinstance(search_plan, list) or len(search_plan) == 0:
            return False
        
        return True

    def _default_plan(self, user_message: str) -> Dict[str, Any]:
        """默认计划（降级路径）"""
        return {
            "intent": {
                "name": "OTHER",
                "confidence": 0.5,
                "entities": []
            },
            "needs_workflow": "unknown",
            "search_plan": [
                {
                    "target": "DOC",
                    "query": user_message,
                    "filters": {
                        "tags": [],
                        "resource_status": ["active"],
                        "freshness_required": False
                    },
                    "top_k": 10
                },
                {
                    "target": "RESULT",
                    "query": user_message,
                    "filters": {
                        "tags": [],
                        "resource_status": ["active"],
                        "freshness_required": False
                    },
                    "top_k": 10
                }
            ],
            "decision_goal": {
                "primary": "best_fit",
                "ranking_rules": ["correctness", "freshness", "coverage"],
                "must_return_single": True
            },
            "constraints": {
                "need_citations": True,
                "no_fabrication": True,
                "output_format": "steps"
            }
        }

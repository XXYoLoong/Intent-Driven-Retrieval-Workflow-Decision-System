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
决策器（Decider）
支持 OpenAI、DeepSeek、Claude、Qianwen，优先使用 .env 中配置的密钥。
"""
from typing import Dict, Any, List, Optional
import json
from pathlib import Path
from config.constants import ActionType
from config.llm_config import get_llm_model
from services.llm.client import get_openai_compatible_client


class Decider:
    """决策器（LLM-2 或规则+LLM）"""

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
        self.model = model or get_llm_model(None, "decider") or getattr(self.client, "model", None)
        self.prompt_template = self._load_prompt()

    def _load_prompt(self) -> str:
        """加载 prompt 模板"""
        prompt_path = Path(__file__).parent.parent.parent / "prompts" / "decider_v1.md"
        if prompt_path.exists():
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def decide(
        self,
        user_message: str,
        plan: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        policy: Optional[Dict[str, Any]] = None,
        available_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """决策（保证 candidates 可迭代，避免 'bool' object is not iterable）"""
        if not isinstance(candidates, list):
            candidates = []
        # 先应用硬规则
        hard_rule_result = self._apply_hard_rules(candidates, plan)
        if hard_rule_result:
            return hard_rule_result
        
        # 如果硬规则未命中，使用 LLM 决策
        return self._llm_decide(user_message, plan, candidates, policy, available_context)

    def _apply_hard_rules(
        self,
        candidates: List[Dict[str, Any]],
        plan: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """应用硬规则（系统级）"""
        # 规则1: 若存在 RESULT 且 freshness OK 且 total ≥ 0.7 → RETURN_RESULT
        for cand in candidates:
            if cand.get("resource_type") == "RESULT":
                scores = cand.get("scores", {})
                total = scores.get("total", 0.0)
                metadata = cand.get("metadata", {})
                fresh_until = metadata.get("fresh_until")
                
                if total >= 0.7:
                    # 检查新鲜度
                    from datetime import datetime
                    if fresh_until:
                        try:
                            fresh_until_dt = datetime.fromisoformat(fresh_until.replace("Z", "+00:00"))
                            if fresh_until_dt.timestamp() > datetime.utcnow().timestamp():
                                return {
                                    "action_type": ActionType.RETURN_RESULT,
                                    "selected": {
                                        "resource_id": cand["resource_id"],
                                        "resource_type": "RESULT",
                                        "confidence": total
                                    },
                                    "reason": {
                                        "why_best_fit": ["已有新鲜结果", f"分数 {total:.2f}"],
                                        "tradeoffs": []
                                    },
                                    "execution": {
                                        "required": False,
                                        "executor_resource_id": None,
                                        "input": {},
                                        "idempotency_key": None
                                    },
                                    "clarify": {
                                        "required": False,
                                        "questions": []
                                    }
                                }
                        except:
                            pass
        
        # 规则2: 若存在 DOC 且 total ≥ 0.7 → RETURN_RESULT
        for cand in candidates:
            if cand.get("resource_type") == "DOC":
                scores = cand.get("scores", {})
                total = scores.get("total", 0.0)
                if total >= 0.7:
                    return {
                        "action_type": ActionType.RETURN_RESULT,
                        "selected": {
                            "resource_id": cand["resource_id"],
                            "resource_type": "DOC",
                            "confidence": total
                        },
                        "reason": {
                            "why_best_fit": ["文档匹配度高", f"分数 {total:.2f}"],
                            "tradeoffs": []
                        },
                        "execution": {
                            "required": False,
                            "executor_resource_id": None,
                            "input": {},
                            "idempotency_key": None
                        },
                        "clarify": {
                            "required": False,
                            "questions": []
                        }
                    }
        
        return None

    def _llm_decide(
        self,
        user_message: str,
        plan: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        policy: Optional[Dict[str, Any]],
        available_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """LLM 决策"""
        system_prompt = self.prompt_template
        
        # 格式化候选
        candidates_text = json.dumps(candidates, ensure_ascii=False, indent=2)
        
        user_prompt = f"""用户消息：{user_message}

检索计划：
{json.dumps(plan, ensure_ascii=False, indent=2)}

候选资源：
{candidates_text}

请输出决策（严格 JSON 格式）。"""

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
                action_json = json.loads(content)
                
                # 验证并二次校验
                if self._validate_action(action_json, candidates):
                    return action_json
                else:
                    if attempt < max_retries - 1:
                        user_prompt += "\n\n你的输出不符合 schema 或 selected.resource_id 不在 candidates 中，请重新输出。"
                        continue
                    else:
                        # 降级：选择分数最高的
                        return self._fallback_decision(candidates)
            
            except Exception as e:
                if attempt < max_retries - 1:
                    continue
                else:
                    return self._fallback_decision(candidates)
        
        return self._fallback_decision(candidates)

    def _validate_action(
        self,
        action: Dict[str, Any],
        candidates: List[Dict[str, Any]]
    ) -> bool:
        """验证 action schema 并校验 resource_id"""
        required_fields = ["action_type", "selected", "reason", "execution", "clarify"]
        for field in required_fields:
            if field not in action:
                return False
        
        # 验证 selected.resource_id 在 candidates 中
        selected_id = action.get("selected", {}).get("resource_id")
        if selected_id:
            candidate_ids = [c.get("resource_id") for c in candidates]
            if selected_id not in candidate_ids:
                return False
        
        return True

    def _fallback_decision(self, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """降级决策（选择分数最高的）"""
        if not candidates:
            return {
                "action_type": ActionType.FALLBACK,
                "selected": {
                    "resource_id": None,
                    "resource_type": None,
                    "confidence": 0.0
                },
                "reason": {
                    "why_best_fit": ["无候选资源"],
                    "tradeoffs": []
                },
                "execution": {
                    "required": False,
                    "executor_resource_id": None,
                    "input": {},
                    "idempotency_key": None
                },
                "clarify": {
                    "required": False,
                    "questions": []
                }
            }
        
        # 选择分数最高的
        best = max(candidates, key=lambda c: c.get("scores", {}).get("total", 0.0))
        
        return {
            "action_type": ActionType.RETURN_RESULT,
            "selected": {
                "resource_id": best["resource_id"],
                "resource_type": best["resource_type"],
                "confidence": best.get("scores", {}).get("total", 0.0)
            },
            "reason": {
                "why_best_fit": ["分数最高"],
                "tradeoffs": []
            },
            "execution": {
                "required": False,
                "executor_resource_id": None,
                "input": {},
                "idempotency_key": None
            },
            "clarify": {
                "required": False,
                "questions": []
            }
        }

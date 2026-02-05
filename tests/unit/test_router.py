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
单元测试：Router
"""
import pytest
from services.orchestrator.router import IntentRouter


def test_router_default_plan():
    """测试默认计划生成"""
    router = IntentRouter()
    plan = router._default_plan("测试消息")
    
    assert "intent" in plan
    assert "search_plan" in plan
    assert len(plan["search_plan"]) > 0

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
集成测试：完整聊天流程
"""
import pytest
from services.orchestrator.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_chat_flow():
    """测试完整聊天流程"""
    orchestrator = Orchestrator()
    
    result = orchestrator.process(
        user_message="如何重置密码？",
        context={
            "tenant_id": "test_tenant",
            "user_id": "test_user"
        }
    )
    
    assert "answer" in result
    assert "meta" in result
    assert result["meta"]["intent"] is not None

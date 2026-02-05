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

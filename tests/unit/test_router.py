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

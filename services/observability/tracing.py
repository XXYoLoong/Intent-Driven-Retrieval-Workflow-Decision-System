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
可观测性：追踪和日志
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import os
import logging
import structlog
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import Resource

# 配置结构化日志
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False,
)

# 配置 OpenTelemetry
trace.set_tracer_provider(
    TracerProvider(
        resource=Resource.create({"service.name": "intent-system"})
    )
)

# Jaeger 导出器（可选）
jaeger_enabled = os.getenv("JAEGER_ENABLED", "false").lower() == "true"
if jaeger_enabled:
    jaeger_exporter = JaegerExporter(
        agent_host_name=os.getenv("JAEGER_HOST", "localhost"),
        agent_port=int(os.getenv("JAEGER_PORT", "6831"))
    )
    trace.get_tracer_provider().add_span_processor(
        BatchSpanProcessor(jaeger_exporter)
    )

tracer = trace.get_tracer(__name__)
logger = structlog.get_logger()


class TraceLogger:
    """追踪日志记录器"""

    @staticmethod
    def log_router(
        trace_id: str,
        intent: Dict[str, Any],
        plan: Dict[str, Any],
        confidence: float,
        duration_ms: float,
        retry_count: int = 0
    ):
        """记录 Router 日志"""
        logger.info(
            "router_completed",
            trace_id=trace_id,
            intent_name=intent.get("name"),
            intent_confidence=confidence,
            search_plan_count=len(plan.get("search_plan", [])),
            duration_ms=duration_ms,
            retry_count=retry_count
        )

    @staticmethod
    def log_retrieval(
        trace_id: str,
        target: str,
        query: str,
        candidates_count: int,
        top_scores: List[float],
        duration_ms: float
    ):
        """记录检索日志"""
        logger.info(
            "retrieval_completed",
            trace_id=trace_id,
            target=target,
            query=query[:100],  # 截断
            candidates_count=candidates_count,
            top_scores=top_scores[:5],  # 只记录前5个
            duration_ms=duration_ms
        )

    @staticmethod
    def log_decision(
        trace_id: str,
        action_type: str,
        selected_resource_id: str,
        confidence: float,
        rule_hit: Optional[str] = None,
        duration_ms: float = 0.0
    ):
        """记录决策日志"""
        logger.info(
            "decision_completed",
            trace_id=trace_id,
            action_type=action_type,
            selected_resource_id=selected_resource_id,
            confidence=confidence,
            rule_hit=rule_hit,
            duration_ms=duration_ms
        )

    @staticmethod
    def log_execution(
        trace_id: str,
        run_id: str,
        workflow_id: str,
        status: str,
        duration_ms: float,
        errors: Optional[List[Dict[str, Any]]] = None
    ):
        """记录执行日志"""
        logger.info(
            "execution_completed",
            trace_id=trace_id,
            run_id=run_id,
            workflow_id=workflow_id,
            status=status,
            duration_ms=duration_ms,
            errors_count=len(errors) if errors else 0
        )

    @staticmethod
    def log_answer(
        trace_id: str,
        answer_length: int,
        citations_count: int,
        token_count: Optional[int] = None,
        duration_ms: float = 0.0
    ):
        """记录回答日志"""
        logger.info(
            "answer_completed",
            trace_id=trace_id,
            answer_length=answer_length,
            citations_count=citations_count,
            token_count=token_count,
            duration_ms=duration_ms
        )

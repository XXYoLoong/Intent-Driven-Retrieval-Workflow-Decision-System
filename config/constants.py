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
核心常量定义（从 constants.yaml 加载）
"""
from pathlib import Path
from typing import List, Dict, Any
import yaml

_CONFIG_DIR = Path(__file__).parent
_CONSTANTS_FILE = _CONFIG_DIR / "constants.yaml"


def load_constants() -> Dict[str, Any]:
    """加载 constants.yaml 配置"""
    with open(_CONSTANTS_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# 加载配置
_constants = load_constants()

# 导出常量
INTENTS: List[str] = _constants["intents"]
DATA_SOURCES: Dict[str, List[Dict[str, Any]]] = _constants["data_sources"]
STRUCTURED_DATA: Dict[str, Any] = _constants["structured_data"]
WORKFLOW_FORMAT: Dict[str, Any] = _constants["workflow_format"]
CITATIONS: Dict[str, Any] = _constants["citations"]
RESULT_TTL: Dict[str, Any] = _constants["result_ttl"]
MULTI_TENANT: Dict[str, Any] = _constants["multi_tenant"]
OUTPUT_FORMAT: Dict[str, Any] = _constants["output_format"]

# 资源类型枚举
class ResourceType:
    DOC = "DOC"
    WORKFLOW = "WORKFLOW"
    TOOL = "TOOL"
    RESULT = "RESULT"
    STRUCTURED = "STRUCTURED"


# 意图枚举
class Intent:
    KNOWLEDGE_QA = "KNOWLEDGE_QA"
    LOOKUP_STATUS = "LOOKUP_STATUS"
    EXECUTE_TASK = "EXECUTE_TASK"
    DECISION_RECOMMEND = "DECISION_RECOMMEND"
    TROUBLESHOOT = "TROUBLESHOOT"
    ACCOUNT_USER_SPECIFIC = "ACCOUNT_USER_SPECIFIC"
    OTHER = "OTHER"


# 动作类型枚举
class ActionType:
    RETURN_RESULT = "RETURN_RESULT"
    EXECUTE_WORKFLOW = "EXECUTE_WORKFLOW"
    ASK_CLARIFY = "ASK_CLARIFY"
    FALLBACK = "FALLBACK"


# 输出格式枚举
class OutputFormat:
    TEXT = "text"
    STEPS = "steps"
    JSON = "json"
    TABLE = "table"

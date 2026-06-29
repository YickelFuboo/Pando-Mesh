from enum import Enum
from typing import Any


class PlanMode(str, Enum):
    TEMPLATE = "template"
    DYNAMIC = "dynamic"


def normalize_plan_mode(raw: Any) -> str:
    text = str(raw or "").strip().lower()
    if text == PlanMode.DYNAMIC.value:
        return PlanMode.DYNAMIC.value
    return PlanMode.TEMPLATE.value

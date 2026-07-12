import re
from typing import Any, Dict, Optional

SUBJECT_KIND_WORKSPACE = "workspace"
SUBJECT_KIND_FEATURE = "feature"
SUBJECT_KIND_ARCH_ELEMENT = "arch_element"
SUBJECT_KIND_REQUIREMENT = "requirement"
SUBJECT_KIND_REPO = "repo"
DEFAULT_SUBJECT_KIND = SUBJECT_KIND_REQUIREMENT
DEFAULT_GRANULARITY = "ir"

SUBJECT_TYPE_WORKSPACE = "workspace"
SUBJECT_TYPE_FEATURE = "feature"
SUBJECT_TYPE_ARCH_ELEMENT = "arch_element"
SUBJECT_TYPE_IR = "ir"
SUBJECT_TYPE_SR = "sr"
SUBJECT_TYPE_AR = "ar"
SUBJECT_TYPE_REPO = "repo"

SUBJECT_TYPE_SPECS: Dict[str, Dict[str, str]] = {
    SUBJECT_TYPE_WORKSPACE: {"kind": SUBJECT_KIND_WORKSPACE, "granularity": "workspace"},
    SUBJECT_TYPE_FEATURE: {"kind": SUBJECT_KIND_FEATURE, "granularity": "feature"},
    SUBJECT_TYPE_ARCH_ELEMENT: {"kind": SUBJECT_KIND_ARCH_ELEMENT, "granularity": "arch_element"},
    SUBJECT_TYPE_IR: {"kind": SUBJECT_KIND_REQUIREMENT, "granularity": "ir"},
    SUBJECT_TYPE_SR: {"kind": SUBJECT_KIND_REQUIREMENT, "granularity": "sr"},
    SUBJECT_TYPE_AR: {"kind": SUBJECT_KIND_REQUIREMENT, "granularity": "ar"},
    SUBJECT_TYPE_REPO: {"kind": SUBJECT_KIND_REPO, "granularity": "repo"},
}

SUBJECT_TYPE_LABELS: Dict[str, str] = {
    SUBJECT_TYPE_WORKSPACE: "Workspace",
    SUBJECT_TYPE_FEATURE: "特性",
    SUBJECT_TYPE_ARCH_ELEMENT: "架构元素",
    SUBJECT_TYPE_IR: "需求 IR",
    SUBJECT_TYPE_SR: "需求 SR",
    SUBJECT_TYPE_AR: "需求 AR",
    SUBJECT_TYPE_REPO: "代码仓",
}

SUBJECT_TYPE_ORDER = [
    SUBJECT_TYPE_WORKSPACE,
    SUBJECT_TYPE_FEATURE,
    SUBJECT_TYPE_ARCH_ELEMENT,
    SUBJECT_TYPE_IR,
    SUBJECT_TYPE_SR,
    SUBJECT_TYPE_AR,
    SUBJECT_TYPE_REPO,
]

_KNOWN_SUBJECT_KINDS = {
    SUBJECT_KIND_WORKSPACE,
    SUBJECT_KIND_FEATURE,
    SUBJECT_KIND_ARCH_ELEMENT,
    SUBJECT_KIND_REQUIREMENT,
    SUBJECT_KIND_REPO,
}
_PLACEHOLDER_RE = re.compile(r"\{([a-z_]+)\}")


def normalize_subject_type(value: str) -> str:
    key = str(value or "").strip().lower()
    if key in SUBJECT_TYPE_SPECS:
        return key
    if key in {SUBJECT_KIND_WORKSPACE, "workspace"}:
        return SUBJECT_TYPE_WORKSPACE
    if key in {SUBJECT_KIND_FEATURE, "features"}:
        return SUBJECT_TYPE_FEATURE
    if key in {SUBJECT_KIND_ARCH_ELEMENT, "arch_element", "element"}:
        return SUBJECT_TYPE_ARCH_ELEMENT
    if key in {"ir", SUBJECT_KIND_REQUIREMENT}:
        return SUBJECT_TYPE_IR
    if key == "sr":
        return SUBJECT_TYPE_SR
    if key == "ar":
        return SUBJECT_TYPE_AR
    if key in {SUBJECT_KIND_REPO, "repo"}:
        return SUBJECT_TYPE_REPO
    return SUBJECT_TYPE_IR


def subject_type_spec(subject_type: str) -> Dict[str, str]:
    return dict(SUBJECT_TYPE_SPECS[normalize_subject_type(subject_type)])


def subject_type_label(subject_type: str) -> str:
    return SUBJECT_TYPE_LABELS.get(normalize_subject_type(subject_type), subject_type)


def schema_to_subject_type(schema: Dict[str, Any]) -> str:
    kind = str(schema.get("kind") or DEFAULT_SUBJECT_KIND).strip().lower()
    granularity = str(schema.get("granularity") or DEFAULT_GRANULARITY).strip().lower()
    for subject_type, spec in SUBJECT_TYPE_SPECS.items():
        if spec["kind"] == kind and spec["granularity"] == granularity:
            return subject_type
    if kind == SUBJECT_KIND_WORKSPACE:
        return SUBJECT_TYPE_WORKSPACE
    if kind == SUBJECT_KIND_FEATURE:
        return SUBJECT_TYPE_FEATURE
    if kind == SUBJECT_KIND_ARCH_ELEMENT:
        return SUBJECT_TYPE_ARCH_ELEMENT
    if kind == SUBJECT_KIND_REPO:
        return SUBJECT_TYPE_REPO
    return SUBJECT_TYPE_IR


def normalize_subject_schema(raw: Any) -> Dict[str, Any]:
    data = raw if isinstance(raw, dict) else {}
    kind = str(data.get("kind") or DEFAULT_SUBJECT_KIND).strip().lower()
    if kind not in _KNOWN_SUBJECT_KINDS:
        kind = DEFAULT_SUBJECT_KIND
    granularity = str(data.get("granularity") or DEFAULT_GRANULARITY).strip().lower() or DEFAULT_GRANULARITY
    required = data.get("required_placeholders")
    placeholders = (
        [str(item).strip() for item in required if str(item).strip()]
        if isinstance(required, list)
        else []
    )
    auto_expand = bool(data.get("auto_expand"))
    return {
        "kind": kind,
        "granularity": granularity,
        "required_placeholders": placeholders,
        "auto_expand": auto_expand,
        "subject_type": schema_to_subject_type(
            {"kind": kind, "granularity": granularity},
        ),
    }


def infer_subject_schema_from_template(
    *,
    user_goal: str = "",
    description: str = "",
    graph: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    text_parts = [user_goal, description]
    if isinstance(graph, dict):
        text_parts.append(str(graph))
    text = "\n".join(part for part in text_parts if part)
    placeholders = set(_PLACEHOLDER_RE.findall(text))
    if "workspace" in placeholders and "requirement_id" not in placeholders:
        return normalize_subject_schema({"kind": SUBJECT_KIND_WORKSPACE, "granularity": "workspace"})
    if "feature" in placeholders or "feature_id" in placeholders:
        return normalize_subject_schema({"kind": SUBJECT_KIND_FEATURE, "granularity": "feature"})
    if "element_id" in placeholders or "element_path" in placeholders:
        return normalize_subject_schema({"kind": SUBJECT_KIND_ARCH_ELEMENT, "granularity": "arch_element"})
    granularity = DEFAULT_GRANULARITY
    if "repo_id" in placeholders:
        return normalize_subject_schema({"kind": SUBJECT_KIND_REPO, "granularity": "repo"})
    if "sr_id" in placeholders:
        granularity = "sr"
    elif "ar_id" in placeholders:
        granularity = "ar"
    return normalize_subject_schema({"kind": SUBJECT_KIND_REQUIREMENT, "granularity": granularity})


def resolve_template_subject_schema(template: Any) -> Dict[str, Any]:
    explicit = getattr(template, "subject_schema", None)
    if isinstance(explicit, dict) and str(explicit.get("kind") or "").strip():
        return normalize_subject_schema(explicit)
    return infer_subject_schema_from_template(
        user_goal=str(getattr(template, "user_goal", "") or ""),
        description=str(getattr(template, "description", "") or ""),
        graph=getattr(template, "graph", None),
    )


def template_matches_subject_type(template: Any, subject_type: str) -> bool:
    schema = resolve_template_subject_schema(template)
    expected = subject_type_spec(subject_type)
    return (
        schema.get("kind") == expected["kind"]
        and schema.get("granularity") == expected["granularity"]
    )

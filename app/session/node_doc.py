from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.graph.plan_graph import DirectExecGraph, GraphNode
from app.workspace.markdown_meta import normalize_meta, split_markdown_frontmatter
from app.workspace.paths import normalize_workspace_path
from app.workspace.requirements import requirement_path
from app.workspace.refs import (
    NodeWorkspaceRef,
    expand_workspace_ref_paths,
    inspect_workspace_refs,
    resolve_workspace_ref_path,
)


@dataclass(frozen=True)
class NodeDocResult:
    node_id: str
    label: str
    content: str
    source_path: str = ""
    generated: bool = False
    workspace_refs: List[Dict[str, Any]] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "label": self.label,
            "content": self.content,
            "source_path": self.source_path,
            "generated": self.generated,
            "workspace_refs": list(self.workspace_refs),
            "meta": dict(self.meta),
        }


def _read_doc_text(path: Path) -> tuple[str, Dict[str, Any]]:
    text = _read_text(path)
    if not text:
        return "", {}
    meta, body = split_markdown_frontmatter(text)
    return body, normalize_meta(meta)


def _read_text(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _node_doc_refs_for_inspect(node: GraphNode) -> List[NodeWorkspaceRef]:
    refs: List[NodeWorkspaceRef] = []
    for path in node.input_doc_paths or []:
        text = str(path or "").strip()
        if text:
            refs.append(NodeWorkspaceRef(path=text, label="输入"))
    for path in node.output_doc_paths or []:
        text = str(path or "").strip()
        if text:
            refs.append(NodeWorkspaceRef(path=text, label="输出"))
    return refs


def _resolve_configured_paths(
    workspace_path: str,
    requirement_id: str,
    paths: List[str],
) -> List[Path]:
    resolved: List[Path] = []
    seen: set[str] = set()
    for ref_path in paths or []:
        text = str(ref_path or "").strip()
        if not text:
            continue
        matches = expand_workspace_ref_paths(workspace_path, requirement_id, text)
        if not matches:
            item = resolve_workspace_ref_path(workspace_path, requirement_id, text)
            if item is not None:
                matches = [item]
        for item in matches:
            key = str(item)
            if key in seen:
                continue
            seen.add(key)
            resolved.append(item)
    return resolved


def _candidate_doc_paths(
    workspace_path: str,
    requirement_id: str,
    req_dir: Path,
    node: GraphNode,
) -> List[Path]:
    paths: List[Path] = []
    paths.extend(_resolve_configured_paths(workspace_path, requirement_id, list(node.input_doc_paths or [])))
    paths.extend(_resolve_configured_paths(workspace_path, requirement_id, list(node.output_doc_paths or [])))
    node_id = (node.id or "").strip()
    label = (node.label or "").strip()
    if node_id:
        paths.extend([
            req_dir / f"{node_id}.md",
            req_dir / "nodes" / f"{node_id}.md",
            req_dir / "docs" / f"{node_id}.md",
            req_dir / "steps" / f"{node_id}.md",
        ])
    if label and label != node_id:
        paths.extend([
            req_dir / f"{label}.md",
            req_dir / "nodes" / f"{label}.md",
            req_dir / "docs" / f"{label}.md",
        ])
    seen: set[str] = set()
    unique: List[Path] = []
    for path in paths:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def _generated_doc(node: GraphNode, node_output: str = "") -> str:
    lines = [
        f"# {node.label or node.id}",
        "",
        f"- **节点 ID**：`{node.id}`",
    ]
    if node.phase:
        lines.extend(["", f"- **Phase**：{node.phase}"])
    if node.task:
        lines.extend(["", "## 任务说明", "", node.task.strip()])
    if node_output.strip():
        lines.extend(["", "## 执行产出", "", "```", node_output.strip(), "```"])
    input_lines = [f"- `{path}`" for path in node.input_doc_paths or [] if str(path or "").strip()]
    output_lines = [f"- `{path}`" for path in node.output_doc_paths or [] if str(path or "").strip()]
    if input_lines:
        lines.extend(["", "## 输入文档路径", ""] + input_lines)
    if output_lines:
        lines.extend(["", "## 输出文档路径", ""] + output_lines)
    lines.extend([
        "",
        "## 文档约定",
        "",
        "可在节点配置中指定输入/输出文档路径，",
        "也可在需求目录下放置以下任一文件作为该步骤文档：",
        "",
        f"- `{node.id}.md`",
        f"- `nodes/{node.id}.md`",
        f"- `docs/{node.id}.md`",
    ])
    return "\n".join(lines)


def load_requirement_readme(workspace_path: str, requirement_id: str) -> Optional[NodeDocResult]:
    ws = normalize_workspace_path(workspace_path)
    if not ws or not requirement_id:
        return None
    try:
        req_dir = requirement_path(ws, requirement_id)
    except (FileNotFoundError, ValueError):
        return None
    for name in ("README.md", "readme.md", "requirement.md", "spec.md"):
        path = req_dir / name
        body, meta = _read_doc_text(path)
        if body:
            return NodeDocResult(
                node_id="",
                label="需求说明",
                content=body,
                source_path=str(path.resolve()),
                generated=False,
                meta=meta,
            )
    return None


def load_node_doc(
    *,
    workspace_path: str,
    requirement_id: str,
    graph: DirectExecGraph,
    node_id: str,
    node_output: str = "",
) -> NodeDocResult:
    key = (node_id or "").strip()
    node = graph.nodes.get(key)
    if node is None:
        raise KeyError(node_id)
    label = node.label or node.id
    workspace_refs: List[Dict[str, Any]] = []
    ws = normalize_workspace_path(workspace_path)
    if ws:
        workspace_refs = inspect_workspace_refs(
            workspace_path=ws,
            requirement_id=requirement_id,
            refs=_node_doc_refs_for_inspect(node),
        )
    if requirement_id and ws:
        try:
            req_dir = requirement_path(ws, requirement_id)
            for path in _candidate_doc_paths(ws, requirement_id, req_dir, node):
                body, meta = _read_doc_text(path)
                if body:
                    return NodeDocResult(
                        node_id=node.id,
                        label=label,
                        content=body,
                        source_path=str(path.resolve()),
                        generated=False,
                        workspace_refs=workspace_refs,
                        meta=meta,
                    )
        except (FileNotFoundError, ValueError):
            pass
    return NodeDocResult(
        node_id=node.id,
        label=label,
        content=_generated_doc(node, node_output),
        source_path="",
        generated=True,
        workspace_refs=workspace_refs,
    )

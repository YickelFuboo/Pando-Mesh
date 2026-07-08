# 工作流扩展规划

## 扩展任务（来自 expand 节点 task）

{{ expand_task }}

## 上下文

- requirement_id: {{ requirement_id }}
- workspace: {{ workspace_path }}
- 默认 lane 模板: {{ default_lane_template_id }}

## 当前 Graph（expand 槽位附近）

{{ graph_context }}

## Workspace 扫描文件

{{ scanned_files }}

## 可选 Lane 模板

{{ template_catalog }}

## 输出要求

仅输出一个 JSON 对象（不要 markdown 代码块），格式：

{% raw %}
{
  "version": 1,
  "lanes": [
    {
      "id": "sr_001",
      "label": "SR-001-标题",
      "template_id": "tpl_sr_to_ar",
      "placeholders": {
        "branch_id": "sr_001",
        "sr_id": "SR-001",
        "sr_doc": "requirements/REQ-xxx/feature_changes/.../SR-001-xxx.md"
      },
      "skip_nodes": ["gate_ar_confirm"],
      "node_overrides": {}
    }
  ]
}
{% endraw %}

规则：
- 每个待扩展分支一条 lane
- template_id 必须从「可选 Lane 模板」中选择；未指定时使用默认模板
- placeholders 填齐模板所需占位符；sr_doc 等为相对 workspace 的路径
- 无接口变更等场景可在 skip_nodes 中列出要跳过的模板节点 id
- 若只需简单单节点分支，可改用 {"tasks":[...]} 格式（与 lanes 二选一）

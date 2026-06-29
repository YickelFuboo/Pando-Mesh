# 建图任务（当轮 user）

## 用户任务

{{ user_goal }}

## 可编排 Agent

{{ agent_catalog }}

## JSON 格式

{% raw %}
{
  "nodes": [
    {
      "id": "步骤id",
      "label": "中文名",
      "task": "该步骤任务说明",
      "max_iterations": 3,
      "executor": {
        "kind": "cli",
        "cli": {
          "commands": [{"command": "claude", "args": ["-p", "--output-format", "json"]}],
          "input": "arg",
          "cwd": "{workspace}",
          "output_mode": "json",
          "result_json_key": "result"
        }
      }
    }
  ],
  "edges": [
    {"from": "START", "to": "首步骤id", "condition": "always"},
    {"from": "步骤A", "to": "步骤B", "condition": "always"},
    {"from": "审查步骤", "to": "被审步骤", "condition": "reject"},
    {"from": "审查步骤", "to": "下一步骤", "condition": "pass"},
    {"from": "末步骤", "to": "END", "condition": "always"}
  ],
  "entry": "首步骤id"
}
{% endraw %}

请根据用户任务输出符合上述 schema 的 JSON 执行图；可先简要说明，再给出 JSON。

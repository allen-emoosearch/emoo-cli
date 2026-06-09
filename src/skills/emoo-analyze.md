---
name: emoo-analyze
description: 智能分析 EMOO 企微群聊 — KM 匹配群 → 定向搜索 → 去重聚合 → Markdown 输出
type: scenario
category: 系统
tags: [搜索, 聊天, 分析, 必装]
emoo:
  search:
    keyword: "{query}"
    page_size: 200
  params:
    query:
      description: 自然语言查询，如 "近一周发货"、"近一个月报销"、"机器故障"
      required: true
      example: 近一周发货
---

# EMOO 群聊智能分析

## 说明

分析企微群聊记录：KM 匹配群 → 并发搜索 → 去重降噪 → 结构化输出。
CLI 负责拉数据，AI 工具负责总结。

## 使用方式

```bash
# Markdown 输出 (推荐: AI 工具直接消费)
emoo skill pipeline analyze "{query}" --format md

# JSON 输出 (程序消费)
emoo --json skill pipeline analyze "{query}"
```

## 执行流程

```
1. emoo skill pipeline analyze "<query>" --format md
2. 检查 source_total、matched_total 和实际结果数
3. 将全部查询结果交给 AI
4. AI 负责去重、关联上下文和总结
5. 不使用 CLI 内置总结
```

## 搜索策略

### 聊天/群消息 → analyze 管道
```bash
emoo skill pipeline analyze "近一周话题" --format md
emoo --json skill pipeline analyze "近一个月发货"
```

### 文档/知识库 → data search
```bash
emoo data search -k "关键词" -f '{"field":"ws_app.ws_app_key","operator":"eq","value":"<key>"}'
```

### 结构化表格 → base record-list
```bash
emoo base record-list --table-name "表名" -f "content:contains:关键词"
```

## 时间表达支持

近一周 / 近一个月 / 近N天 / 今天 / 昨天 / 本周 / 本月 / 上个季度

## 输出格式

| 格式 | 用法 | 适用 |
|------|------|------|
| `text` | 默认 | 人类阅读 |
| `md` | `--format md` | **AI 工具消费 (推荐)** |
| `json` | `--json` | 程序处理 |

## 前置条件

```bash
emoo auth login --api-key <key>
emoo skill init
emoo skill pipeline knowledge-map --auto --ttl 24h
```

## 注意事项

1. 必须先有知识图谱缓存 (`knowledge-map --auto`)
2. select 字段用简单值 `"value"`，不能 `["value"]`
3. reference 字段必须数组 `["key"]`
4. user/group 字段用数字 ID，不能 open_id/名字
5. 文档 search 端点硬上限 500 条，超过用 data get

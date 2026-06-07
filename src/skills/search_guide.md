---
name: emoo-search-guide
description: EMOO搜索策略 — 用知识图谱驱动的智能搜索替代盲目keyword搜索
type: scenario
category: 系统
tags: [搜索, 指南, 必读]
emoo:
  search:
    keyword: "{query}"
    page_size: 200
  params:
    query:
      description: 要搜索的问题或关键词
      required: true
      example: 近一周发货情况
---

# EMOO 搜索指南

## 搜索决策树 (必须按此顺序)

```
用户提问
  │
  ├─ 是聊天/群消息相关？
  │   → emoo skill pipeline analyze "<query>"
  │     自动: KM匹配群 → 定向搜索 → 聚合
  │
  ├─ 是文档/知识库搜索？
  │   → emoo data search -k "<keyword>" -f '<app_filter>'
  │     ⚠️ 不要裸搜！先用 KM 确定 ws_app_key
  │
  ├─ 是数据库表查询？
  │   → emoo base record-list --table-name "<name>" -f "..."
  │     支持: contains(模糊)/eq/gte/lte 操作符
  │
  └─ 不确定？
      → 先: emoo skill pipeline knowledge-map --auto --ttl 24h
        再看 KM 输出决定用哪个命令
```

## 关键规则

1. **KM 优先**: 任何搜索前，确保 KM 缓存有效 (24h)
2. **analyze 管道的威力**: 一条命令 = KM匹配 + 时间解析 + 关键词扩展 + 多群搜索 + 聚合
3. **不要裸搜**: `emoo data search -k "xxx"` 不传 filter 会搜全企业，效率低
4. **Base 表优先 contains**: `content:contains:关键词` 用于模糊搜索

## 常用模式

```bash
# 聊天分析 (最常用)
emoo skill pipeline analyze "近一周发货情况"
emoo skill pipeline analyze "近一个月报销"
emoo skill pipeline analyze "机器故障"

# 文档搜索 (带filter)
emoo data search -k "关键词" -f '{"field":"ws_app.ws_app_key","operator":"eq","value":"<从KM获取>"}'

# Base表搜索
emoo base record-list --table-name "<表名>" -f "content:contains:关键词,msgtime:gte:2026-06-01"
```

## 工作区管理

```bash
emoo auth switch              # 列出可用配置
emoo auth switch <name>       # 切换工作区
emoo auth switch --save <name> # 保存当前配置
```

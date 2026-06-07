---
name: emoo-search-guide
description: EMOO 搜索策略指南 v5 — KM驱动 + 并发加速 + 全量可审计
type: scenario
category: 系统
tags: [搜索, 指南, 必读]
emoo:
  search:
    keyword: "{query}"
    page_size: 200
  params:
    query:
      description: 搜索关键词
      required: true
      example: 近一周话题
---

# EMOO 搜索指南 v5

## 核心原则

**CLI 负责拉数据，AI 工具负责总结。** KM 驱动，不要裸搜。

---

## 一、初始化

```bash
emoo auth login --api-key <key>
emoo skill init
emoo skill pipeline knowledge-map --auto --ttl 24h
```

---

## 二、命令速查

| 搜索类型 | 命令 |
|----------|------|
| 🗨️ 聊天/群消息 | `emoo skill pipeline analyze` |
| 📄 文档/知识库 | `emoo data search` (需带 filter) |
| 📊 结构化表格 | `emoo base record-list` |
| 📦 大量拉取 | `emoo data get` (无500上限) |

---

## 三、聊天分析 `analyze`

```bash
emoo skill pipeline analyze "近一周话题"
emoo --json skill pipeline analyze "近一个月发货"
```

### 工作流程

```
用户查询 → AI时间解析 → 关键词提取 → AI关键词扩展
  → KM匹配群 → 5群并发 → 群内并发翻页
  → msgid+content+时间三重去重 → 输出结构化数据
```

### 选项

| 选项 | 说明 |
|------|------|
| `--compact` | 精简输出 |
| `--no-probe-filter` | 不过滤测试数据 |

### 时间表达

近一周/近一个月/近N天/今天/昨天/本周/本月/上个季度

### JSON 输出

```json
{
  "total": 242, "keywords": ["发货"],
  "time_range": ["2026-05-07", "2026-06-07"],
  "daily_summary": {"2026-06-01": 26},
  "matched_rooms": [{"name": "发货群", "group_id": "wrYK...", "reasons": [...]}],
  "results": [{
    "time": "2026-06-01", "user": "xxx",
    "msgid": "msg_xxx", "content": "...",
    "group": "wrYK...", "group_name": "发货群"
  }]
}
```

> AI 工具拿 JSON 自行分析，无需 CLI 内置总结。

---

## 四、文档搜索 `data search`

```bash
emoo data search -k "关键词" -f '{"field":"ws_app.ws_app_key","operator":"eq","value":"<key>"}'
emoo data search -k "关键词" --max-results 500
# ⚠️ 硬上限500, 超过用 data get
```

---

## 五、Base 表操作 `base`

```bash
# 记录查询
emoo base record-list --table-name "xxx" -f "content:contains:关键词"
emoo base record-list --table-name "xxx" --room-id "wrYK..."
emoo base record-list --table-name "xxx" -f "..." --max-results 500
# 返回含 _source_total/_source_pages/_matched_total 可审计

# 字段类型写入格式
# select → "value" (不能 ["value"])
# reference → ["key"] (必须数组)
# user/group → 数字ID (不能 open_id/名字)
```

---

## 六、工作区管理

```bash
emoo auth switch              # 列出
emoo auth switch <name>       # 切换
emoo auth switch --save <name> # 保存
emoo auth clear-cache         # 清除缓存
```

---

## 七、性能

| 特性 | 说明 |
|------|------|
| 群间并发 | 5线程 |
| 群内翻页 | 首页后剩余页并发 |
| 三重去重 | msgid + content hash + 时间用户 |
| 速度 | 近一周~8s, 近一月~15s |

---

## 八、禁止

1. ❌ 裸搜
2. ❌ 聊天用 data search
3. ❌ select 用数组
4. ❌ reference 不用数组
5. ❌ user/group 用 open_id

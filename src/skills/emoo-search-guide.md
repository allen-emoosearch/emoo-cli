---
name: emoo-search-guide
description: EMOO 搜索策略指南 v4 — KM驱动 + AI总结 + 并发加速 + 可审计全量
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

# EMOO 搜索指南 v4

## 核心原则

**KM 驱动，不要裸搜。** 先用知识图谱了解数据源，再选择对应命令。

---

## 一、初始化

```bash
emoo auth login --api-key <key>                     # 登录
emoo skill init                                      # 初始化 + 安装本指南
emoo skill pipeline knowledge-map --auto --ttl 24h   # 生成知识图谱 (必须！)
```

---

## 二、命令速查

| 搜索类型 | 命令 | 说明 |
|----------|------|------|
| 🗨️ 聊天/群消息 | `emoo skill pipeline analyze` | KM匹配群 → 全量拉取 → AI总结 |
| 📄 文档/知识库 | `emoo data search` | 需带KM来的 filter |
| 📊 结构化表格 | `emoo base record-list` | 支持 contains/eq/gte/lte |
| 📦 大量拉取 | `emoo data get` | 无500上限，支持 --stream |

---

## 三、聊天分析 `analyze` (最常用)

```bash
# 结构化输出
emoo skill pipeline analyze "近一周话题"

# AI 总结模式 — 拉全量送模型，最准确
emoo skill pipeline analyze "近一个月发货" --summarize

# JSON 输出 — 返回全量结果 + msgid
emoo --json skill pipeline analyze "近一周话题"
```

### 工作流程

```
用户查询 → AI时间解析 → 关键词提取 → AI关键词扩展 → KM匹配群
  → 5群并发 → 群内并发翻页 → msgid+content双重去重
  → (可选)AI总结 → 输出(含群名称+覆盖度)
```

### 选项

| 选项 | 说明 |
|------|------|
| `--summarize` | AI 自动总结 (拉全量，无关键词过滤) |
| `--compact` | 精简输出 (仅 time/from/content/group) |
| `--no-probe-filter` | 不过滤测试数据 |

### 时间表达

近一周/近一个月/近N天/今天/昨天/本周/本月/上个季度 (AI模型解析)

### JSON 输出字段

```json
{
  "total": 154,                          // 去重后匹配数
  "sampling": "stratified_by_day",       // full 或 stratified_by_day
  "daily_summary": {"2026-06-01": 26},   // 每日原始消息量
  "results": [{                          // 全量结果
    "time": "2026-06-01", "user": "xxx",
    "msgid": "msg_xxx",                  // 原始消息ID
    "content": "...", "group": "wrYK...",
    "group_name": "发货群"               // 可读群名
  }],
  "ai_summary": "...",                   // AI总结(仅--summarize)
  "ai_summary_source_count": 154,        // 送入模型的记录数
  "ai_summary_truncated": false,         // 是否截断
  "matched_rooms": [{"name": "发货群", "reasons": [...]}]
}
```

---

## 四、文档搜索 `data search`

```bash
emoo data search -k "关键词" -f '{"field":"ws_app.ws_app_key","operator":"eq","value":"<km_key>"}'
emoo data search -k "关键词" --max-results 500
# 过滤字段: ws_app.ws_app_key / doc_group.app_group_id / app_created_at / app_updated_at
# 运算符: eq, neq, in, nin, gte, lte
# ⚠️ 硬上限500, 超过用 data get
```

---

## 五、Base 表操作 `base`

```bash
# 表/字段管理
emoo base table-list / table-get / table-create / table-update / table-delete
emoo base column-add / column-update / column-delete

# 记录查询
emoo base record-list --table-name "xxx" -f "field:eq:value"
emoo base record-list --table-name "xxx" -f "content:contains:关键词"  # 模糊搜索
emoo base record-list --table-name "xxx" --room-id "wrYK..."            # 按群过滤
emoo base record-list --table-name "xxx" --group-field "roomid"         # 指定群字段
emoo base record-list --table-name "xxx" --max-results 500              # 自动翻页
# 返回值含 _source_total/_source_pages 可审计翻了多少源数据

# 增删改
emoo base record-create --table-name "xxx" -r '[{"字段":"值"}]'
emoo base record-update --table-name "xxx" --record-key "k" -f '{"字段":"新值"}'
emoo base record-delete --table-name "xxx" -k '["key1","key2"]'
```

### 字段类型写入格式

| 类型 | 写入 | ⚠️ |
|------|------|-----|
| string/number/date/time/datetime | 直接值 | |
| boolean | `true`/`false` | 返回 1/0 |
| select | `"value"` | ❌ 不能 `["value"]` |
| reference | `["key"]` | ❌ 必须数组 |
| user/group | 数字ID | ❌ 不能 open_id/名字 |

---

## 六、工作区管理

```bash
emoo auth switch              # 列出可用配置
emoo auth switch <name>       # 切换工作区
emoo auth switch --save <name> # 保存当前配置
emoo auth status              # 查看认证状态
emoo auth set-base-url <url>  # 设置/查看 Base URL
emoo auth clear-cache         # 清除请求缓存
```

---

## 七、性能特性

| 特性 | 说明 |
|------|------|
| 群间并发 | 5线程 |
| 群内翻页 | 首页后剩余页并发 |
| 业务去重 | msgid优先 + content hash |
| 速度 | 近一周~8s, 近一月~15s |
| 缓存 | GET请求5min, KM 24h |

---

## 八、禁止事项

1. ❌ 不查KM就裸搜
2. ❌ 聊天查询用 data search 而不是 analyze
3. ❌ select 用数组 → 报错"选项值无效"
4. ❌ reference 不用数组 → 存空
5. ❌ user/group 用 open_id/名字 → 报错
6. ❌ data search 超500条不用 data get

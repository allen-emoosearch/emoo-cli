---
name: emoo-search-guide
description: EMOO 搜索策略指南 — KM驱动的智能搜索，覆盖聊天/文档/Base全部场景
type: scenario
category: 系统
tags: [搜索, 指南, 必读, 初始化]
emoo:
  search:
    keyword: "{query}"
    page_size: 200
  params:
    query:
      description: 搜索关键词
      required: true
      example: 搜索关键词
---

# EMOO 搜索指南 v2

## 核心原则

**KM 驱动，不要裸搜。** 任何搜索前先确保知识图谱缓存有效 (7d)。
⚠️ **`analyze` 不是万能的 — 只处理聊天/群消息。文档和表格用对应命令。**

---

## 一、初始化流程

```bash
emoo auth login --api-key <key>                    # 登录
emoo skill init                                     # 创建目录 + 注册 symlink + 安装本指南
emoo skill pipeline knowledge-map --auto --ttl 7d  # 生成知识图谱 (必须！)
```

---

## 二、搜索决策树

⚠️ **analyze 只覆盖聊天/群消息。** 文档和表格必须用对应命令。

```
用户提问
  │
  ├─ 是聊天/群消息？ ← 🗨️ analyze
  │   → emoo skill pipeline analyze "<自然语言查询>"
  │     原理: KM匹配群 → API 时间+群过滤 → 客户端关键词 → 去重聚合
  │     示例: "近一周群内消息" / "本月有哪些讨论"
  │     ⚠️ 前提: KM里必须有 type=chat 的 Base 表(聊天记录表)
  │
  ├─ 是文档/知识库？ ← 📄 data search
  │   → emoo data search -k "<keyword>" -f '<filter>'
  │     ⚠️ 必须从 KM 获取 ws_app_key 加 filter，不要裸搜！
  │
  ├─ 是数据库表？ ← 📊 base record-list
  │   → emoo base record-list --table-name "<从KM获取>" -f "..."
  │     支持: eq / gte / lte / contains(模糊)
  │
  ├─ 是大范围全量拉取？ ← 📦 data get
  │   → emoo data get --max-results N [-f '<filter>']
  │     无500硬上限，--stream 流式输出
  │
  └─ 不确定？
     → 先: emoo skill pipeline knowledge-map --auto --ttl 7d  ← KM 告诉你一切
```

## 三、各命令详解

### 3.1 聊天分析 `analyze` (最常用, 但仅限聊天)

```bash
emoo skill pipeline analyze "<自然语言查询>"
```

**自动步骤:** AI时间解析 → 提取关键词 → AI扩展 → KM匹配群 → 定向搜索 → 去重聚合

**时间表达式:** 近一周/近一个月/近3天/今天/昨天/本周/本月/上个季度

**⚠️ 限制:** 只在KM有 type=chat 的Base表时可用。无聊天表时报「未找到聊天表」。
**⚠️ 长时间范围(>7天)限制每群1页，可能不全。**

---

### 3.2 文档搜索 `data search` (文档/报告/制度)

```bash
# 基本搜索 (⚠️ 尽量带filter)
emoo data search -k "关键词" -f '{"field":"ws_app.ws_app_key","operator":"eq","value":"<key>"}'

# 自动翻页 (⚠️ 硬上限500)
emoo data search -k "关键词" --max-results 500

# 过滤条件 (简写自动包装)
emoo data search -k "关键词" -f '{"field":"app_updated_at","operator":"gte","value":"2026-01-01"}'

# 过滤字段: ws_app.ws_app_key / doc_group.app_group_id / app_created_at / app_updated_at
# 运算符: eq, neq, in, nin, gte, lte
# ⚠️ search 端点硬上限 500 条，超过请用 data get
```

### 3.3 数据获取 `data get` (无上限)

```bash
emoo data get --max-results 5000 -f '<filter>'
emoo data get --stream -f '<filter>'         # 流式JSON Lines
emoo data get --max-results 10000 --json | jq '.data.results'  # 管道处理
```

### 3.4 Base 表操作 `base`

**表和字段管理:**
```bash
emoo base table-list / table-get / table-create / table-update / table-delete
emoo base column-add / column-update / column-delete
```

**记录查询 (最常用):**
```bash
# API 过滤
emoo base record-list --table-name "xxx" -f "field:eq:value,field2:gte:2026-06-01"

# 模糊搜索 (客户端)
emoo base record-list --table-name "xxx" -f "content:contains:关键词"

# 按群过滤 (聊天表)
emoo base record-list --table-name "xxx" --room-id "wrYK..." -f "msgtime:gte:..."

# 自动翻页
emoo base record-list --table-name "xxx" --max-results 500
```

**字段类型写入格式:**
| 类型 | 写入 | ⚠️ |
|------|------|-----|
| string/number/date/time/datetime | 直接值 | |
| boolean | `true`/`false` | 返回 1/0 |
| select | `"value"` | ❌ 不能 `["value"]` |
| reference | `["key"]` | ❌ 必须数组 |
| user/group | 数字ID(`123`) | ❌ 不能 open_id/名字 |
| file | `"https://..."` | |

### 3.5 工作区管理

```bash
emoo auth switch              # 列出配置
emoo auth switch <name>       # 切换
emoo auth switch --save <name> # 保存
emoo auth status              # 查看状态
emoo --base-url <url> ...     # 临时切换
```

### 3.6 缓存

```bash
emoo --cache-ttl 600 ...     # 自定义TTL(秒)
emoo --no-cache ...           # 禁用缓存
emoo auth clear-cache         # 清除全部缓存
```

---

## 四、命令速查

| 搜索类型 | 命令 |
|----------|------|
| 🗨️ 聊天/群消息 | `emoo skill pipeline analyze` |
| 📄 文档/知识库 | `emoo data search` (需带 KM 来的 filter) |
| 📊 结构化表格 | `emoo base record-list` (CRUD 查询) |
| 📦 大量拉取 | `emoo data get` (无 500 上限) |

---

## 五、禁止事项

1. ❌ 不查KM就裸搜 `emoo data search -k "xxx"`
2. ❌ 聊天查询用 `data search` 而不是 `analyze`
3. ❌ select 用数组格式 `["value"]` → 报错"选项值无效"
4. ❌ reference 不用数组 → 存空
5. ❌ user/group 用 open_id 或名字 → 报错"字段值无效"
6. ❌ `data search` 超 500 条不加 `--max-results` 不知道截断

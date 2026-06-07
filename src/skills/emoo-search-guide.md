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
      example: 发货
---

# EMOO 搜索指南 v2

## 核心原则

**KM 驱动，不要裸搜。** 任何搜索前先确保知识图谱缓存有效 (24h)。

---

## 一、初始化流程

```bash
# 1. 登录
emoo auth login --api-key <key>

# 2. 初始化
emoo skill init          # 创建目录 + 注册到 Claude Code + 安装本指南

# 3. 生成知识图谱 (必须！)
emoo skill pipeline knowledge-map --auto --ttl 24h

# 4. 查看知识图谱
# JSON: ~/.emoo/knowledge_map/<ws>/emoo_knowledge_map.json
# MD:   ~/.emoo/knowledge_map/<ws>/emoo_knowledge_map.md
```

---

## 二、搜索决策树

```
用户提问
  │
  ├─ 聊天/群消息查询？
  │   → emoo skill pipeline analyze "<自然语言查询>"
  │     时间: 近一周/近一个月/今天/昨天/上个季度 (AI模型解析)
  │     关键词: 自动提取 + AI语义扩展
  │     原理: KM匹配群 → 定向搜索 → 去重聚合
  │     示例: "近一周发货情况" / "近一个月报销" / "机器故障"
  │
  ├─ 文档搜索？(报告、制度、记录)
  │   → emoo data search -k "<keyword>" [--max-results N] [-f '<filter>']
  │     ⚠️ 务必带 filter (ws_app_key)，从KM获取！
  │     示例: emoo data search -k "报销" -f '{"field":"ws_app.ws_app_key","operator":"eq","value":"<km_app_key>"}'
  │
  ├─ 数据库表查询？(CRM、项目、投资)
  │   → emoo base record-list --table-name "<name>" -f "..." [--room-id <id>] [--max-results N]
  │     支持: eq/gte/lte/contains 操作符
  │     ⚠️ contains 是客户端过滤，大小写不敏感，支持中文
  │     示例: emoo base record-list --table-name "xxx" -f "content:contains:关键词,msgtime:gte:2026-06-01"
  │
  ├─ 大范围全量拉取？
  │   → emoo data get --max-results N [-f '<filter>']
  │     无500硬上限，游标翻页
  │     --stream 流式输出，适合管道处理
  │
  └─ 不确定？
      → 先: emoo skill pipeline knowledge-map --auto --ttl 24h  (检查KM)
      → 再: emoo skill list  (看看有没有现成skill)
      → 最后根据KM里的信息决定用哪个命令
```

---

## 三、各命令详解

### 3.1 智能分析管道 (最强大)

```bash
emoo skill pipeline analyze "<自然语言查询>"
```

**自动完成的步骤:**
1. AI解析时间 → "近一周" → 2026-06-01~2026-06-07
2. 提取关键词 → "发货" 
3. AI扩展关键词 → ["发货","物流","装车","运输","配送"]
4. 从KM匹配聊天群 → 3个群命中
5. 对每个群定向搜索 (API时间+roomid过滤)
6. 客户端关键词过滤 + 去重
7. 聚合: 每日分布、关键人物、样本消息

**时间表达式支持:**
- 近一周/近一个月/近3天
- 今天/昨天/本周/本月
- 上个季度/去年 (AI模型解析)

---

### 3.2 文档搜索

```bash
# 基本搜索
emoo data search -k "关键词"

# 带分页
emoo data search -k "报告" --page-size 20 --current-page 1

# 自动翻页 (最多500条)
emoo data search -k "上海" --max-results 500

# 过滤条件 (外层OR, 内层AND)
emoo data search -k "关键词" -f '[[{"field":"ws_app.ws_app_key","operator":"eq","value":"<key>"}]]'

# 从文件加载过滤
emoo data search -k "关键词" -f ./filter.json

# 简写格式 (自动包装)
emoo data search -k "关键词" -f '{"field":"ws_app.ws_app_key","operator":"eq","value":"<key>"}'

# ⚠️ search 端点硬上限 500 条，翻页无法突破
# 需要更多用 data get
```

**过滤字段:**
- `ws_app.ws_app_key` — 应用Key
- `doc_group.app_group_id` — 文档组ID
- `app_created_at` / `app_updated_at` — 时间范围

**运算符:** eq, neq, in, nin, gte, lte

---

### 3.3 数据获取 (无上限)

```bash
# 游标分页获取 (无500硬上限)
emoo data get --max-results 5000

# 带过滤
emoo data get -f '[[{"field":"app_updated_at","operator":"gte","value":"2025-01-01T00:00:00+08:00"}]]'

# 流式输出 JSON Lines (大数据量管道处理)
emoo data get --stream -f '<filter>' | jq '...'
```

---

### 3.4 Base 表操作

**表管理:**
```bash
emoo base table-list                          # 列出所有表
emoo base table-get --table-name "xxx"        # 获取表详情
emoo base table-create -n "表名"              # 创建表
emoo base table-update --table-key "k" --new-table-name "新名"  # 更新表
emoo base table-delete --table-name "xxx"     # 删除表
```

**字段管理:**
```bash
emoo base column-add --table-name "xxx" -n "字段名" -t string
emoo base column-update --table-name "xxx" --column-key "k" --new-column-name "新名"
emoo base column-delete --table-name "xxx" --column-key "k"
# 支持类型: string/number/boolean/date/time/datetime/reference/file/user/group/select
```

**记录操作:**
```bash
# 查询 (最常用)
emoo base record-list --table-name "xxx" --page-size 20
emoo base record-list --table-name "xxx" -f "field:eq:value,field2:gte:2026-06-01"
emoo base record-list --table-name "xxx" -f "content:contains:关键词"   # 模糊搜索
emoo base record-list --table-name "xxx" --room-id "wrYK..."            # 按群过滤
emoo base record-list --table-name "xxx" --max-results 500              # 自动翻页

# 增删改
emoo base record-create --table-name "xxx" -r '[{"字段":"值"}]'
emoo base record-update --table-name "xxx" --record-key "k" -f '{"字段":"新值"}'
emoo base record-batch-update --table-name "xxx" -r '[...]'
emoo base record-delete --table-name "xxx" -k '["key1","key2"]'
```

**字段类型写入格式:**
| 类型 | 写入 | 示例 |
|------|------|------|
| string | 字符串 | `"hello"` |
| number | 数字 | `123.45` |
| boolean | 布尔 | `true` (返回 1/0) |
| date | 字符串 | `"2026-06-15"` |
| time | 字符串 | `"14:30:00"` |
| datetime | 字符串 | `"2026-06-15 14:30:00"` |
| select | **简单值** | `"a"` (⚠️ 不能 `["a"]`) |
| reference | **数组** | `["record_key"]` (⚠️ 必须数组) |
| user | **数字ID** | `123` (⚠️ 不能 open_id) |
| group | **数字ID** | `1` |
| file | URL字符串 | `"https://..."` |

---

### 3.5 其他命令

**工作区切换:**
```bash
emoo auth switch              # 列出
emoo auth switch <name>       # 切换
emoo auth switch --save <name> # 保存
```

**应用管理:**
```bash
emoo app list                           # 列出 (含文档数)
emoo app doc-groups -k <ws_app_key>    # 列出文档组
emoo app overview --max-docs 500        # 生成知识地图
```

**缓存管理:**
```bash
emoo --cache-ttl 600 data search ...   # 自定义TTL
emoo --no-cache data search ...         # 禁用缓存
emoo auth clear-cache                   # 清除缓存
```

**全局选项:**
```bash
emoo --json ...          # JSON输出
emoo --user-id <id> ...  # OAuth2模式
emoo --version           # 版本号
```

---

## 四、真实场景SOP

### 场景1: "帮我查下最近一周发货情况"

```bash
# 第一步: 确认KM新鲜
emoo skill pipeline knowledge-map --auto --ttl 24h  # 缓存命中，秒出

# 第二步: 一行搞定
emoo skill pipeline analyze "近一周发货情况"
# 输出: 16条结果, 2个群, 每日分布, 关键人物, 样本消息
```

### 场景2: "丰凯APP里有没有报销相关的文档"

```bash
# 先查KM找 ws_app_key
# 然后:
emoo data search -k "报销" -f '{"field":"ws_app.ws_app_key","operator":"eq","value":"d282707415ba44b68bd82336c0fcb608"}'
```

### 场景3: "企微存档里张家兴说了什么"

```bash
emoo base record-list --table-name "企微会话存档" \
  -f "from_user:eq:ZhangJiaXing,msgtime:gte:2026-06-01" --max-results 100
```

---

## 五、禁止事项

1. ❌ 不查KM就裸搜 `emoo data search -k "xxx"`
2. ❌ 搜索大时间范围不用analyze管道 (直接搜Base会很慢)
3. ❌ select字段用数组格式 (会报"选项值无效")
4. ❌ reference字段不用数组 (会存空)
5. ❌ user/group字段用open_id或名字 (必须数字ID)
6. ❌ 数据 search 超过500条不用 data get

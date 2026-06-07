---
name: emoo-search-guide
description: EMOO 搜索策略指南 v3 — KM驱动 + AI总结 + 并发加速
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

# EMOO 搜索指南 v3

## 核心原则

**KM 驱动，不要裸搜。** 先用知识图谱了解数据源，再选择对应命令。

---

## 一、初始化 (首次使用)

```bash
emoo auth login --api-key <key>                     # 登录
emoo skill init                                      # 初始化 + 注册 symlink + 安装本指南
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
# 基础用法 — 结构化输出
emoo skill pipeline analyze "近一周话题"

# AI 总结模式 — 拉全量送模型，最准确
emoo skill pipeline analyze "近一个月发货" --summarize

# JSON 输出
emoo --json skill pipeline analyze "近一周话题"
```

### 工作流程

```
用户查询 → AI时间解析 → AI关键词扩展 → KM匹配群
  → 5群并发查询 → 群内并发翻页 → 全量数据
  → (可选)AI总结 → 输出
```

### 支持的时间表达
近一周/近一个月/近3天/今天/昨天/本周/本月/上个季度 (AI模型解析)

### 选项

| 选项 | 说明 |
|------|------|
| `--summarize` | AI 自动总结 (拉全量，无关键词过滤) |
| `--compact` | 精简输出 (仅 time/from/content/group) |
| `--no-probe-filter` | 不过滤测试数据 |
| `--max-results 500` | 最多返回条数 |

---

## 四、文档搜索 `data search`

```bash
# 基本搜索 (务必带 filter)
emoo data search -k "关键词" -f '{"field":"ws_app.ws_app_key","operator":"eq","value":"<km_key>"}'

# 自动翻页 (⚠️ 硬上限500)
emoo data search -k "关键词" --max-results 500

# 过滤字段: ws_app.ws_app_key / doc_group.app_group_id / app_created_at / app_updated_at
# 运算符: eq, neq, in, nin, gte, lte
```

---

## 五、Base 表操作 `base`

```bash
# 表管理
emoo base table-list / table-get / table-create / table-update / table-delete

# 字段管理
emoo base column-add / column-update / column-delete

# 记录查询 (最常用)
emoo base record-list --table-name "xxx" -f "field:eq:value"
emoo base record-list --table-name "xxx" -f "content:contains:关键词"  # 模糊搜索
emoo base record-list --table-name "xxx" --room-id "wrYK..."            # 按群过滤
emoo base record-list --table-name "xxx" --group-field "roomid"         # 指定群字段名
emoo base record-list --table-name "xxx" --max-results 500              # 自动翻页

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
| user/group | 数字ID(`123`) | ❌ 不能 open_id/名字 |
| file | `"https://..."` | |

---

## 六、工作区管理

```bash
emoo auth switch              # 列出可用配置
emoo auth switch <name>       # 切换工作区 (config/skills/KM 全跟随)
emoo auth switch --save <name> # 保存当前配置
emoo auth status              # 查看认证状态
emoo auth set-base-url <url>  # 设置/查看 Base URL
emoo auth clear-cache         # 清除请求缓存
```

---

## 七、缓存

```bash
emoo --cache-ttl 600 ...      # 自定义请求缓存TTL(秒)
emoo --no-cache ...            # 禁用缓存
emoo auth clear-cache          # 清除全部缓存

# KM 缓存 (默认24h)
emoo skill pipeline knowledge-map --auto --ttl 24h  # 智能缓存
emoo skill pipeline knowledge-map --refresh          # 强制刷新
```

---

## 八、性能

| 特性 | 说明 |
|------|------|
| 群间并发 | 5线程同时查询多个群 |
| 群内并发 | 首页后剩余页并发拉取 |
| 速度参考 | 近一周 ~8s, 近一个月 ~15s |

---

## 九、禁止事项

1. ❌ 不查KM就裸搜
2. ❌ 聊天查询用 data search 而不是 analyze
3. ❌ select 用数组 → 报错"选项值无效"
4. ❌ reference 不用数组 → 存空
5. ❌ user/group 用 open_id/名字 → 报错"字段值无效"
6. ❌ data search 超500条不用 data get

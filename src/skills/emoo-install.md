---
name: emoo
description: EMOO CLI 安装与使用全指南 — 群聊分析、文档搜索、Base表操作
type: scenario
category: 系统
tags: [安装, 指南, 初始化, 必装]
emoo:
  search:
    keyword: "{query}"
    page_size: 200
  params:
    query:
      description: 搜索关键词
      required: true
      example: 近一周发货
---

# EMOO CLI 安装与使用全指南

## 安装

```bash
# 从 GitHub 安装
pip install git+https://github.com/allen-emoosearch/emoo-cli.git

# 或克隆后安装
git clone https://github.com/allen-emoosearch/emoo-cli.git
cd emoo-cli && pip install .
```

## 初始化 (首次使用必须按顺序执行)

```bash
# 1. 登录
emoo auth login --api-key <your-api-key>

# 2. 初始化 skills + 注册到 Claude Code
emoo skill init

# 3. 生成知识图谱 (后续搜索的基石，缓存 24h)
emoo skill pipeline knowledge-map --auto --ttl 24h
```

## 搜索策略 (必须按此顺序)

用户提问后，按以下决策树选择命令：

```
┌─ 是聊天/群消息查询？
│    → emoo skill pipeline analyze "<query>" --format md
│      (KM 匹配群 → 并发搜索 → 去重降噪 → Markdown 输出)
│      支持: 近一周/近一个月/今天/昨天/上个季度
│
├─ 是文档/知识库搜索？
│    → emoo data search -k "<keyword>" -f '<filter>'
│      从 KM 获取 ws_app_key 加 filter，不要裸搜
│      硬上限 500 条，超过用 data get
│
├─ 是结构化表格查询？
│    → emoo base record-list --table-name "<name>" -f "..."
│      支持: eq/gte/lte/contains(模糊搜索)
│
└─ 不确定？先检查 KM
     → emoo skill pipeline knowledge-map --auto --ttl 24h
```

## 核心命令

### 聊天分析 (最常用)
```bash
# Markdown 输出 (推荐: AI 工具消费)
emoo skill pipeline analyze "近一周发货" --format md

# JSON 输出 (程序消费，含全量结果)
emoo --json skill pipeline analyze "近一个月发货"

# 文本输出 (人类阅读)
emoo skill pipeline analyze "机器故障"
```

### 文档搜索
```bash
emoo data search -k "关键词" --max-results 500
emoo data search -k "关键词" -f '{"field":"ws_app.ws_app_key","operator":"eq","value":"<key>"}'
# 过滤字段: ws_app.ws_app_key / doc_group.app_group_id / app_created_at / app_updated_at
# 运算符: eq, neq, in, nin, gte, lte
```

### Base 表操作
```bash
# 记录查询 (支持 contains 模糊搜索)
emoo base record-list --table-name "表名" -f "content:contains:关键词"
emoo base record-list --table-name "表名" --room-id "wrYK..."   # 按群过滤
emoo base record-list --table-name "表名" --max-results 500     # 自动翻页

# 表管理
emoo base table-list / table-get / table-create / table-update / table-delete

# 字段管理 (支持 11 种类型: string/number/boolean/date/time/datetime/reference/file/user/group/select)
emoo base column-add / column-update / column-delete

# 记录增删改
emoo base record-create / record-update / record-batch-update / record-delete
```

### 工作区管理
```bash
emoo auth switch              # 列出可用配置
emoo auth switch <name>       # 切换工作区 (skills + KM 自动跟随)
emoo auth switch --save <name> # 保存当前配置
```

## 字段类型写入格式 (重要)

| 类型 | 写入 | ❌ 常见错误 |
|------|------|-------------|
| string/number/date/time/datetime | 直接值 | |
| boolean | `true` / `false` | 返回 1/0 |
| **select** | `"value"` | ❌ `["value"]` 报错 |
| **reference** | `["key"]` | ❌ 不用数组存空 |
| **user** | 数字ID `123` | ❌ open_id 报错 |
| **group** | 数字ID `1` | ❌ 名字/字符串报错 |
| file | URL字符串 | |

## 执行流程 (标准 SOP)

```
1. emoo skill pipeline analyze "<query>" --format md
2. 检查 source_total、matched_total 和结果数
3. 将结果交给 AI 分析和总结
4. AI 负责去重、关联上下文、提取洞察
5. 不使用 CLI 内置总结
```

## 注意事项

1. **KM 优先**: 任何搜索前确保知识图谱缓存有效
2. **Chat → analyze**: 群聊查询必须用 analyze 管道，不用 data search
3. **Doc → data search**: 文档搜索必须带 filter，从 KM 获取 ws_app_key
4. **select ≠ reference**: select 用裸值，reference 用数组，不可互换
5. **user/group**: 必须数字 ID，先 `emoo contact list` 确认
6. **version**: `emoo --version` 检查版本
7. **cache**: `emoo auth clear-cache` 手动清除缓存

# emoo-cli

EMOO 开放平台命令行工具，覆盖鉴权、通讯录、数据搜索、对话、消息推送、EMOO Base 等全部 OpenAPI 接口。

## 安装

```bash
# 方式一：pip 从 GitHub 直接安装
pip install git+https://github.com/allen-emoosearch/emoo-cli.git

# 方式二：克隆后安装
git clone https://github.com/allen-emoosearch/emoo-cli.git
cd emoo-cli
pip install .

# 方式三：开发模式（改源码即时生效）
pip install -e .
```

依赖：Python 3.10+、click、requests、rich。

## 快速开始

```bash
# 方式一：API Key 登录（推荐，无需 --user-id）
emoo auth login --api-key <your-api-key>

# 方式二：OAuth2 登录（需 --user-id）
emoo auth login --client-id <your-client-id> --client-secret <your-client-secret>

# 搜索数据
emoo data search -k "关键词"

# 发送对话
emoo chat send -q "你好"

# 查看认证状态
emoo auth status
```

## 架构：三层命令模型

EMOO CLI 借鉴 Lark CLI 架构，采用三层命令模型 + Agent 原生契约：

```
L3 透传:  emoo api GET/POST/PUT/DELETE /v1/...      一条命令覆盖 100% API
L2 生成:  emoo data search / chat send / ...         结构化命令，与端点 1:1
L1 快捷:  emoo skill run <name> / pipeline           智能默认值、MD 驱动
```

| 层 | 谁写 | 覆盖 | 价值 |
|---|:---:|:---:|------|
| L3 `api` | 自动生成 | 100% API | 无需等待封装，第一天即可用 |
| L2 域命令 | 手写 | 16 端点 | 结构化、参数校验、Rich 表格 |
| L1 skill | 用户 + 手写 | 高频场景 | 智能默认值、CSV 导出、Claude Code 集成 |

### Agent 原生契约

- **stdout 数据，stderr 提示** — `--json` 模式下绝不混合
- **结构化错误** — 每条错误带 `hint` 字段告诉 Agent 怎么修
- **`emoo schema`** — 先查再调，不猜字段
- **`--dry-run`** — 副作用命令可预览不执行

---

### L3 透传: `emoo api`

通用 API 透传命令，覆盖全部 EMOO 端点。使用现有鉴权链，无需单独配置。

```bash
# GET 请求
emoo api GET /v1/apps
emoo api GET "/v1/app/{ws_app_key}/doc-groups?page_size=10"

# POST 请求 (JSON body)
emoo api POST /v1/search -d '{"keyword":"test","page_size":5,"current_page":1}'

# 从文件读取 body
emoo api POST /v1/search -d ./search-body.json

# 从 stdin 读取 body
echo '{"keyword":"test","page_size":5,"current_page":1}' | emoo api POST /v1/search -d -

# Dry-run 预览 (不执行)
emoo api POST /v1/chat/messages -d '{"query":"hi"}' --dry-run

# JSON 输出
emoo --json api GET /v1/apps | jq '.data[].title'
```

### Schema 自省: `emoo schema`

给 Agent "先查再调、不猜字段"的命令。列出所有端点或查看指定端点的参数、请求体、响应、权限。

```bash
# 列出所有端点
emoo schema list

# 查看端点详情
emoo schema data.search          # 参数、Body、响应字段、过滤条件
emoo schema chat.send            # Body 参数、认证要求
emoo schema search               # 模糊匹配（search → data.search）

# JSON 输出
emoo --json schema data.search   # 机器可读，Agent 可编程消费
```

### --dry-run

对有副作用的命令预览请求而不执行：

```bash
emoo chat send -q "你好" --dry-run
emoo message push -t normal -c "通知" --from-title "test" --dry-run
emoo api POST /v1/data/records -d '{"table_name":"t","records":[...]}' --dry-run
```

---

## 认证机制

支持两种认证方式：

### API Key（推荐）

```bash
emoo auth login --api-key emoo_xxx
```

- API Key 直接作为 Bearer Token，无需 Emoo-User-Id
- 适合服务端调用、脚本自动化
- 无过期时间，无需续期

### OAuth2

- **首次登录**：`emoo auth login` 将 client_id/client_secret 保存到 `~/.emoo/config.json`，同时获取 access_token（有效期 2 小时）
- **自动续期**：每次 API 调用前检查 token，过期前 60 秒自动用保存的凭证刷新
- **无效 token 恢复**：如果 token 意外失效，下次调用时自动重新登录
- **无需手动管理**：只要登录过一次，后续所有命令自动携带有效 token

## 全局选项

所有命令都支持以下全局选项，必须放在子命令之前：

| 选项 | 环境变量 | 说明 |
|------|----------|------|
| `--user-id <id>` | `EMOO_USER_ID` | Emoo-User-Id 请求头 (OAuth2 方式必填，API Key 方式无需) |
| `--base-url <url>` | `EMOO_BASE_URL` | API 地址，默认 `https://app.emoosearch.com/open-api/v1` |
| `--json` | — | 输出原始 JSON（默认用 rich 表格美化输出） |

```bash
# 全局选项放在子命令前面
emoo --json data search -k "test"

# OAuth2 方式需要传 --user-id
emoo --user-id open_xxx data search -k "test"

# 或用环境变量
export EMOO_USER_ID=open_xxx
emoo data search -k "test"
```

## 命令详解

### auth — 鉴权管理

#### `emoo auth login`

登录并获取凭证，保存到 `~/.emoo/config.json`。支持 API Key 和 OAuth2 两种方式（二选一）。

| 参数 | 必填 | 环境变量 | 说明 |
|------|:----:|----------|------|
| `--api-key` | 条件 | `EMOO_API_KEY` | API Key（以 `emoo_` 开头），推荐方式 |
| `--client-id` | 条件 | `EMOO_CLIENT_ID` | OAuth2 客户端 ID |
| `--client-secret` | 条件 | `EMOO_CLIENT_SECRET` | OAuth2 客户端密钥（输入时隐藏） |
| `--base-url` | 否 | `EMOO_BASE_URL` | API 地址 |

```bash
# API Key 登录（推荐）
emoo auth login --api-key emoo_xxx

# OAuth2 交互式输入
emoo auth login

# OAuth2 通过参数指定
emoo auth login --client-id xxx --client-secret yyy

# 通过环境变量
EMOO_API_KEY=emoo_xxx emoo auth login
EMOO_CLIENT_ID=xxx EMOO_CLIENT_SECRET=yyy emoo auth login
```

#### `emoo auth status`

查看当前认证状态：认证方式（API Key / OAuth2）、Token 有效期、Base URL、默认 User ID。

```bash
emoo auth status
emoo --json auth status   # JSON 格式输出
```

#### `emoo auth set-default-user-id`

设置默认 Emoo-User-Id (仅 OAuth2 方式需要)，保存到 `~/.emoo/config.json`。

| 参数 | 必填 | 说明 |
|------|:----:|------|
| `USER_ID` (参数) | 是 | 用户的 open_id |

```bash
emoo auth set-default-user-id open_xxx
```

---

### contact — 通讯录管理

#### `emoo contact list`

获取通讯录成员列表（分页）。

| 参数 | 必填 | 默认值 | 说明 |
|------|:----:|--------|------|
| `--page-size` | 否 | 50 | 每页条数（最大 100） |
| `--current-page` | 否 | 1 | 页码 |
| `--keyword` | 否 | — | 搜索关键词，不传则返回全部成员 |

```bash
emoo --user-id <id> contact list
emoo --user-id <id> contact list --page-size 10 --current-page 1
emoo --user-id <id> contact list --keyword "张三"
emoo --user-id <id> contact list --json
```

返回字段：`open_id`、`user_id`、`ws_username`、`ws_user_type`（1=普通成员 2=管理员 3=拥有者）、`email`、`mobile_num`、`ws_group_list` 等。

#### `emoo contact update`

更新成员信息。

| 参数 | 必填 | 说明 |
|------|:----:|------|
| `OPEN_ID` (参数) | 是 | 成员的 open_id |
| `--username` | 否 | 新的工作区显示名称 |
| `--ext-info` | 否 | 扩展信息 JSON 字符串 |

```bash
emoo --user-id <id> contact update open_xxx
emoo --user-id <id> contact update open_xxx --username "新名称"
emoo --user-id <id> contact update open_xxx --ext-info '{"key":"value"}'
```

---

### data — 数据搜索与获取

#### `emoo data search`

搜索企业绑定的所有数据源（不支持个人数据源）。

| 参数 | 必填 | 默认值 | 说明 |
|------|:----:|--------|------|
| `-k, --keyword` | 是 | — | 搜索关键词 |
| `--page-size` | 否 | 20 | 每页条数（最大 200） |
| `--current-page` | 否 | 1 | 页码（从 1 开始） |
| `--text-format` | 否 | plain | `plain` 或 `markdown`（语雀 HTML） |
| `--ws-agent-key` | 否 | — | Dify/Coze/Timus 平台需传入的 Agent Key |
| `-f, --filter` | 否 | — | 过滤条件，JSON 字符串或 JSON 文件路径 |

```bash
# 基本搜索
emoo --user-id <id> data search -k "关键词"

# 分页 + markdown 格式
emoo --user-id <id> data search -k "方案" --page-size 10 --current-page 2 --text-format markdown

# 带过滤条件（外层 OR，内层 AND）
emoo --user-id <id> data search -k "报告" -f '[[{"field":"ws_app.ws_app_key","operator":"eq","value":"abc123"}]]'

# 从文件加载过滤条件
emoo --user-id <id> data search -k "报告" -f ./filter.json

# JSON 输出（方便管道处理）
emoo --user-id <id> data search -k "test" --json | jq '.data.results[].title'
```

返回字段见 [DocDetailInfo 数据模型](#docdetailinfo)。

#### `emoo data get`

游标分页获取文档数据，用法与 search 类似但不传 keyword。

| 参数 | 必填 | 默认值 | 说明 |
|------|:----:|--------|------|
| `--page-size` | 否 | 50 | 每页条数（最大 200） |
| `--cursor` | 否 | "" | 分页游标，空则从头开始 |
| `--text-format` | 否 | plain | `plain` 或 `markdown`（语雀 HTML） |
| `-f, --filter` | 否 | — | 过滤条件 |

```bash
emoo --user-id <id> data get --page-size 10
emoo --user-id <id> data get --page-size 10 -f '[[{"field":"app_updated_at","operator":"gte","value":"2025-01-01T00:00:00+08:00"}]]'
```

---

### chat — 对话管理

#### `emoo chat list`

获取用户对话列表（最多前 50 个）。

| 参数 | 必填 | 默认值 | 说明 |
|------|:----:|--------|------|
| `--page-size` | 否 | 50 | 每页条数 |
| `--current-page` | 否 | 1 | 页码 |

```bash
emoo --user-id <id> chat list
emoo --user-id <id> chat list --page-size 20 --current-page 1
```

返回字段：`id`、`title`、`created_at`、`updated_at`。

#### `emoo chat create`

创建新对话。

| 参数 | 必填 | 说明 |
|------|:----:|------|
| `--title` | 否 | 对话标题 |

```bash
emoo --user-id <id> chat create
emoo --user-id <id> chat create --title "项目讨论"
```

返回：`chat_id`（后续发送消息时需要）。

#### `emoo chat send`

发送对话消息并获取 AI 回复（当前仅支持一次性返回，不支持 SSE 流式）。

| 参数 | 必填 | 说明 |
|------|:----:|------|
| `-q, --query` | 是 | 提问/消息内容 |
| `--chat-id` | 否 | 对话 ID，不传则自动创建新对话 |
| `--file-list` | 否 | 引用文件 URL 列表，逗号分隔（最多 10 个） |
| `--ws-agent-key` | 否 | 指定 Agent 回复（默认使用 EMOO 默认 Agent） |

```bash
# 新对话
emoo --user-id <id> chat send -q "最近一周的销售数据汇总"

# 多轮对话
emoo --user-id <id> chat send -q "什么是EMOO？" --chat-id 5172
emoo --user-id <id> chat send -q "EMOO有哪些核心功能？" --chat-id 5172

# 带文件引用
emoo --user-id <id> chat send -q "总结这些文档" --chat-id 5172 --file-list "https://example.com/doc1,https://example.com/doc2"
```

返回字段：`chat_id`、`message_id`、`complete_response`（AI 回复，可能含 `[xxx]` 引用标记可按需正则去除）。

---

### message — 消息推送

#### `emoo message push`

主动推送消息给指定用户。

| 参数 | 必填 | 说明 |
|------|:----:|------|
| `-t, --type` | 是 | `normal`（普通通知）或 `agent`（Agent 主动推送） |
| `-c, --content` | 是 | 消息内容（最长 300 字符） |
| `-u, --user-id` | 否 | 接收者 Emoo User ID |
| `--from-title` | 条件 | **(normal 必填)** 来源名称 |
| `--from-image-url` | 否 | 来源头像 URL |
| `--detail-link` | 否 | 详情链接 |
| `--agent-key` | 条件 | **(agent 必填)** Agent 的 ws_agent_key |
| `--chat-id` | 否 | 目标对话 ID（不传则自动创建） |

```bash
# 普通通知消息
emoo --user-id <id> message push -t normal -c "审批已通过" --from-title "OA系统"

# 完整普通消息
emoo --user-id <id> message push -t normal -c "审批已通过" \
  --from-title "OA系统" \
  --from-image-url "https://example.com/logo.png" \
  --detail-link "https://example.com/detail/123"

# Agent 主动推送
emoo --user-id <id> message push -t agent -c "您好，这是本周工作总结" \
  --agent-key <ws_agent_key> \
  --chat-id 12345
```

返回字段：`message_id`、`chat_id`（agent 类型一定返回）、`chat_message_id`（agent 类型一定返回）。

---

### base — EMOO Base

对数据表记录进行增删改查操作。所有命令需要 `--table-name` 或 `--table-key` 指定表。

#### `emoo base record-create`

插入记录到数据表（最多 100 条）。

| 参数 | 必填 | 说明 |
|------|:----:|------|
| `--table-name` | 条件 | 表显示名称（与 `--table-key` 二选一） |
| `--table-key` | 条件 | 表系统标识（与 `--table-name` 二选一） |
| `-r, --records` | 是 | 记录 JSON 字符串或 JSON 文件路径（数组，1-100 条） |

```bash
# 用表名创建
emoo base record-create --table-name "线上线索" \
  -r '[{"姓名":"张三","联系方式":"13800138000"}]'

# 用 table_key 创建
emoo base record-create --table-key "lead_table" \
  -r '[{"name":"张三","phone":"13800138000"}]'

# 从文件加载
emoo base record-create --table-name "线上线索" -r ./records.json
```

#### `emoo base record-update`

更新单条记录。

| 参数 | 必填 | 说明 |
|------|:----:|------|
| `--table-name` | 条件 | 表显示名称（与 `--table-key` 二选一） |
| `--table-key` | 条件 | 表系统标识（与 `--table-name` 二选一） |
| `--record-key` | 是 | 记录标识 |
| `-f, --fields` | 是 | 需要更新的字段 JSON 对象或文件路径 |

```bash
emoo base record-update --table-name "线上线索" \
  --record-key "rec_xxx" -f '{"姓名":"李四"}'
```

#### `emoo base record-batch-update`

批量更新记录（最多 100 条）。

| 参数 | 必填 | 说明 |
|------|:----:|------|
| `--table-name` | 条件 | 表显示名称（与 `--table-key` 二选一） |
| `--table-key` | 条件 | 表系统标识（与 `--table-name` 二选一） |
| `-r, --records` | 是 | 记录数组 JSON 或文件路径（每条含 `record_key` 和 `fields`，最多 100 条） |

```bash
emoo base record-batch-update --table-name "线上线索" \
  -r '[{"record_key":"rec_xxx","fields":{"姓名":"李四"}},{"record_key":"rec_yyy","fields":{"姓名":"王五"}}]'
```

#### `emoo base record-delete`

删除记录（最多 100 条）。

| 参数 | 必填 | 说明 |
|------|:----:|------|
| `--table-name` | 条件 | 表显示名称（与 `--table-key` 二选一） |
| `--table-key` | 条件 | 表系统标识（与 `--table-name` 二选一） |
| `-k, --record-keys` | 是 | 记录标识数组 JSON 或文件路径（最多 100 条） |

```bash
emoo base record-delete --table-name "线上线索" \
  -k '["rec_xxx","rec_yyy"]'
```

#### `emoo base record-list`

查询记录列表。

| 参数 | 必填 | 默认值 | 说明 |
|------|:----:|--------|------|
| `--table-name` | 条件 | — | 表显示名称（与 `--table-key` 二选一） |
| `--table-key` | 条件 | — | 表系统标识（与 `--table-name` 二选一） |
| `--page-size` | 否 | 20 | 每页数量（最大 100） |
| `--current-page` | 否 | 1 | 页码 |
| `-f, --filter` | 否 | — | 过滤条件，逗号分隔（如 `status:eq:active,score:gte:60`） |
| `--sort` | 否 | — | 排序（如 `created_at:desc`） |

```bash
# 基本查询
emoo base record-list --table-name "线上线索"

# 带过滤和排序
emoo base record-list --table-name "线上线索" \
  -f "status:eq:active" --sort "created_at:desc"

# 分页
emoo base record-list --table-name "线上线索" --page-size 10 --current-page 2
```

---

### app — 应用与文档组管理

浏览工作区中的所有应用（ws_app_key）和文档组，生成知识地图方便搜索前定位数据源。

#### `emoo app overview`

遍历文档，按 ws_app_key 分组生成 markdown 知识地图，列出每个应用的文档数和示例内容。

| 参数 | 必填 | 默认值 | 说明 |
|------|:----:|--------|------|
| `--max-docs` | 否 | 500 | 扫描文档上限 |
| `-o, --output-file` | 否 | `emoo_knowledge_map.md` | 输出 Markdown 文件路径 |

```bash
# 生成知识地图 (默认扫描 500 篇)
emoo app overview

# 指定扫描上限和输出路径
emoo app overview --max-docs 1000 -o my_knowledge_map.md
```

输出文件包含：快速索引表、各应用详情（ws_app_key、平台、文档数、示例文档）、过滤搜索建议。

#### `emoo app list`

调用 `GET /v1/apps` 接口直接列出所有 ws_app_key，含文档组数和文档数。

```bash
emoo app list
emoo --json app list   # JSON 输出完整 ws_app_key
```

返回字段：`id`、`ws_app_key`、`title`、`doc_group_count`、`doc_count`。

#### `emoo app doc-groups`

调用 `GET /v1/app/{ws_app_key}/doc-groups` 接口列出应用的文档组（分页）。

| 参数 | 必填 | 默认值 | 说明 |
|------|:----:|--------|------|
| `-k, --ws-app-key` | 是 | — | ws_app_key |
| `--page-size` | 否 | 100 | 每页数量（最大 200） |
| `--current-page` | 否 | 1 | 页码 |

```bash
# 列出文档组
emoo app doc-groups -k 9ecb14f83abf469db9d2d49d584b5fbc

# 分页 + JSON
emoo --json app doc-groups -k 9ecb14f83abf469db9d2d49d584b5fbc --page-size 10 --current-page 2
```

返回字段：`app_group_id`、`app_group_name`、`app_group_desc`、`url`、`doc_count`、`created_at`、`updated_at`。

> **ws_agent_key** 需在 EMOO 管理后台 → Agent 管理 → 复制 Agent Key。

---

### skill — MD 驱动的自适应搜索 + Claude Code 集成

**一份 MD，两处运行** — skill 文件既是 Claude Code 能加载的 skill，也是 CLI 能执行的搜索模板。

Skill 文件存放在 `~/.emoo/skills/*.md`，使用 YAML frontmatter 定义搜索参数，Markdown body 作为说明文档。

```
~/.emoo/skills/                   ~/.claude/skills/emoo/  (symlink)
  ├── store-revenue.md               Claude Code 自动加载
  ├── item-analysis.md
  ├── employee-search.md
  ├── policy-search.md
  ├── app-filter.md
  └── time-filter.md
```

#### Skill MD 格式

```markdown
---
name: store-revenue                    # 唯一标识
description: 查询指定门店的营业数据   # 一句话描述
type: scenario                         # scenario(场景) 或 dimension(维度)
category: 门店营收                     # 分类标签
tags: [营收, POS, 门店]
emoo:
  search:
    keyword: "{store} {month} 营业情况"  # 搜索关键词模板，{param} 占位
    app: 天财·POS系统                   # 可选，自动匹配 ws_app_key
    doc_group: 营业情况汇总             # 可选，限定文档组
    page_size: 200                      # 可选，默认 200
  params:
    store:
      description: 门店名称（如 示例门店）
      required: true
      example: 示例门店
    month:
      description: 月份（如 2026-03）
      required: false
      default: "2026-03"
      map_to: time_range               # 自动生成时间过滤条件
  csv_export: true                      # 可选，执行后自动导出 CSV
---

# 门店营收查询

## 使用方式
...
```

#### 初始化 + Claude Code 注册

```bash
# 初始化 skills 目录 + 注册到 Claude Code
emoo skill init

# 创建 symlink: ~/.claude/skills/emoo/ → ~/.emoo/skills/
# 注册后，Claude Code 可自动加载所有 emoo skill
```

#### `emoo skill list`

列出所有已安装的 skill，按分类分组展示。

```bash
emoo skill list
emoo skill list --category "门店营收"     # 按分类过滤
emoo skill list --type dimension          # 按类型过滤 (scenario|dimension)
emoo --json skill list                    # JSON 输出
```

#### `emoo skill show`

显示 skill 的完整 MD 内容和参数说明。

```bash
emoo skill show store-revenue             # 渲染 markdown
emoo skill show store-revenue --params-only  # 仅参数 JSON
```

#### `emoo skill run`

执行 skill 搜索。参数通过 `--param value` 格式传递。

```bash
# 场景类 skill
emoo skill run store-revenue --store "示例门店" --month "2026-03"

# 维度类 skill
emoo skill run app-filter --keyword "营收" --app_name "天财·POS系统"
emoo skill run time-filter --keyword "报告" --time "最近7天"

# 导出 CSV
emoo skill run store-revenue --store "示例门店" --csv output.csv
```

执行流程：模板替换 → app/doc_group 名称解析（知识图谱） → 时间过滤生成 → POST /search → 可选 CSV 导出。

#### `emoo skill create`

脚手架 — 快速创建新 skill MD 文件。

| 参数 | 必填 | 说明 |
|------|:----:|------|
| `NAME` (参数) | 是 | skill 名称（用作文件名和标识） |
| `-d, --description` | 否 | 一句话描述 |
| `-c, --category` | 否 | 分类标签 |
| `--type` | 否 | scenario 或 dimension（默认 scenario） |
| `-k, --keyword` | 否 | 搜索关键词模板 |

```bash
emoo skill create store-revenue -c "门店营收" --keyword "{store} {month}"
emoo skill create app-filter --type dimension -c "搜索维度"
```

#### `emoo skill register`

注册/刷新 Claude Code 集成。默认创建 symlink 让 Claude Code 加载 emoo skills。

```bash
emoo skill register              # 注册
emoo skill register --unregister # 取消注册
```

#### `emoo skill pipeline` — 自适应搜索流水线

三段式智能搜索流水线（子命令组），自动适配不同客户的数据环境。

```
emoo skill pipeline knowledge-map    →  生成增强知识图谱 (JSON + MD)
emoo skill pipeline intent <query>   →  分析意图，输出搜索方案
emoo skill pipeline search -p plan   →  执行搜索方案，聚合结果
```

**pipeline knowledge-map** — 扫描工作区，采样文档标题，生成知识图谱。

```bash
emoo skill pipeline knowledge-map
emoo skill pipeline knowledge-map --max-sample-per-group 10 -o /tmp/km
```

**pipeline intent** — 自然语言意图分析，支持中文时间表达（`3月`、`最近7天`、`上周`等）。

```bash
emoo skill pipeline intent "示例门店店3月营收"
emoo skill pipeline intent "最近7天品项销售" --top 3 -o plan.json
```

**pipeline search** — 执行搜索方案，聚合多 app 结果。

```bash
emoo skill pipeline search -p plan.json
emoo skill pipeline search -p plan.json --csv output.csv
# 管道模式
emoo skill pipeline intent "营收" -o plan.json && emoo skill pipeline search -p plan.json
```

---

## 过滤条件语法

`-f, --filter` 参数支持三种格式，CLI 会自动标准化为二维数组：

```bash
# 格式 1（简写）：单个条件对象，自动包装
-f '{"field":"ws_app.ws_app_key","operator":"eq","value":"abc123"}'

# 格式 2（简写）：条件数组（AND 逻辑），自动包装
-f '[{"field":"ws_app.ws_app_key","operator":"eq","value":"abc123"},{"field":"app_updated_at","operator":"gte","value":"2024-01-01"}]'

# 格式 3（标准）：完整二维数组
-f '[[{"field":"ws_app.ws_app_key","operator":"eq","value":"abc123"}]]'
```

二维数组逻辑：
- **外层数组**：OR 逻辑（满足任意一组即返回）
- **内层数组**：AND 逻辑（需同时满足组内所有条件）

### 过滤字段

| 字段 | 说明 |
|------|------|
| `id` | 文档在 EMOO 中的 ID |
| `app_doc_id` | 文档在源应用中的 ID |
| `doc_group.id` | EMOO 中的文档组 ID |
| `doc_group.app_group_id` | 文档组在源应用中的 ID |
| `app_updated_at` | 文档更新时间 |
| `app_created_at` | 文档创建时间 |
| `ws_app.id` | 应用在 EMOO 中的 ID |
| `ws_app.app_id` | 源应用 ID |
| `ws_app.ws_app_key` | 应用的 Ws App Key |
| `author_ws_app_user_id` | 文档作者的用户 ID |

### 运算符

| 运算符 | 说明 |
|:------:|------|
| `eq` | 等于 |
| `neq` | 不等于 |
| `in` | 属于 |
| `nin` | 不属于 |
| `gte` | 大于等于 |
| `lte` | 小于等于 |

### 示例

```bash
# 单个条件：app_key 为 X
-f '[[{"field":"ws_app.ws_app_key","operator":"eq","value":"abc123"}]]'

# AND 条件：app_key 为 X 且更新时间在 2024 年后
-f '[[{"field":"ws_app.ws_app_key","operator":"eq","value":"abc123"},{"field":"app_updated_at","operator":"gte","value":"2024-01-01T00:00:00+08:00"}]]'

# OR 条件：属于文档组 A 或文档组 B
-f '[[{"field":"doc_group.app_group_id","operator":"eq","value":"group_a"}],[{"field":"doc_group.app_group_id","operator":"eq","value":"group_b"}]]'

# 从文件加载（文件内容同上）
-f ./filter.json
```

---

## 输出格式

| 模式 | 说明 |
|------|------|
| 默认 | Rich 表格美化输出，分页数据自动展示表头和数据行 |
| `--json` | 原始 JSON，适合管道处理：`emoo --json ... \| jq '.data.results'` |

---

## 数据模型

### DocDetailInfo

文档搜索结果中的每条记录。

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | integer | EMOO 中文档 ID |
| `app_doc_id` | string | 源应用中文档 ID |
| `title` | string | 文档标题 |
| `url` | string | 访问链接 |
| `content_type` | string | `text` 或 `json` |
| `content` | string | 文档内容，格式取决于 `text_format` 参数 |
| `app_created_at` | string | 创建时间 |
| `app_updated_at` | string | 更新时间 |
| `ws_app` | WsAppInfo | 所属应用信息 |
| `doc_group` | DocGroupInfo | 所属文档组信息 |

### WsUserDetailInfo

通讯录成员信息。

| 字段 | 类型 | 说明 |
|------|------|------|
| `open_id` | string | 成员唯一标识 |
| `user_id` | integer | 用户系统 ID |
| `ws_user_type` | integer | 1=普通成员 2=管理员 3=工作区拥有者 |
| `ws_username` | string | 用户名 |
| `email` | string | 邮箱 |
| `mobile_num` | string | 手机号 |
| `ws_group_list` | array | 所属角色列表 |

---

## 错误码

### 业务错误码 (HTTP 200 + code 字段)

| 错误码 | 说明 | 处理建议 |
|:------:|------|----------|
| `200` | 成功 | — |
| `4083` | API Token 无效 | 重新执行 `emoo auth login` |
| `4084` | Emoo-User-Id 无效 | 检查 `--user-id` 参数是否正确 |
| `4008` | 应用不存在 | 检查 `ws_app_key` 是否正确 |
| `4042` | 无权限访问该应用 | 确认当前用户有权访问此应用 |
| `4092` | ws_agent_key 不存在 | 检查 Agent Key |
| `4044` | 对话消息不能为空 | 检查 `-q` 参数 |
| `4133` | 表不存在 | 检查 `--table-name` 或 `--table-key` 是否正确 |

### HTTP 状态码

| 状态码 | 说明 |
|:------:|------|
| `400` | 请求参数错误 |
| `401` | 认证失败，检查 API Key 或重新登录 |
| `403` | 无权限访问 |
| `404` | 资源不存在 |
| `500` | 服务器内部错误 |

---

## 环境变量

| 变量 | 说明 |
|------|------|
| `EMOO_API_KEY` | API Key（推荐，设置后无需 `--user-id`） |
| `EMOO_CLIENT_ID` | OAuth2 客户端 ID |
| `EMOO_CLIENT_SECRET` | OAuth2 客户端密钥 |
| `EMOO_USER_ID` | 默认 Emoo-User-Id（OAuth2 方式使用） |
| `EMOO_BASE_URL` | API 地址，默认 `https://app.emoosearch.com/open-api/v1` |

```bash
# API Key 方式
export EMOO_API_KEY=emoo_xxx

# OAuth2 方式
export EMOO_CLIENT_ID=xxx
export EMOO_CLIENT_SECRET=yyy
export EMOO_USER_ID=open_xxx
```

---

## 命令速查

```
emoo auth login [--api-key <key>]          登录 (API Key 推荐 / OAuth2)
emoo auth status                           查看认证状态
emoo auth set-default-user-id <open_id>    设置默认 User ID (OAuth2)

emoo api GET /v1/<path>                    通用 API 透传 (L3, 覆盖 100%)
emoo api POST /v1/<path> -d <json>         通用 POST 透传
emoo schema list                           列出所有 API 端点
emoo schema <endpoint>                     查看端点参数/响应/权限

emoo app list                              列出所有 ws_app_key (含文档组数和文档数)
emoo app doc-groups -k <key>               列出应用的文档组 (分页)
emoo app overview                          遍历文档生成知识地图

emoo skill init                            初始化 + 注册到 Claude Code
emoo skill list                            列出所有 skill
emoo skill show <name>                     显示 skill MD 内容
emoo skill run <name> [--params ...]       执行 skill 搜索
emoo skill create <name>                   创建新 skill (脚手架)
emoo skill register                        注册/取消注册 Claude Code
emoo skill pipeline knowledge-map          生成增强知识图谱
emoo skill pipeline intent "查询意图"      分析意图，输出搜索方案
emoo skill pipeline search -p plan.json    执行搜索方案，聚合多 app 结果

emoo contact list                          获取通讯录成员 (分页+关键词)
emoo contact update <open_id>              更新成员信息 (用户名/扩展信息)

emoo data search -k <keyword>              搜索数据 (分页+过滤+markdown)
emoo data get                              游标分页获取数据

emoo chat list                             对话列表
emoo chat create [--title <title>]         创建新对话
emoo chat send -q <query>                  发送消息并获取 AI 回复

emoo message push -t normal|agent -c ...   主动推送消息

emoo base record-create                    新建记录
emoo base record-update                    更新单条记录
emoo base record-batch-update              批量更新记录
emoo base record-delete                    删除记录
emoo base record-list                      查询记录列表
```

---

## 配置存储

所有配置保存在 `~/.emoo/config.json`：

**API Key 方式**（推荐）：
```json
{
  "api_key": "emoo_xxx",
  "base_url": "https://app.emoosearch.com/open-api/v1"
}
```

**OAuth2 方式**：
```json
{
  "client_id": "xxx",
  "client_secret": "yyy",
  "access_token": "eyJ...",
  "expires_at": 1778785232,
  "base_url": "https://app.emoosearch.com/open-api/v1",
  "default_user_id": "open_xxx"
}
```

- API Key 和 OAuth2 互斥，切换时自动清理另一种方式的凭证
- OAuth2 Token 自动管理，无需手动刷新
- 敏感信息仅存储在本地

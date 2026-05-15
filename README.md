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
# 1. 登录获取 Token（只需一次，Token 自动续期）
emoo auth login --client-id <your-client-id> --client-secret <your-client-secret>

# 2. 搜索数据
emoo --user-id <open_id> data search -k "关键词"

# 3. 发送对话
emoo --user-id <open_id> chat send -q "你好"

# 4. 设置默认用户 ID（避免每次重复输入）
export EMOO_USER_ID=<open_id>
emoo chat list
```

## 认证机制

- **首次登录**：`emoo auth login` 将 client_id/client_secret 保存到 `~/.emoo/config.json`，同时获取 access_token（有效期 2 小时）
- **自动续期**：每次 API 调用前检查 token，过期前 60 秒自动用保存的凭证刷新
- **无效 token 恢复**：如果 token 意外失效，下次调用时自动重新登录
- **无需手动管理**：只要登录过一次，后续所有命令自动携带有效 token

## 全局选项

所有命令都支持以下全局选项，必须放在子命令之前：

| 选项 | 环境变量 | 说明 |
|------|----------|------|
| `--user-id <id>` | `EMOO_USER_ID` | Emoo-User-Id 请求头，标识以哪个用户身份调用 API |
| `--base-url <url>` | `EMOO_BASE_URL` | API 地址，默认 `https://app.emoosearch.com/open-api/v1` |
| `--json` | — | 输出原始 JSON（默认用 rich 表格美化输出） |

```bash
# 全局选项放在子命令前面
emoo --user-id open_xxx --json data search -k "test"

# 或用环境变量
export EMOO_USER_ID=open_xxx
emoo data search -k "test"
```

## 命令详解

### auth — 鉴权管理

#### `emoo auth login`

登录并获取 API Token，凭证保存到 `~/.emoo/config.json`。

| 参数 | 必填 | 环境变量 | 说明 |
|------|:----:|----------|------|
| `--client-id` | 是 | `EMOO_CLIENT_ID` | 客户端 ID |
| `--client-secret` | 是 | `EMOO_CLIENT_SECRET` | 客户端密钥（输入时隐藏） |
| `--base-url` | 否 | `EMOO_BASE_URL` | API 地址 |

```bash
# 交互式输入（会提示输入 client-id 和 client-secret）
emoo auth login

# 通过参数指定
emoo auth login --client-id xxx --client-secret yyy

# 通过环境变量
EMOO_CLIENT_ID=xxx EMOO_CLIENT_SECRET=yyy emoo auth login
```

#### `emoo auth status`

查看当前 Token 状态：Token 预览、剩余有效时间、Base URL、默认 User ID。

```bash
emoo auth status
emoo --json auth status   # JSON 格式输出
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
| `--page-size` | 否 | 20 | 每页条数（最大 100） |
| `--current-page` | 否 | 1 | 页码（从 1 开始） |
| `--text-format` | 否 | plain | `plain` 或 `markdown` |
| `--ws-agent-key` | 否 | — | Dify/Coze/Timus 平台需传入的 Agent Key |
| `-f, --filter` | 否 | — | 过滤条件，JSON 字符串或 JSON 文件路径 |

```bash
# 基本搜索
emoo --user-id <id> data search -k "卡特彼勒"

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
| `--text-format` | 否 | plain | `plain` 或 `markdown` |
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
emoo --user-id <id> chat send -q "轻流是什么产品？"

# 多轮对话
emoo --user-id <id> chat send -q "轻流是什么？" --chat-id 5172
emoo --user-id <id> chat send -q "它的核心功能有哪些？" --chat-id 5172

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

#### `emoo base record-create`

新建数据表记录（开发中）。

| 参数 | 必填 | 说明 |
|------|:----:|------|
| `--table-name` | 条件 | 表显示名称（与 `--table-key` 二选一） |
| `--table-key` | 条件 | 表系统标识（与 `--table-name` 二选一） |
| `-r, --records` | 是 | 记录 JSON 字符串或 JSON 文件路径（数组，1-100 条） |

```bash
# 用表名创建
emoo --user-id <id> base record-create --table-name "线上线索" \
  -r '[{"姓名":"张三","联系方式":"13800138000"}]'

# 用 table_key 创建
emoo --user-id <id> base record-create --table-key "lead_table" \
  -r '[{"name":"张三","phone":"13800138000"}]'

# 从文件加载
emoo --user-id <id> base record-create --table-name "线上线索" -r ./records.json
```

---

## 过滤条件语法

`-f, --filter` 参数使用二维数组：
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
| `ws_app.ws_app_key` | 应用的 Ws App Key |

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

所有接口在 HTTP 200 响应中通过 `code` 字段返回错误码：

| 错误码 | 说明 | 处理建议 |
|:------:|------|----------|
| `200` | 成功 | — |
| `4083` | API Token 无效 | 重新执行 `emoo auth login` |
| `4084` | Emoo-User-Id 无效 | 检查 `--user-id` 参数是否正确 |
| `4092` | ws_agent_key 不存在 | 检查 Agent Key |
| `4044` | 对话消息不能为空 | 检查 `-q` 参数 |

---

## 环境变量

| 变量 | 说明 |
|------|------|
| `EMOO_CLIENT_ID` | 客户端 ID（auth login 时使用） |
| `EMOO_CLIENT_SECRET` | 客户端密钥（auth login 时使用） |
| `EMOO_USER_ID` | 默认 Emoo-User-Id，设置后无需每次传 `--user-id` |
| `EMOO_BASE_URL` | API 地址，默认 `https://app.emoosearch.com/open-api/v1` |

```bash
# 一次性配置所有默认值
export EMOO_USER_ID=open_xxx
export EMOO_CLIENT_ID=xxx
export EMOO_CLIENT_SECRET=yyy
```

---

## 命令速查

```
emoo auth login          登录获取 Token（自动保存+续期）
emoo auth status         查看 Token 状态

emoo contact list        获取通讯录成员（支持分页+关键词）
emoo contact update      更新成员信息（用户名/扩展信息）

emoo data search         搜索数据（关键词+分页+过滤+markdown）
emoo data get            游标分页获取数据

emoo chat list           对话列表
emoo chat create         创建新对话
emoo chat send           发送消息并获取 AI 回复

emoo message push        主动推送消息（普通/Agent）

emoo base record-create  新建数据表记录
```

---

## 配置存储

所有配置保存在 `~/.emoo/config.json`：

```json
{
  "client_id": "xxx",
  "client_secret": "yyy",
  "access_token": "eyJ...",
  "expires_at": 1778785232,
  "base_url": "https://app.emoosearch.com/open-api/v1"
}
```

- Token 自动管理，无需手动刷新
- 敏感信息（client_secret）仅存储在本地

# EMOO 开放平台 API 文档

> **Base URL:** `https://app.emooai.com/open-api/v1`
> **认证方式:** Bearer Token（API Key `emoo_...` 或 OAuth2 `access_token`）
> **文档来源:** https://open.emooai.com
> **机器可读规范:** `docs/openapi.json`
> **生成日期:** 2026-10-17
> **接口总数:** 73 个操作

> 本文由 `python scripts/sync_api_docs.py` 从远端 `llms.txt` 自动生成，请勿手工编辑。

## 快速导航

- [鉴权](#鉴权)（1）
- [应用](#应用)（2）
- [Agent 管理](#Agent-管理)（5）
- [搜索能力](#搜索能力)（3）
- [对话能力](#对话能力)（4）
- [工作项/个人管理](#工作项个人管理)（4）
- [工作项/标签](#工作项标签)（5）
- [工作项/消息推送与回调](#工作项消息推送与回调)（4）
- [个人快捷方式](#个人快捷方式)（5）
- [用户管理](#用户管理)（3）
- [角色管理](#角色管理)（8）
- [知识库/上传文件](#知识库上传文件)（4）
- [知识库/文件管理](#知识库文件管理)（4）
- [知识库/Folder 管理](#知识库Folder-管理)（4）
- [知识库/表管理](#知识库表管理)（5）
- [知识库/列管理](#知识库列管理)（3）
- [知识库/表记录](#知识库表记录)（5）
- [知识库/表权限管理](#知识库表权限管理)（4）

## 通用约定

### 认证

- **API Key（推荐）**：`Authorization: Bearer emoo_xxx`，自动继承绑定用户，无需 `Emoo-User-Id`。
- **OAuth2**：`Authorization: Bearer <access_token>` + `Emoo-User-Id: <open_id>`。
- 例外：`/message`、`/message/batch`、`/message/status`、`/message/status/query`、`/chat/agent-messages` 支持服务间调用，`Emoo-User-Id` 可选。
- 注意：所有错误除认证外通常返回 HTTP 200，调用方必须检查 `body.code == 200`。

### 业务错误码

| code | message | 说明 |
|---|---|---|
| 4006 | workspace_not_found | workspace 不存在或被删除 |
| 4007 | user_not_found | open_id 在工作区中无对应用户 |
| 4008 | ws_app_not_found | ws_app_key 不存在 |
| 4012 | data_not_found | 记录/doc_key/folder 等资源不存在 |
| 4015 | invalid_params | 参数校验失败（具体原因见 data.reason） |
| 4029 | ws_group_name_exists | 角色名重复 |
| 4031 | ws_group_not_found | ws_group_id 不存在 |
| 4034 | file_already_exists | file_key 已 confirm 过 |
| 4035 | file_too_large | 单文件超过大小上限 |
| 4041 | file_not_found | file_key 未确认上传或文件不存在 |
| 4042 | permission_denied | 权限不足 |
| 4044 | chat_message_query_required | query 缺失或为空 |
| 4045 | chat_not_found | chat_id 不属于当前用户/工作区 |
| 4081 | ws_agent_not_found | agent 不属于当前 workspace |
| 4083 | invalid_api_token | API Token 无效，重新登录 |
| 4084 | invalid_open_api_user_id | 缺少/无效 Emoo-User-Id（HTTP 401） |
| 4092 | invalid_open_api_ws_agent_key | ws_agent_key 不存在 |
| 4113 | limit_exceeded | Tag/快捷方式等数量超过上限 |
| 4114 | duplicate_name | Tag 名称重复 |
| 4133 | base_table_not_found | 数据表不存在 |
| 4134 | base_table_name_exists | 同名表已存在 |
| 4138 | base_column_name_exists | 同表内列名重复 |
| 4139 | base_column_limit_exceeded | 列数超过 300 上限 |
| 4140 | base_record_not_found | 记录不存在 |
| 4143 | base_record_title_not_unique | record_title 对应多条记录 |
| 4147 | base_record_filter_invalid | 过滤条件 op 对字段类型不开放 |
| 4154 | rate_limit_exceeded | 限流超配额（data.retry_after） |
| 4205 | base_folder_not_found | folder 不存在 |
| 4206 | base_folder_name_exists | 同 parent 下 folder 重名 |
| 4207 | base_folder_depth_exceeded | folder 超过 10 层 |
| 4208 | base_folder_cycle_detected | folder 移动成环 |
| 4209 | base_role_cross_table_conflict | 权限 role 命中其他表 |
| 4210 | base_open_id_invalid | 指定的 open_id 不存在 |

### 过滤条件

- `/search`、`/data`、`/search/aggregate` 的 `filter_conditions` 是二维数组：外层 OR、内层 AND。
- 运算符：`eq` / `neq` / `in` / `nin` / `gte` / `lte`。
- `/data/records/list` 的 `filters` 是字符串数组：`field:op:value`，op 支持 `eq/neq/in/not_in/gte/lte/is_empty/is_not_empty`。

### 字段类型（Base 写入）

| 类型 | 写入 | 示例 |
|------|------|------|
| string / number / date / time / datetime | 标量 | `"hello"` / `123.45` / `"2026-06-15"` |
| boolean | 布尔 | `true` / `false` |
| select | 简单值 | `"a"`（不能 `["a"]`） |
| reference | 数组 | `["record_key"]` |
| user / group | 数字 ID | `123` / `1` |
| file | URL 字符串 | `"https://..."` |

## API 详情

### 鉴权

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/auth/token` | 获取企业令牌 |

#### `GET /auth/token`

获取 API 访问令牌，默认有效期 2 小时（7200 秒）

**认证:** 无需认证

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| grant_type | string | 否 | 固定为这个值，默认也是这个值 |
| client_id | string | 是 |  |
| client_secret | string | 是 |  |

**响应字段**

- `data.access_token`: string
- `data.token_type`: string — 目前仅会返回Bearer
- `data.expires_in`: integer — 默认有效时间为2小时，即7200秒

```bash
emoo api GET /v1/auth/token
```

### 应用

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/app/{ws_app_key}/doc-groups` | 获取应用的文档组列表 |
| `GET` | `/apps` | 获取工作空间的应用列表 |

#### `GET /app/{ws_app_key}/doc-groups`

列出指定应用的文档组（分页）

**认证:** Bearer Token + Emoo-User-Id

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| ws_app_key | string | 是 |  |

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| page_size | string | 否 |  |
| current_page | string | 否 |  |

```bash
emoo api GET /v1/app/{ws_app_key}/doc-groups
```

#### `GET /apps`

列出工作区所有应用

**认证:** Bearer Token + Emoo-User-Id

**响应字段**

- `data[]`: id, ws_app_key, title, doc_group_count, doc_count

```bash
emoo api GET /v1/apps
```

### Agent 管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/agents` | 获取 agent 列表 |
| `POST` | `/agents` | 创建 agent |
| `DELETE` | `/agents/{ws_agent_key}` | 删除 agent |
| `GET` | `/agents/{ws_agent_key}` | 获取 agent 详情 |
| `PATCH` | `/agents/{ws_agent_key}` | 部分更新 agent |

#### `GET /agents`

获取当前 workspace 下的 agent 列表（分页），可按 agent_type 过滤

**认证:** Bearer Token + Emoo-User-Id

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| page_size | integer | 否 | 最小: 1 |
| current_page | integer | 否 | 最小: 1 |
| agent_type | string | 否 | 集成类型 可选值: webhook, dify, coze, timus |

**响应字段**

- `data.total`: integer
- `data.page_size`: integer
- `data.current_page`: integer
- `data.total_pages`: integer
- `data.results`: array[object]
- `data.results[].ws_agent_key`: string — agent 唯一标识
- `data.results[].title`: string — agent 显示名称
- `data.results[].agent_type`: string — 集成类型 可选值: webhook, dify, coze, timus
- `data.results[].is_enabled`: boolean — 是否启用
- `data.results[].description`: string — agent 描述
- `data.results[].scope`: string — 可见范围：public=全员可用（默认），specified_ws_groups=指定角色可用 可选值: public, specified_ws_groups
- `data.results[].specified_ws_group_ids`: array[integer] — scope=specified_ws_groups 时为角色 id 列表；scope=public 时为空数组
- `data.results[].data_auth`: string — 数据源权限模式：all=全部数据（默认），include_specified_data=仅指定数据，exclude_specified_data=排除指定数据 可选值: all, include_specified_data, exclude_specified_data
- `data.results[].created_at`: string
- `data.results[].updated_at`: string

```bash
emoo api GET /v1/agents
```

#### `POST /agents`

创建 agent。支持 4 种集成类型 (webhook/dify/coze/timus)，config 按类型有不同结构

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| title | string | 是 | agent 显示名称 最长: 100 |
| agent_type | string | 是 | 集成类型 可选值: webhook, dify, coze, timus |
| config | object | 是 | 集成配置，按 agent_type 不同有不同结构（见 WebhookConfig / DifyConfig / CozeConfig / TimusConfig） |
| is_enabled | boolean | 否 | 是否启用，默认 true |
| description | string | 否 | agent 描述（可空字符串或 null） |
| scope | string | 否 | 可见范围：public=全员可用（默认），specified_ws_groups=指定角色可用 可选值: public, specified_ws_groups |
| specified_ws_group_ids | array[integer] | 否 | scope=specified_ws_groups 时必填且 minItems=1；scope=public 时可不传或空数组。角色 id 可通过 GET /ws-groups 获取 |
| data_auth | string | 否 | 数据源权限模式：all=全部数据（默认），include_specified_data=仅指定数据，exclude_specified_data=排除指定数据 可选值: all, include_specified_data, exclude_specified_data |
| data_auth_config | object | 否 | 指定数据范围；data_auth 非 all 时必填（三个列表至少一个非空）。doc_group_ids 可通过 GET /app/{ws_app_key}/doc-groups 获取；doc_ids 可通过搜索结果获取 |

**响应字段**

- `data.ws_agent_key`: string — agent 唯一标识
- `data.title`: string — agent 显示名称
- `data.agent_type`: string — 集成类型 可选值: webhook, dify, coze, timus
- `data.is_enabled`: boolean — 是否启用
- `data.description`: string — agent 描述
- `data.scope`: string — 可见范围：public=全员可用（默认），specified_ws_groups=指定角色可用 可选值: public, specified_ws_groups
- `data.specified_ws_group_ids`: array[integer] — scope=specified_ws_groups 时为角色 id 列表；scope=public 时为空数组
- `data.data_auth`: string — 数据源权限模式：all=全部数据（默认），include_specified_data=仅指定数据，exclude_specified_data=排除指定数据 可选值: all, include_specified_data, exclude_specified_data
- `data.data_auth_config`: object — 指定数据范围；data_auth 非 all 时必填（三个列表至少一个非空）。doc_group_ids 可通过 GET /app/{ws_app_key}/doc-groups 获取；doc_ids 可通过搜索结果获取
- `data.created_at`: string
- `data.updated_at`: string

```bash
emoo api POST /v1/agents
```

#### `DELETE /agents/{ws_agent_key}`

删除 agent

**认证:** Bearer Token + Emoo-User-Id

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| ws_agent_key | string | 是 |  |

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| ws_agent_key | string | 是 | Agent 唯一标识 |

```bash
emoo api DELETE /v1/agents/{ws_agent_key}
```

#### `GET /agents/{ws_agent_key}`

获取 agent 详情 — 获取指定 agent 的详情

**认证:** Bearer Token + Emoo-User-Id

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| ws_agent_key | string | 是 |  |

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| ws_agent_key | string | 是 | Agent 唯一标识 |

**响应字段**

- `data.ws_agent_key`: string — agent 唯一标识
- `data.title`: string — agent 显示名称
- `data.agent_type`: string — 集成类型 可选值: webhook, dify, coze, timus
- `data.is_enabled`: boolean — 是否启用
- `data.description`: string — agent 描述
- `data.scope`: string — 可见范围：public=全员可用（默认），specified_ws_groups=指定角色可用 可选值: public, specified_ws_groups
- `data.specified_ws_group_ids`: array[integer] — scope=specified_ws_groups 时为角色 id 列表；scope=public 时为空数组
- `data.data_auth`: string — 数据源权限模式：all=全部数据（默认），include_specified_data=仅指定数据，exclude_specified_data=排除指定数据 可选值: all, include_specified_data, exclude_specified_data
- `data.data_auth_config`: object — 指定数据范围；data_auth 非 all 时必填（三个列表至少一个非空）。doc_group_ids 可通过 GET /app/{ws_app_key}/doc-groups 获取；doc_ids 可通过搜索结果获取
- `data.created_at`: string
- `data.updated_at`: string

```bash
emoo api GET /v1/agents/{ws_agent_key}
```

#### `PATCH /agents/{ws_agent_key}`

部分更新 agent 配置。agent_type 不可修改

**认证:** Bearer Token + Emoo-User-Id

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| ws_agent_key | string | 是 |  |

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| ws_agent_key | string | 是 | Agent 唯一标识 |

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| title | string | 否 | 最长: 100 |
| description | string | 否 |  |
| is_enabled | boolean | 否 |  |
| config | object | 否 | 新集成配置（按原 agent_type 校验，不可通过 config 改类型） |
| scope | string | 否 | 可见范围：public=全员可用（默认），specified_ws_groups=指定角色可用 可选值: public, specified_ws_groups |
| specified_ws_group_ids | array[integer] | 否 | scope=specified_ws_groups 时必填且 minItems=1；scope=public 时可不传或空数组 |
| data_auth | string | 否 | 数据源权限模式：all=全部数据（默认），include_specified_data=仅指定数据，exclude_specified_data=排除指定数据 可选值: all, include_specified_data, exclude_specified_data |
| data_auth_config | object | 否 | 指定数据范围；data_auth 非 all 时必填（三个列表至少一个非空）。doc_group_ids 可通过 GET /app/{ws_app_key}/doc-groups 获取；doc_ids 可通过搜索结果获取 |

**响应字段**

- `data.ws_agent_key`: string — agent 唯一标识
- `data.title`: string — agent 显示名称
- `data.agent_type`: string — 集成类型 可选值: webhook, dify, coze, timus
- `data.is_enabled`: boolean — 是否启用
- `data.description`: string — agent 描述
- `data.scope`: string — 可见范围：public=全员可用（默认），specified_ws_groups=指定角色可用 可选值: public, specified_ws_groups
- `data.specified_ws_group_ids`: array[integer] — scope=specified_ws_groups 时为角色 id 列表；scope=public 时为空数组
- `data.data_auth`: string — 数据源权限模式：all=全部数据（默认），include_specified_data=仅指定数据，exclude_specified_data=排除指定数据 可选值: all, include_specified_data, exclude_specified_data
- `data.data_auth_config`: object — 指定数据范围；data_auth 非 all 时必填（三个列表至少一个非空）。doc_group_ids 可通过 GET /app/{ws_app_key}/doc-groups 获取；doc_ids 可通过搜索结果获取
- `data.created_at`: string
- `data.updated_at`: string

```bash
emoo api PATCH /v1/agents/{ws_agent_key}
```

### 搜索能力

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/data` | 游标分页批量拉取文档 |
| `POST` | `/search` | 搜索文档 |
| `POST` | `/search/aggregate` | 聚合统计 |

#### `POST /data`

游标分页获取文档数据

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| cursor | string | 否 | 游标，首次请求不传 |
| page_size | integer | 否 | 每页数量，默认 50；超过 200 自动 clamp 到 200 |
| text_format | string | 否 | 可选值: plain, markdown |
| filter_conditions | array[array] | 否 | 过滤条件二维数组（外层 OR、内层 AND） |

**响应字段**

- `data.page_size`: integer
- `data.has_more`: boolean — 是否还有更多数据
- `data.next_cursor`: string — 下一页游标，无更多数据时为 null
- `data.results`: array[object]
- `data.results[].id`: integer — 文档 ID
- `data.results[].app_doc_id`: string — 应用侧文档 ID
- `data.results[].title`: string — 文档标题
- `data.results[].url`: string — 文档链接
- `data.results[].app_created_at`: string — 应用侧创建时间
- `data.results[].app_updated_at`: string — 应用侧更新时间
- `data.results[].content_type`: string — 内容类型 可选值: text, json
- `data.results[].content`: string — 文档内容；text_format=plain 时去除 HTML 标签
- `data.results[].doc_group`: object — 文档分组信息
- `data.results[].ws_app`: object — 文档所属应用信息

```bash
emoo api POST /v1/data
```

#### `POST /search`

搜索企业绑定的所有数据源（不支持个人数据源）

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| keyword | string | 否 | 搜索关键词（建议必填） |
| ws_agent_key | string | 否 | Agent 标识，限定搜索范围 |
| current_page | integer | 否 | 页码，默认 1（代码不强制 minimum） |
| page_size | integer | 否 | 每页数量，默认 50；超过 200 自动 clamp 到 200（代码不强制 minimum） |
| text_format | string | 否 | 文本格式，默认 plain 可选值: plain, markdown |
| filter_conditions | array[array] | 否 | 过滤条件二维数组（外层 OR、内层 AND） |

**响应字段**

- `data.total`: integer
- `data.page_size`: integer
- `data.current_page`: integer
- `data.total_pages`: integer
- `data.results`: array[object]
- `data.results[].id`: integer — 文档 ID
- `data.results[].app_doc_id`: string — 应用侧文档 ID
- `data.results[].title`: string — 文档标题
- `data.results[].url`: string — 文档链接
- `data.results[].app_created_at`: string — 应用侧创建时间
- `data.results[].app_updated_at`: string — 应用侧更新时间
- `data.results[].content_type`: string — 内容类型 可选值: text, json
- `data.results[].content`: string — 文档内容；text_format=plain 时去除 HTML 标签
- `data.results[].doc_group`: object — 文档分组信息
- `data.results[].ws_app`: object — 文档所属应用信息

**可过滤字段:** id, app_doc_id, doc_group.id, doc_group.app_group_id, app_updated_at, app_created_at, ws_app.ws_app_key

**过滤运算符:** eq, neq, in, nin, gte, lte

```bash
emoo api POST /v1/search
```

#### `POST /search/aggregate`

聚合统计 — 在用户可见文档范围内做 metric + group_by 聚合（与 /search 同源 filter + permission）

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| metric_type | string | 是 | 聚合操作：count 走文档数；sum/avg/min/max 走数值/日期字段；values 返回字段值枚举 可选值: count, sum, avg, min, max, values |
| metric_field | string | 否 | 聚合字段名（count 时可省）；type=table 字段建议用通配路径如 '支付信息.*.金额' |
| group_by_field | string | 否 | 分组字段名，不传时返回单桶 total；类型自动探测，date 字段会启用 date_histogram |
| group_by_interval | string | 否 | 时间分桶粒度（仅 group_by_field 是 date 类型时生效，其他类型静默忽略） 可选值: day, week, month, quarter, year |
| max_groups | integer | 否 | group_by 桶上限（hard cap 50） |
| max_values | integer | 否 | metric=values 时返回值上限（hard cap 200） |
| ws_agent_key | string | 否 | Agent 标识，限定聚合范围 |
| filter_conditions | array[array] | 否 | 过滤条件二维数组（外层 OR、内层 AND），同 /search |

**响应字段**

- `data.total_docs`: integer — 匹配过滤条件的文档总数（含权限过滤后）
- `data.metric_type`: string — 可选值: count, sum, avg, min, max, values
- `data.metric_field`: string
- `data.buckets`: array[object]
- `data.truncated`: boolean — 是否触达 max_groups / max_values 上限
- `data.note`: string — 空结果时的引导提示（建议调 describe_doc_group 确认字段名）

```bash
emoo api POST /v1/search/aggregate
```

### 对话能力

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/chat` | 获取对话列表 |
| `POST` | `/chat` | 创建对话 |
| `POST` | `/chat/agent-messages` | Agent 主动推送消息 |
| `POST` | `/chat/messages` | 发送对话消息 |

#### `GET /chat`

获取用户对话列表（最多前 50 个）

**认证:** Bearer Token + Emoo-User-Id

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| current_page | integer | 否 | 页码，默认 1 |
| page_size | integer | 否 | 每页数量，默认 50 |

**响应字段**

- `data.total`: integer
- `data.page_size`: integer
- `data.current_page`: integer
- `data.total_pages`: integer
- `data.results`: array[object]
- `data.results[].id`: integer — 对话 ID
- `data.results[].title`: string — 对话标题
- `data.results[].created_at`: string
- `data.results[].updated_at`: string

```bash
emoo api GET /v1/chat
```

#### `POST /chat`

创建新对话

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| title | string | 否 | 对话标题（可选） |

**响应字段**

- `data.chat_id`: integer

```bash
emoo api POST /v1/chat
```

#### `POST /chat/agent-messages`

Agent 主动推送消息 — Agent 身份的服务间调用，向自己归属的会话追加 assistant 消息（审批执行结果、长任务进度、主动通知）

**认证:** Bearer Token

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| chat_id | integer | 是 | 目标会话 ID（必填，必须是当前 agent 归属的会话） |
| content | string | 是 | 消息内容（必填，不能为空白）；v1 仅 markdown 文本，不能发审批卡 |

**响应字段**

- `data.chat_id`: integer — 会话 ID
- `data.chat_message_id`: integer — 落库后的消息 ID

```bash
emoo api POST /v1/chat/agent-messages
```

#### `POST /chat/messages`

发送对话消息并返回 AI 回答（API 支持 stream=true SSE；CLI 目前一次性返回）

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| chat_id | integer | 否 | 对话 ID；不传则创建新对话 |
| query | string | 是 | 用户问题（必填，不能为空） |
| file_list | array[string] | 否 | 关联文件 file_key 列表，最多 10 个 最多: 10 项 |
| ws_agent_key | string | 否 | Agent 标识 |
| stream | boolean | 否 | 是否流式返回（默认 false） |

**响应字段**

- `data.chat_id`: integer
- `data.complete_response`: string — AI 完整回答（已替换文档引用为标题）
- `data.message_id`: integer — 本次消息 ID

```bash
emoo api POST /v1/chat/messages
```

### 工作项/个人管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/work_item` | 工作项列表 |
| `POST` | `/work_item` | 创建工作项 |
| `DELETE` | `/work_item/{item_id}` | 删除工作项 |
| `PUT` | `/work_item/{item_id}` | 更新工作项 |

#### `GET /work_item`

工作项列表 — 分页查询当前用户的统一工作项（含自建与外部推送项），支持按 Tag、状态、无 Tag 过滤

**认证:** Bearer Token + Emoo-User-Id

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| page_size | integer | 否 | 默认 50，超过 500 按 500 处理 最小: 1 |
| current_page | integer | 否 | 最小: 1 |
| scope | string | 否 | pending=待处理主列表（默认）；done=已完成折叠区 可选值: pending, done |
| tag_id | integer | 否 | 正整数=按 Tag 过滤；不传或 0=不过滤 最小: 0 |
| not_taged | boolean | 否 | true=仅查无 Tag 项；与正整数 tag_id 互斥（同传返回 400） |

**响应字段**

- `data.total`: integer
- `data.page_size`: integer
- `data.current_page`: integer
- `data.total_pages`: integer
- `data.results`: array[object]
- `data.results[].id`: integer — 工作项 id
- `data.results[].source`: string — 来源：self=用户自建（内容层可编辑）；push=外部系统/Agent 推送（内容层只读，归推送方） 可选值: self, push
- `data.results[].content`: string — 内容（推送项为原文截断/去 Markdown 后的前 500 字）
- `data.results[].from_title`: string — 推送项的来源标题（self 项为 null）
- `data.results[].from_image_url`: string — 推送项的来源图片 URL，缺省取 workspace 默认 logo（self 项为 null）
- `data.results[].detail_link`: string — 推送项的详情链接（self 项为 null）
- `data.results[].thread_key`: string — 推送方业务单据 id（如审批单号）；同 (workspace, user, thread_key) 只保留一条，`POST /message/status` 按它核销/复活（self 项为 null）
- `data.results[].due_at`: string — 截止时间
- `data.results[].remind_at`: string — 稍后提醒时间
- `data.results[].status`: string — 状态：pending=待处理；done=已完成（推送项勾选完成=清出我的列表，不回写源系统） 可选值: pending, done
- `data.results[].done_at`: string — 完成时间（未完成为 null）
- `data.results[].has_read`: boolean — 是否已读（推送项初始未读，自建项恒为已读）
- `data.results[].tag_id`: integer — 关联 Tag id（无 Tag 时为 null）
- `data.results[].tag_info`: object — 工作项 Tag
- `data.results[].ws_agent_key`: string — Agent 推送项关联的 Agent 标识（非 agent 推送为 null）
- `data.results[].chat_id`: integer — Agent 推送项关联的对话 id（非 agent 推送为 null）
- `data.results[].chat_message_id`: integer — Agent 推送项关联的对话消息 id（非 agent 推送为 null）
- `data.results[].created_at`: string
- `data.results[].updated_at`: string

```bash
emoo api GET /v1/work_item
```

#### `POST /work_item`

创建工作项 — 创建一条自建（source=self）工作项，默认待处理、已读

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| content | string | 是 | 工作项内容（仅可创建 self 来源） 最长: 500 |
| due_at | string | 否 | 截止时间，可选 |
| tag_id | integer | 否 | 关联 Tag id；不传或传 0/null 表示不关联。Tag 必须属于当前用户，否则 4012 最小: 0 |

**响应字段**

- `data.id`: integer — 工作项 id
- `data.source`: string — 来源：self=用户自建（内容层可编辑）；push=外部系统/Agent 推送（内容层只读，归推送方） 可选值: self, push
- `data.content`: string — 内容（推送项为原文截断/去 Markdown 后的前 500 字）
- `data.from_title`: string — 推送项的来源标题（self 项为 null）
- `data.from_image_url`: string — 推送项的来源图片 URL，缺省取 workspace 默认 logo（self 项为 null）
- `data.detail_link`: string — 推送项的详情链接（self 项为 null）
- `data.thread_key`: string — 推送方业务单据 id（如审批单号）；同 (workspace, user, thread_key) 只保留一条，`POST /message/status` 按它核销/复活（self 项为 null）
- `data.due_at`: string — 截止时间
- `data.remind_at`: string — 稍后提醒时间
- `data.status`: string — 状态：pending=待处理；done=已完成（推送项勾选完成=清出我的列表，不回写源系统） 可选值: pending, done
- `data.done_at`: string — 完成时间（未完成为 null）
- `data.has_read`: boolean — 是否已读（推送项初始未读，自建项恒为已读）
- `data.tag_id`: integer — 关联 Tag id（无 Tag 时为 null）
- `data.tag_info`: object — 工作项 Tag
- `data.ws_agent_key`: string — Agent 推送项关联的 Agent 标识（非 agent 推送为 null）
- `data.chat_id`: integer — Agent 推送项关联的对话 id（非 agent 推送为 null）
- `data.chat_message_id`: integer — Agent 推送项关联的对话消息 id（非 agent 推送为 null）
- `data.created_at`: string
- `data.updated_at`: string

```bash
emoo api POST /v1/work_item
```

#### `DELETE /work_item/{item_id}`

删除工作项 — 删除指定工作项

**认证:** Bearer Token + Emoo-User-Id

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| item_id | string | 是 |  |

**响应字段**

- `data.item_id`: integer

```bash
emoo api DELETE /v1/work_item/{item_id}
```

#### `PUT /work_item/{item_id}`

更新工作项 — 部分更新工作项

**认证:** Bearer Token + Emoo-User-Id

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| item_id | string | 是 |  |

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| content | string | 否 | 仅 self 来源可改 最长: 500 |
| due_at | string | 否 | 仅 self 来源可改。不传不修改；传 null 清空；传值更新 |
| tag_id | integer | 否 | 不传或传 null=不修改；传 0=清空 Tag；传正整数=设置 Tag（Tag 必须属于当前用户） 最小: 0 |
| status | string | 否 | 状态切换。pending→done 记录完成时间；done→pending 恢复待处理。推送项标记 done=清出我的列表，不回写源系统 可选值: pending, done |
| remind_at | string | 否 | 稍后提醒时间。不传不修改；传 null 清空；传值更新 |

**响应字段**

- `data.id`: integer — 工作项 id
- `data.source`: string — 来源：self=用户自建（内容层可编辑）；push=外部系统/Agent 推送（内容层只读，归推送方） 可选值: self, push
- `data.content`: string — 内容（推送项为原文截断/去 Markdown 后的前 500 字）
- `data.from_title`: string — 推送项的来源标题（self 项为 null）
- `data.from_image_url`: string — 推送项的来源图片 URL，缺省取 workspace 默认 logo（self 项为 null）
- `data.detail_link`: string — 推送项的详情链接（self 项为 null）
- `data.thread_key`: string — 推送方业务单据 id（如审批单号）；同 (workspace, user, thread_key) 只保留一条，`POST /message/status` 按它核销/复活（self 项为 null）
- `data.due_at`: string — 截止时间
- `data.remind_at`: string — 稍后提醒时间
- `data.status`: string — 状态：pending=待处理；done=已完成（推送项勾选完成=清出我的列表，不回写源系统） 可选值: pending, done
- `data.done_at`: string — 完成时间（未完成为 null）
- `data.has_read`: boolean — 是否已读（推送项初始未读，自建项恒为已读）
- `data.tag_id`: integer — 关联 Tag id（无 Tag 时为 null）
- `data.tag_info`: object — 工作项 Tag
- `data.ws_agent_key`: string — Agent 推送项关联的 Agent 标识（非 agent 推送为 null）
- `data.chat_id`: integer — Agent 推送项关联的对话 id（非 agent 推送为 null）
- `data.chat_message_id`: integer — Agent 推送项关联的对话消息 id（非 agent 推送为 null）
- `data.created_at`: string
- `data.updated_at`: string

```bash
emoo api PUT /v1/work_item/{item_id}
```

### 工作项/标签

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/work_item/tags` | Tag 列表 |
| `POST` | `/work_item/tags` | 创建 Tag |
| `POST` | `/work_item/tags/order` | 重排 Tag |
| `DELETE` | `/work_item/tags/{tag_id}` | 删除 Tag |
| `PUT` | `/work_item/tags/{tag_id}` | 更新 Tag |

#### `GET /work_item/tags`

Tag 列表 — 获取当前用户的全部 Tag，按 order 升序

**认证:** Bearer Token + Emoo-User-Id

**响应字段**

- `data[].id`: integer — Tag id
- `data[].name`: string — Tag 名称
- `data[].color`: string — Tag 颜色（如 #FFFFFF）
- `data[].order`: integer — 排序值，按 order 升序

```bash
emoo api GET /v1/work_item/tags
```

#### `POST /work_item/tags`

创建 Tag — 创建一个 Tag

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| name | string | 是 | Tag 名称，同一用户下唯一 最长: 50 |
| color | string | 是 | Tag 颜色（如 #FFFFFF） 最长: 30 |

**响应字段**

- `data.id`: integer — Tag id
- `data.name`: string — Tag 名称
- `data.color`: string — Tag 颜色（如 #FFFFFF）
- `data.order`: integer — 排序值，按 order 升序

```bash
emoo api POST /v1/work_item/tags
```

#### `POST /work_item/tags/order`

重排 Tag — 重排 Tag 顺序

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| tag_ids | array[integer] | 是 | 按新顺序排列的全部 tag_id |

**响应字段**

- `data[].id`: integer — Tag id
- `data[].name`: string — Tag 名称
- `data[].color`: string — Tag 颜色（如 #FFFFFF）
- `data[].order`: integer — 排序值，按 order 升序

```bash
emoo api POST /v1/work_item/tags/order
```

#### `DELETE /work_item/tags/{tag_id}`

删除 Tag — 删除指定 Tag

**认证:** Bearer Token + Emoo-User-Id

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| tag_id | string | 是 |  |

**响应字段**

- `data.tag_id`: integer

```bash
emoo api DELETE /v1/work_item/tags/{tag_id}
```

#### `PUT /work_item/tags/{tag_id}`

更新 Tag — 更新 Tag 的名称和颜色（整体覆盖，两个字段都必填）

**认证:** Bearer Token + Emoo-User-Id

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| tag_id | string | 是 |  |

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| name | string | 是 | Tag 名称，同一用户下唯一 最长: 50 |
| color | string | 是 | Tag 颜色（如 #FFFFFF） 最长: 30 |

**响应字段**

- `data.id`: integer — Tag id
- `data.name`: string — Tag 名称
- `data.color`: string — Tag 颜色（如 #FFFFFF）
- `data.order`: integer — 排序值，按 order 升序

```bash
emoo api PUT /v1/work_item/tags/{tag_id}
```

### 工作项/消息推送与回调

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/message` | 推送消息 |
| `POST` | `/message/batch` | 批量推送消息 |
| `POST` | `/message/status` | 批量核销/复活工作项 |
| `POST` | `/message/status/query` | 对账查询 |

#### `POST /message`

推送消息并落工作项（normal/agent；thread_key 幂等，due_at 截止时间）

**认证:** Bearer Token

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| emoo_user_id | string | 否 | 目标用户 open_id；不传时取请求头 Emoo-User-Id |
| message_type | string | 是 | 可选值: normal, agent |
| content | string | 是 | 消息内容（原文截断前 500 字落工作项） |
| thread_key | string | 否 | 推送方业务单据 id（如审批单号）。同一 (workspace, user, thread_key) 只保留一条工作项，再推送刷新内容并浮回；不带则每次推送独立一条。需在工作区内全局唯一，多系统集成建议带系统前缀（如 oa:approval-8821） 最长: 128 |
| due_at | string | 否 | 截止时间，可选；带 thread_key 重推时会覆盖。ISO 8601：带偏移量按绝对时刻解析（`Z`=UTC、`+08:00`=北京时间），建议始终带偏移量；不带则按服务器时区（Asia/Shanghai）解释 |
| normal_message_info | object | 条件 | 普通消息附加信息（message_type=normal 时必填，from_title 必填非空） |
| agent_message_info | object | 条件 | Agent 消息附加信息（message_type=agent 时必填，ws_agent_key 必填非空） |

**响应字段**

- `data.item_id`: integer — 统一工作项 ID（即 WorkItem.id，可用 GET /work_item/{item_id} 查询）
- `data.chat_id`: integer — 对话 ID；normal=null，agent=真实 chat id
- `data.chat_message_id`: integer — chat 内消息 ID；normal=null，agent=真实 chat_message_id

```bash
emoo api POST /v1/message
```

#### `POST /message/batch`

批量推送消息 — 批量推送（fan-out 场景）：`messages` ≤50 条，每条与 `POST /message` 完全同构（含各自的 emoo_user_id / thread_key）

**认证:** Bearer Token

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| messages | array | 是 | 批量推送条目，每条与 POST /message 的 PushMessageRequest 完全同构。逐条校验落库、逐条返回结果，不整体原子（部分失败不影响其他条） 最多: 50 项 |

**响应字段**

- `data.success_count`: integer — 成功条数
- `data.failure_count`: integer — 失败条数（含校验失败与业务失败）
- `data.results`: array[object] — 逐条结果，顺序与请求 messages 一致
- `data.results[].index`: integer — 请求中的下标（从 0 开始）
- `data.results[].code`: integer — 200=成功；400=该条校验失败；其他=该条业务错误码
- `data.results[].message`: string
- `data.results[].data`: object — 成功时为工作项落库结果；失败时为错误详情（如 data.reason 或字段校验错误）

```bash
emoo api POST /v1/message/batch
```

#### `POST /message/status`

批量核销/复活工作项 — 源系统回调：按 `thread_keys`（≤100，去重保序，逐 key 独立）批量核销/复活工作项，幂等（重复调用安全，只更新需要变更的条目）

**认证:** Bearer Token

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| thread_keys | array[string] | 是 | 推送时携带的业务单据 id 列表（去重保序，逐 key 独立处理），按 (workspace, thread_key) 匹配该工作区下所有用户的条目 最多: 100 项 |
| status | string | 是 | resolved=源系统已办结，自动核销（标记 done）；reopened=源系统撤回/重开，回到待处理并重置未读 可选值: resolved, reopened |

**响应字段**

- `data.results`: array[object] — 逐 key 结果（去重保序）
- `data.results[].thread_key`: string — 回执的业务单据 id
- `data.results[].status`: string — 核销/复活后的目标状态：resolved→done，reopened→pending 可选值: pending, done
- `data.results[].updated_count`: integer — 该 key 本次实际变更的条目数（幂等：重复调用或无需变更时为 0）

```bash
emoo api POST /v1/message/status
```

#### `POST /message/status/query`

对账查询 — 按 `thread_keys`（≤100，去重保序）返回各收件人的工作项状态

**认证:** Bearer Token

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| thread_keys | array[string] | 是 | 业务单据 id 列表（去重保序）。按 (workspace, thread_key) 查询该工作区下所有用户的条目 最多: 100 项 |

**响应字段**

- `data.results`: array[object] — 按请求顺序返回全部请求 key；从未推送过（或无条目）的 key 返回空 items
- `data.results[].thread_key`: string
- `data.results[].items`: array[object] — 该 key 下各收件人的条目（条目数 = 当初推送的 fan-out 人数，不分页）

```bash
emoo api POST /v1/message/status/query
```

### 个人快捷方式

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/shortcut` | 快捷方式列表 |
| `POST` | `/shortcut` | 创建快捷方式 |
| `POST` | `/shortcut/order` | 重排快捷方式 |
| `DELETE` | `/shortcut/{shortcut_id}` | 删除快捷方式 |
| `PUT` | `/shortcut/{shortcut_id}` | 更新快捷方式 |

#### `GET /shortcut`

快捷方式列表 — 获取当前用户的全部快捷方式，按 order,id 升序

**认证:** Bearer Token + Emoo-User-Id

**响应字段**

- `data[].id`: integer — 快捷方式 id
- `data[].title`: string — 标题
- `data[].url`: string — 跳转链接（仅约束长度，不校验 URL 格式，兼容自定义协议）
- `data[].order`: integer — 排序值，按 order 升序

```bash
emoo api GET /v1/shortcut
```

#### `POST /shortcut`

创建快捷方式 — 创建一条快捷方式，追加到列表末尾

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| title | string | 是 | 标题 最长: 200 |
| url | string | 是 | 跳转链接 最长: 500 |

**响应字段**

- `data.id`: integer — 快捷方式 id
- `data.title`: string — 标题
- `data.url`: string — 跳转链接（仅约束长度，不校验 URL 格式，兼容自定义协议）
- `data.order`: integer — 排序值，按 order 升序

```bash
emoo api POST /v1/shortcut
```

#### `POST /shortcut/order`

重排快捷方式 — 重排快捷方式顺序

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| shortcut_ids | array[integer] | 是 | 按新顺序排列的全部 shortcut_id；无快捷方式时可为空数组 |

**响应字段**

- `data[].id`: integer — 快捷方式 id
- `data[].title`: string — 标题
- `data[].url`: string — 跳转链接（仅约束长度，不校验 URL 格式，兼容自定义协议）
- `data[].order`: integer — 排序值，按 order 升序

```bash
emoo api POST /v1/shortcut/order
```

#### `DELETE /shortcut/{shortcut_id}`

删除快捷方式 — 删除指定快捷方式

**认证:** Bearer Token + Emoo-User-Id

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| shortcut_id | string | 是 |  |

**响应字段**

- `data.shortcut_id`: integer

```bash
emoo api DELETE /v1/shortcut/{shortcut_id}
```

#### `PUT /shortcut/{shortcut_id}`

更新快捷方式 — 整体覆盖更新标题和链接（两个字段都必填）

**认证:** Bearer Token + Emoo-User-Id

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| shortcut_id | string | 是 |  |

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| title | string | 是 | 标题 最长: 200 |
| url | string | 是 | 跳转链接 最长: 500 |

**响应字段**

- `data.id`: integer — 快捷方式 id
- `data.title`: string — 标题
- `data.url`: string — 跳转链接（仅约束长度，不校验 URL 格式，兼容自定义协议）
- `data.order`: integer — 排序值，按 order 升序

```bash
emoo api PUT /v1/shortcut/{shortcut_id}
```

### 用户管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/ws-user` | 获取工作区用户列表 |
| `PUT` | `/ws-user` | 批量更新用户信息 |
| `POST` | `/ws-user/batch-get` | 批量按 open_id 查询用户 |

#### `GET /ws-user`

获取通讯录成员列表（分页）

**认证:** Bearer Token + Emoo-User-Id

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| keyword | string | 否 | 搜索关键词 |
| page_size | integer | 否 | 每页数量，默认 50，最大 100 最小: 1 |
| current_page | integer | 否 | 页码，默认 1 最小: 1 |

**响应字段**

- `data.total`: integer
- `data.page_size`: integer
- `data.current_page`: integer
- `data.total_pages`: integer
- `data.results`: array[object]
- `data.results[].open_id`: string — 用户 open_id
- `data.results[].user_id`: integer — 用户 ID
- `data.results[].is_active`: boolean — 是否激活
- `data.results[].workspace_id`: integer — 工作区 ID
- `data.results[].ws_user_type`: integer — 用户角色：1=工作区用户、2=工作区管理员、3=工作区拥有者 可选值: 1, 2, 3
- `data.results[].ws_username`: string — 用户名（缺失时回退到 display_name / username / mobile_num）
- `data.results[].created_at`: string
- `data.results[].updated_at`: string
- `data.results[].ws_group_list`: array[object] — 所属角色列表
- `data.results[].email`: string
- `data.results[].mobile_num`: string
- `data.results[].avatar_url`: string — 头像 URL（7 天有效期签名 URL，无头像为空字符串）
- `data.results[].ext_info`: object — 扩展信息

```bash
emoo api GET /v1/ws-user
```

#### `PUT /ws-user`

更新成员信息

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| open_id | string | 是 | 成员在当前工作区中的唯一标识 |
| ws_username | string | 否 | 工作区中的显示名称 |
| ext_info | object | 否 | 扩展信息（自由格式 key-value） |

**响应字段**

- `data[].open_id`: string — 失败的 open_id
- `data[].ws_username`: string
- `data[].ext_info`: object
- `data[].failed_type`: string — 失败原因枚举：open_id_not_found=该 open_id 在当前 workspace 不存在 可选值: open_id_not_found

```bash
emoo api PUT /v1/ws-user
```

#### `POST /ws-user/batch-get`

批量按 open_id 查询用户 — 一次查询最多 100 个 open_id，返回用户完整信息（结构同列表接口），**按请求顺序**返回

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| open_ids | array[string] | 是 | 要查询的 open_id 列表（1-100 个；重复值自动去重，重复不影响返回） 最多: 100 项 |

**响应字段**

- `data[].open_id`: string — 用户 open_id
- `data[].user_id`: integer — 用户 ID
- `data[].is_active`: boolean — 是否激活
- `data[].workspace_id`: integer — 工作区 ID
- `data[].ws_user_type`: integer — 用户角色：1=工作区用户、2=工作区管理员、3=工作区拥有者 可选值: 1, 2, 3
- `data[].ws_username`: string — 用户名（缺失时回退到 display_name / username / mobile_num）
- `data[].created_at`: string
- `data[].updated_at`: string
- `data[].ws_group_list`: array[object] — 所属角色列表
- `data[].email`: string
- `data[].mobile_num`: string
- `data[].avatar_url`: string — 头像 URL（7 天有效期签名 URL，无头像为空字符串）
- `data[].ext_info`: object — 扩展信息

```bash
emoo api POST /v1/ws-user/batch-get
```

### 角色管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/ws-groups` | 获取角色列表 |
| `POST` | `/ws-groups` | 创建角色 |
| `POST` | `/ws-groups/batch-get` | 批量按 id 查询角色 |
| `DELETE` | `/ws-groups/{ws_group_id}` | 删除角色 |
| `PATCH` | `/ws-groups/{ws_group_id}` | 更新角色 |
| `GET` | `/ws-groups/{ws_group_id}/members` | 查询角色成员列表 |
| `POST` | `/ws-groups/{ws_group_id}/members` | 批量加入成员 |
| `DELETE` | `/ws-groups/{ws_group_id}/members/{open_id}` | 移除单个成员 |

#### `GET /ws-groups`

获取当前 workspace 下的角色列表（分页），支持关键字搜索

**认证:** Bearer Token + Emoo-User-Id

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| keyword | string | 否 | 按 group_name 模糊搜索 |
| page_size | integer | 否 | 最小: 1 |
| current_page | integer | 否 | 最小: 1 |

**响应字段**

- `data.total`: integer
- `data.page_size`: integer
- `data.current_page`: integer
- `data.total_pages`: integer
- `data.results`: array[object]
- `data.results[].id`: integer — ws_group id
- `data.results[].group_name`: string — 角色名称（workspace 内唯一）
- `data.results[].group_desc`: string — 角色描述
- `data.results[].created_at`: string
- `data.results[].avatar_url`: string — 角色头像 URL（7 天有效期签名 URL，无头像为空字符串）

```bash
emoo api GET /v1/ws-groups
```

#### `POST /ws-groups`

创建角色。group_name 在 workspace 内必须唯一

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| group_name | string | 是 | 角色名称（workspace 内唯一） 最长: 100 |
| group_desc | string | 否 | 角色描述（可选） |

**响应字段**

- `data.id`: integer — ws_group id
- `data.group_name`: string — 角色名称（workspace 内唯一）
- `data.group_desc`: string — 角色描述
- `data.created_at`: string
- `data.avatar_url`: string — 角色头像 URL（7 天有效期签名 URL，无头像为空字符串）

```bash
emoo api POST /v1/ws-groups
```

#### `POST /ws-groups/batch-get`

批量按 id 查询角色 — 一次查询最多 100 个 ws_group id，返回角色信息（结构同列表接口），**按请求顺序**返回

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| ws_group_ids | array[integer] | 是 | 要查询的 ws_group id 列表（1-100 个；重复值自动去重） 最多: 100 项 |

**响应字段**

- `data[].id`: integer — ws_group id
- `data[].group_name`: string — 角色名称（workspace 内唯一）
- `data[].group_desc`: string — 角色描述
- `data[].created_at`: string
- `data[].avatar_url`: string — 角色头像 URL（7 天有效期签名 URL，无头像为空字符串）

```bash
emoo api POST /v1/ws-groups/batch-get
```

#### `DELETE /ws-groups/{ws_group_id}`

删除角色。成员关系自动解除

**认证:** Bearer Token + Emoo-User-Id

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| ws_group_id | string | 是 |  |

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | integer | 是 | 角色 ID |

```bash
emoo api DELETE /v1/ws-groups/{ws_group_id}
```

#### `PATCH /ws-groups/{ws_group_id}`

更新角色基础信息（不影响成员关系）

**认证:** Bearer Token + Emoo-User-Id

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| ws_group_id | string | 是 |  |

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | integer | 是 | 角色 ID |

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| group_name | string | 否 | 新角色名（workspace 内唯一） 最长: 100 |
| group_desc | string | 否 | 新描述；传 null=清空（转空串） |

**响应字段**

- `data.id`: integer — ws_group id
- `data.group_name`: string — 角色名称（workspace 内唯一）
- `data.group_desc`: string — 角色描述
- `data.created_at`: string
- `data.avatar_url`: string — 角色头像 URL（7 天有效期签名 URL，无头像为空字符串）

```bash
emoo api PATCH /v1/ws-groups/{ws_group_id}
```

#### `GET /ws-groups/{ws_group_id}/members`

查询角色成员列表 — 分页返回角色下的成员

**认证:** Bearer Token + Emoo-User-Id

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| ws_group_id | string | 是 |  |

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| page_size | integer | 否 | 最小: 1 |
| current_page | integer | 否 | 最小: 1 |

**响应字段**

- `data.total`: integer
- `data.page_size`: integer
- `data.current_page`: integer
- `data.total_pages`: integer
- `data.results`: array[object]
- `data.results[].open_id`: string — 成员 open_id
- `data.results[].ws_username`: string — 用户名（缺失时回退到 display_name / username / mobile_num）
- `data.results[].ws_user_type`: integer — 用户角色：1=工作区用户、2=工作区管理员、3=工作区拥有者 可选值: 1, 2, 3
- `data.results[].is_active`: boolean — 是否启用
- `data.results[].email`: string
- `data.results[].mobile_num`: string
- `data.results[].avatar_url`: string — 成员头像 URL（7 天有效期签名 URL，无头像为空字符串）

```bash
emoo api GET /v1/ws-groups/{ws_group_id}/members
```

#### `POST /ws-groups/{ws_group_id}/members`

通过 open_id 批量添加成员到角色（幂等）

**认证:** Bearer Token + Emoo-User-Id

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| ws_group_id | string | 是 |  |

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | integer | 是 | 角色 ID |

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| open_ids | array[string] | 是 | 成员 open_id 列表（每个不能为空字符串） |

```bash
emoo api POST /v1/ws-groups/{ws_group_id}/members
```

#### `DELETE /ws-groups/{ws_group_id}/members/{open_id}`

通过 open_id 从角色中移除单个成员（幂等）

**认证:** Bearer Token + Emoo-User-Id

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| ws_group_id | string | 是 |  |
| open_id | string | 是 |  |

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | integer | 是 | 角色 ID |
| open_id | string | 是 | 成员 open_id |

```bash
emoo api DELETE /v1/ws-groups/{ws_group_id}/members/{open_id}
```

### 知识库/上传文件

| 方法 | 路径 | 说明 |
|------|------|------|
| `DELETE` | `/data/kb-file` | 删除知识库文件 |
| `POST` | `/data/kb-file` | 登记已上传的文件 |
| `GET` | `/data/kb-file/{doc_key}/permission` | 读取知识库文件权限 |
| `PUT` | `/data/kb-file/{doc_key}/permission` | 设置知识库文件权限 |

#### `DELETE /data/kb-file`

删除知识库文件 — 软删除

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| doc_key | string | 是 | 待删除文件文档的 doc_key 最长: 255 |

**响应字段**

- `data.deleted`: boolean

```bash
emoo api DELETE /v1/data/kb-file
```

#### `POST /data/kb-file`

登记已上传的文件 — 把一个**已上传**的文件登记为知识库文件，可选归属到某个 folder

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| file_key | string | 是 | 确认上传后拿到的 file_key；必须是已确认上传的文件，否则 4041 file_not_found 最长: 255 |
| file_name | string | 是 | 原始文件名（含扩展名），决定扩展名白名单校验。白名单：pdf/docx/doc/pptx/xlsx/xls/csv/txt/md/markdown/html/htm/json/xml/jpg/jpeg/png/gif/bmp 最长: 500 |
| file_size | integer | 是 | 文件字节数 最小: 0 |
| mime_type | string | 否 | 可选，默认空串 |
| folder_id | integer | 否 | 可选，归属 folder；必须属于当前应用，否则 4012 data_not_found。null / 不传 = 根目录 最小: 1 |
| title | string | 否 | 可选展示名，默认 = file_name 最长: 500 |

**响应字段**

- `data.id`: integer
- `data.doc_key`: string — 文档唯一 key，删除 / 权限接口的定位标识
- `data.ws_app_id`: integer
- `data.title`: string — 展示名（默认 = file_name，可改）
- `data.summary`: string
- `data.file_key`: string — 源文件的 file_key（upload-credentials → confirm 拿到）
- `data.extra`: object — 文件元信息（白名单字段）
- `data.scope`: string
- `data.folder_id`: integer — 所属 folder id，null = 根目录
- `data.folder_order`: integer
- `data.created_at`: string
- `data.updated_at`: string
- `data.deleted_at`: string

```bash
emoo api POST /v1/data/kb-file
```

#### `GET /data/kb-file/{doc_key}/permission`

读取知识库文件权限 — 读取这份文件的访问范围：谁可见 / 谁可删除

**认证:** Bearer Token + Emoo-User-Id

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| doc_key | string | 是 |  |

**响应字段**

- `data.visible`: object — 权限受众三态：all=全员；none=不授权（仅超管与创建者仍可访问）；specified=指定用户/组。
- `data.deletable`: object — 权限受众三态：all=全员；none=不授权（仅超管与创建者仍可访问）；specified=指定用户/组。

```bash
emoo api GET /v1/data/kb-file/{doc_key}/permission
```

#### `PUT /data/kb-file/{doc_key}/permission`

设置知识库文件权限 — 整体覆盖设置这份文件的访问范围（可见 / 可删除）

**认证:** Bearer Token + Emoo-User-Id

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| doc_key | string | 是 |  |

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| visible | object | 是 | 权限受众三态：all=全员；none=不授权（仅超管与创建者仍可访问）；specified=指定用户/组。 |
| deletable | object | 是 | 权限受众三态：all=全员；none=不授权（仅超管与创建者仍可访问）；specified=指定用户/组。 |

```bash
emoo api PUT /v1/data/kb-file/{doc_key}/permission
```

### 知识库/文件管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/data/files/confirm` | 确认文件上传完成 |
| `GET` | `/data/files/download-url` | 获取文件下载链接 |
| `POST` | `/data/files/extract-content` | 解析文件内容为文本 |
| `POST` | `/data/files/upload-credentials` | 获取一批文件的上传凭证 |

#### `POST /data/files/confirm`

确认文件上传完成, 创建文件元数据记录, 返回 24h 下载链接

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| files | array[object] | 是 | 最多: 20 项 |

**响应字段**

- `data[].file_key`: string
- `data[].url`: string — 24h 有效下载链接

```bash
emoo api POST /v1/data/files/confirm
```

#### `GET /data/files/download-url`

获取文件下载链接 (24h 有效)。confirm 返回的 URL 过期后用此刷新

**认证:** Bearer Token + Emoo-User-Id

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| file_key | string | 是 | 文件 file_key |

**响应字段**

- `data.url`: string — 24h 有效下载链接

```bash
emoo api GET /v1/data/files/download-url
```

#### `POST /data/files/extract-content`

解析文件内容为文本 — 按 `file_key` 批量解析文件内容为纯文本（同步返回）

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| file_keys | array[string] | 是 | 最多: 20 项 |

**响应字段**

- `data[].file_key`: string
- `data[].content`: string — 解析出的文本；空串表示拿不到文本，原因见 reason
- `data[].reason`: string — 仅在没抽到内容且可明确归因时返回。unsupported_file_type=不支持的文件类型（含图片，本接口不走 OCR）；file_too_large=超过 50MB 解析上限；extract_failed=下载或解析异常。content 为空串且无 reason 表示解析成功但文件本身无文本。 可选值: unsupported_file_type, file_too_large, extract_failed

```bash
emoo api POST /v1/data/files/extract-content
```

#### `POST /data/files/upload-credentials`

获取一批文件的上传凭证 (1-20个, 凭证 1h 过期)。返回 upload 指令 + file_key

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| files | array[object] | 是 | 最多: 20 项 |

**响应字段**

- `data[].file_key`: string — emoo 分配的文件 key，confirm 时回传
- `data[].file_name`: string
- `data[].file_size`: integer
- `data[].mime_type`: string — 未传时为空串
- `data[].upload`: object

```bash
emoo api POST /v1/data/files/upload-credentials
```

### 知识库/Folder 管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `DELETE` | `/data/folder` | 删除 folder |
| `POST` | `/data/folder` | 创建 folder |
| `PUT` | `/data/folder` | 更新 folder（改名 / 移动） |
| `GET` | `/data/folder/items` | 列出 folder 直接 children |

#### `DELETE /data/folder`

删除 folder (限超管)。子孙级联删除, 下属 table/document 上浮到祖父

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| folder_id | integer | 是 | 目标 folder ID 最小: 1 |

**响应字段**

- `data.folder_id`: integer — 已删除的 folder ID

```bash
emoo api DELETE /v1/data/folder
```

#### `POST /data/folder`

创建 folder (限 workspace 超管)。同 parent 下名称唯一

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| name | string | 是 | folder 名称（同 parent 下唯一，≤200 字符） 最长: 200 |
| parent_id | integer | 否 | 父 folder ID；不传 / null = 根 folder 最小: 1 |

**响应字段**

- `data.id`: integer — folder ID
- `data.ws_app_id`: integer — 所属 ws_app ID
- `data.workspace_id`: integer — 所属 workspace ID
- `data.name`: string — folder 名称
- `data.parent_id`: integer — 父 folder ID，null = 根 folder
- `data.created_by`: integer
- `data.created_at`: string
- `data.updated_by`: integer
- `data.updated_at`: string
- `data.table_count`: integer — 直接子 table + document 总数；OpenAPI 写接口（create/update folder）恒为 null
- `data.order`: integer — 同 parent 下排序值

```bash
emoo api POST /v1/data/folder
```

#### `PUT /data/folder`

更新 folder (改名/移动, 限超管)。name 或 parent_id 至少传一项; parent_id PATCH 语义

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| folder_id | integer | 是 | 目标 folder ID 最小: 1 |
| name | string | 否 | 新名称 最长: 200 |
| parent_id | integer | 否 | 不传=不改；null=移到根；int=移到目标 parent 最小: 1 |

**响应字段**

- `data.id`: integer — folder ID
- `data.ws_app_id`: integer — 所属 ws_app ID
- `data.workspace_id`: integer — 所属 workspace ID
- `data.name`: string — folder 名称
- `data.parent_id`: integer — 父 folder ID，null = 根 folder
- `data.created_by`: integer
- `data.created_at`: string
- `data.updated_by`: integer
- `data.updated_at`: string
- `data.table_count`: integer — 直接子 table + document 总数；OpenAPI 写接口（create/update folder）恒为 null
- `data.order`: integer — 同 parent 下排序值

```bash
emoo api PUT /v1/data/folder
```

#### `GET /data/folder/items`

列出 folder 直接 children (混合 folder+table+document，不递归)。所有成员可调

**认证:** Bearer Token + Emoo-User-Id

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| folder_id | integer | 否 | 不传 / null = 列根级；int = 列指定 folder 直接 children 最小: 1 |

**响应字段**

- `data.items`: array[object] — 顺序：先 folder（按 order），再 table + document（按 folder_order）

```bash
emoo api GET /v1/data/folder/items
```

### 知识库/表管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `DELETE` | `/data/table` | 删除数据表 |
| `GET` | `/data/table` | 获取数据表列表（分页） |
| `POST` | `/data/table` | 创建数据表 |
| `PUT` | `/data/table` | 更新数据表 |
| `GET` | `/data/table/detail` | 获取数据表详情 |

#### `DELETE /data/table`

软删除数据表，通过 table_key 或 table_name 定位

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| table_key | string | 否 | 表唯一标识（推荐） |
| table_name | string | 否 | 表名称 |

**响应字段**

- `data.deleted`: boolean

```bash
emoo api DELETE /v1/data/table
```

#### `GET /data/table`

分页获取数据表列表

**认证:** Bearer Token + Emoo-User-Id

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| page_size | integer | 否 | 每页数量，默认 20 最小: 1 |
| current_page | integer | 否 | 页码，默认 1 最小: 1 |
| folder_id | integer | 否 | 按文件夹过滤，不传 / null 则返回全部表 最小: 1 |

**响应字段**

- `data.total`: integer
- `data.page_size`: integer
- `data.current_page`: integer
- `data.total_pages`: integer
- `data.results`: array[object]
- `data.results[].table_key`: string — 表唯一标识
- `data.results[].table_name`: string — 表名称
- `data.results[].folder_id`: integer — 所属文件夹 ID，null = 未分类
- `data.results[].extra`: object — 扩展元数据
- `data.results[].column_count`: integer — 列数量
- `data.results[].record_count`: integer — 记录数量
- `data.results[].created_at`: string
- `data.results[].updated_at`: string
- `data.results[].columns`: array[object] — 列详情，仅在 get_table / create_table 接口返回

```bash
emoo api GET /v1/data/table
```

#### `POST /data/table`

创建数据表，可同时指定初始列定义

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| table_name | string | 是 | 表名称 |
| extra | object | 否 | 扩展元数据 |
| folder_id | integer | 否 | 所属文件夹 ID，不传为未分类 最小: 1 |
| columns | array[object] | 否 | 初始列定义数组 |

**响应字段**

- `data.table_key`: string — 表唯一标识
- `data.table_name`: string — 表名称
- `data.folder_id`: integer — 所属文件夹 ID，null = 未分类
- `data.extra`: object — 扩展元数据
- `data.column_count`: integer — 列数量
- `data.record_count`: integer — 记录数量
- `data.created_at`: string
- `data.updated_at`: string
- `data.columns`: array[object] — 列详情，仅在 get_table / create_table 接口返回

```bash
emoo api POST /v1/data/table
```

#### `PUT /data/table`

更新数据表名称或扩展元数据，通过 table_key 或 table_name 定位

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| table_key | string | 否 | 表唯一标识（推荐） |
| table_name | string | 否 | 表名称 |
| new_table_name | string | 否 | 新的表名称 |
| extra | object | 否 | 扩展元数据 |
| folder_id | integer | 否 | 移动到指定文件夹；传 null 表示移出文件夹；不传则保持不变 最小: 1 |

**响应字段**

- `data.table_key`: string — 表唯一标识
- `data.table_name`: string — 表名称
- `data.folder_id`: integer — 所属文件夹 ID，null = 未分类
- `data.extra`: object — 扩展元数据
- `data.column_count`: integer — 列数量
- `data.record_count`: integer — 记录数量
- `data.created_at`: string
- `data.updated_at`: string
- `data.columns`: array[object] — 列详情，仅在 get_table / create_table 接口返回

```bash
emoo api PUT /v1/data/table
```

#### `GET /data/table/detail`

获取表详情（含完整列定义），通过 table_key 或 table_name 直查

**认证:** Bearer Token + Emoo-User-Id

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| table_key | string | 否 | 表唯一标识（与 table_name 二选一） |
| table_name | string | 否 | 表名称 |

**响应字段**

- `data.table_key`: string — 表唯一标识
- `data.table_name`: string — 表名称
- `data.folder_id`: integer — 所属文件夹 ID，null = 未分类
- `data.extra`: object — 扩展元数据
- `data.column_count`: integer — 列数量
- `data.record_count`: integer — 记录数量
- `data.created_at`: string
- `data.updated_at`: string
- `data.columns`: array[object] — 列详情，仅在 get_table / create_table 接口返回

```bash
emoo api GET /v1/data/table/detail
```

### 知识库/列管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `DELETE` | `/data/table/columns` | 删除列 |
| `POST` | `/data/table/columns` | 添加列 |
| `PUT` | `/data/table/columns` | 更新列 |

#### `DELETE /data/table/columns`

软删除列，通过 table_key/table_name + column_key/column_name 定位

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| table_key | string | 否 | 表唯一标识（推荐） |
| table_name | string | 否 | 表名称 |
| column_key | string | 否 |  |
| column_name | string | 否 |  |

**响应字段**

- `data.deleted`: boolean

```bash
emoo api DELETE /v1/data/table/columns
```

#### `POST /data/table/columns`

向数据表添加一列，通过 table_key 或 table_name 定位目标表

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| table_key | string | 否 | 表唯一标识（推荐） |
| table_name | string | 否 | 表名称 |
| column_name | string | 是 |  |
| type | string | 是 | 可选值: string, number, boolean, date, time, datetime, select, user, group, file, reference |
| title_column | boolean | 否 |  |
| multiple | boolean | 否 |  |
| reference_table_key | string | 否 | 与 reference_table_name 互斥 |
| reference_table_name | string | 否 | 与 reference_table_key 互斥 |
| options | object | 否 |  |
| extra | object | 否 |  |

**响应字段**

- `data.column_key`: string — 列唯一标识
- `data.column_name`: string — 列名称
- `data.type`: string — 可选值: string, number, boolean, date, time, datetime, select, user, group, file, reference
- `data.table_key`: string — 所属表 key
- `data.title_column`: boolean
- `data.multiple`: boolean
- `data.order`: integer — 列顺序
- `data.reference_table_key`: string
- `data.reference_table_name`: string
- `data.options`: object
- `data.extra`: object
- `data.created_at`: string
- `data.updated_at`: string

```bash
emoo api POST /v1/data/table/columns
```

#### `PUT /data/table/columns`

更新列属性，通过 table_key/table_name + column_key/column_name 定位

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| table_key | string | 否 | 表唯一标识（推荐） |
| table_name | string | 否 | 表名称 |
| column_key | string | 否 | 列唯一标识（推荐，与 column_name 二选一） |
| column_name | string | 否 | 列名称（用于定位列） |
| new_column_name | string | 否 | 新的列名称 |
| type | string | 否 | 可选值: string, number, boolean, date, time, datetime, select, user, group, file, reference |
| title_column | boolean | 否 |  |
| multiple | boolean | 否 |  |
| reference_table_key | string | 否 |  |
| reference_table_name | string | 否 |  |
| options | object | 否 |  |
| extra | object | 否 |  |

**响应字段**

- `data.column_key`: string — 列唯一标识
- `data.column_name`: string — 列名称
- `data.type`: string — 可选值: string, number, boolean, date, time, datetime, select, user, group, file, reference
- `data.table_key`: string — 所属表 key
- `data.title_column`: boolean
- `data.multiple`: boolean
- `data.order`: integer — 列顺序
- `data.reference_table_key`: string
- `data.reference_table_name`: string
- `data.options`: object
- `data.extra`: object
- `data.created_at`: string
- `data.updated_at`: string

```bash
emoo api PUT /v1/data/table/columns
```

### 知识库/表记录

| 方法 | 路径 | 说明 |
|------|------|------|
| `DELETE` | `/data/records` | 删除记录 |
| `POST` | `/data/records` | 插入记录 |
| `PUT` | `/data/records` | 更新单条记录 |
| `POST` | `/data/records/batch-update` | 批量更新记录 |
| `POST` | `/data/records/list` | 查询记录列表 |

#### `DELETE /data/records`

删除记录（最多 100 条）

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| table_key | string | 否 |  |
| table_name | string | 否 |  |
| record_keys | array[string] | 否 | 最多: 100 项 |
| record_titles | array[string] | 否 | 最多: 100 项 |

**响应字段**

- `data.deleted_count`: integer

```bash
emoo api DELETE /v1/data/records
```

#### `POST /data/records`

插入记录到数据表（最多 100 条）

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| table_key | string | 否 | 数据表 key（与 table_name 二选一） |
| table_name | string | 否 | 数据表名（与 table_key 二选一） |
| records | array[object] | 是 | 最多: 100 项 |

**响应字段**

- `data[].id`: integer — 记录内部 ID
- `data[].record_key`: string — 记录唯一标识
- `data[].fields`: object — 记录字段值字典，key 为 column_key 或 column_name，value 按字段类型多态（见 info.description）
- `data[].created_by`: object — 记录系统字段 created_by/updated_by 的用户元数据：id 是 open_id 字符串（非 integer），name 按 ws_username > display_name > username 回退
- `data[].created_at`: string
- `data[].updated_by`: object — 记录系统字段 created_by/updated_by 的用户元数据：id 是 open_id 字符串（非 integer），name 按 ws_username > display_name > username 回退
- `data[].updated_at`: string

```bash
emoo api POST /v1/data/records
```

#### `PUT /data/records`

更新单条记录（通过 record_key 或 record_title 定位）

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| table_key | string | 否 |  |
| table_name | string | 否 |  |
| record_key | string | 否 | 记录唯一标识（与 record_title 二选一） |
| record_title | string | 否 | 标题字段值，后端通过 title 列解析为 record_key |
| fields | object | 是 | 记录字段值字典，key 为 column_key 或 column_name，value 按字段类型多态（见 info.description） |

**响应字段**

- `data.id`: integer — 记录内部 ID
- `data.record_key`: string — 记录唯一标识
- `data.fields`: object — 记录字段值字典，key 为 column_key 或 column_name，value 按字段类型多态（见 info.description）
- `data.created_by`: object — 记录系统字段 created_by/updated_by 的用户元数据：id 是 open_id 字符串（非 integer），name 按 ws_username > display_name > username 回退
- `data.created_at`: string
- `data.updated_by`: object — 记录系统字段 created_by/updated_by 的用户元数据：id 是 open_id 字符串（非 integer），name 按 ws_username > display_name > username 回退
- `data.updated_at`: string

```bash
emoo api PUT /v1/data/records
```

#### `POST /data/records/batch-update`

批量更新记录（最多 100 条）

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| table_key | string | 否 |  |
| table_name | string | 否 |  |
| records | array[object] | 是 | 最多: 100 项 |

**响应字段**

- `data[].id`: integer — 记录内部 ID
- `data[].record_key`: string — 记录唯一标识
- `data[].fields`: object — 记录字段值字典，key 为 column_key 或 column_name，value 按字段类型多态（见 info.description）
- `data[].created_by`: object — 记录系统字段 created_by/updated_by 的用户元数据：id 是 open_id 字符串（非 integer），name 按 ws_username > display_name > username 回退
- `data[].created_at`: string
- `data[].updated_by`: object — 记录系统字段 created_by/updated_by 的用户元数据：id 是 open_id 字符串（非 integer），name 按 ws_username > display_name > username 回退
- `data[].updated_at`: string

```bash
emoo api POST /v1/data/records/batch-update
```

#### `POST /data/records/list`

查询记录列表（分页+过滤+排序）

**认证:** Bearer Token + Emoo-User-Id

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| table_key | string | 否 |  |
| table_name | string | 否 |  |
| page_size | integer | 否 | 最小: 1 |
| current_page | integer | 否 | 最小: 1 |
| filters | array[string] | 否 | 过滤条件，每条格式 `field:op:value`。op ∈ {eq, neq, contains, in, not_in, gte, lte, is_empty, is_not_empty}。in/not_in 的 value 用逗号分隔多值。field 支持 column_key/column_name/系统字段（id/record_key/created_by/updated_by/created_at/updated_at）。 |
| sort | string | 否 | 排序，格式 `field:asc` 或 `field:desc`，field 支持 column_key/column_name/系统字段 |

**响应字段**

- `data.total`: integer
- `data.page_size`: integer
- `data.current_page`: integer
- `data.total_pages`: integer
- `data.results`: array[object]
- `data.results[].id`: integer — 记录内部 ID
- `data.results[].record_key`: string — 记录唯一标识
- `data.results[].fields`: object — 记录字段值字典，key 为 column_key 或 column_name，value 按字段类型多态（见 info.description）
- `data.results[].created_by`: object — 记录系统字段 created_by/updated_by 的用户元数据：id 是 open_id 字符串（非 integer），name 按 ws_username > display_name > username 回退
- `data.results[].created_at`: string
- `data.results[].updated_by`: object — 记录系统字段 created_by/updated_by 的用户元数据：id 是 open_id 字符串（非 integer），name 按 ws_username > display_name > username 回退
- `data.results[].updated_at`: string

```bash
emoo api POST /v1/data/records/list
```

### 知识库/表权限管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/data/table/{table_key}/permissions` | 获取表的所有权限策略 |
| `POST` | `/data/table/{table_key}/permissions` | 创建一条权限策略 |
| `DELETE` | `/data/table/{table_key}/permissions/{role_key}` | 删除权限策略 |
| `PUT` | `/data/table/{table_key}/permissions/{role_key}` | 更新权限策略（整策略覆盖） |

#### `GET /data/table/{table_key}/permissions`

获取表中已配置的全部权限策略

**认证:** Bearer Token + Emoo-User-Id

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| table_key | string | 是 | 数据表 key |

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| table_key | string | 是 | 数据表 key |

**响应字段**

- `data[].role_key`: string — 策略唯一标识，后端自动生成（格式 strategy_<8位>）
- `data[].description`: string — 策略描述（必填非空）
- `data[].audience`: object — 策略受众：所有人 或 指定用户/组
- `data[].data_range`: string — all=所有行；specified=按 conditions 过滤 可选值: all, specified
- `data[].conditions`: array — 行级过滤条件，data_range=specified 时非空
- `data[].column_permissions`: object — 每列访问级别，key=column_key，value ∈ visible / editable / hidden
- `data[].allow_create`: boolean — 是否允许创建记录
- `data[].allow_delete`: boolean — 是否允许删除记录
- `data[].allow_schema_update`: boolean — 是否允许改 schema
- `data[].allow_schema_delete`: boolean — 是否允许删 schema

```bash
emoo api GET /v1/data/table/{table_key}/permissions
```

#### `POST /data/table/{table_key}/permissions`

为指定表创建权限策略，role_key 由后端自动生成

**认证:** Bearer Token + Emoo-User-Id

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| table_key | string | 是 | 数据表 key |

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| table_key | string | 是 | 数据表 key |

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| description | string | 是 | 策略描述（必填非空） |
| audience | object | 是 | 策略受众：所有人 或 指定用户/组 |
| data_range | string | 是 | 可选值: all, specified |
| conditions | array | 否 |  |
| column_permissions | object | 是 |  |
| allow_create | boolean | 否 |  |
| allow_delete | boolean | 否 |  |
| allow_schema_update | boolean | 否 |  |
| allow_schema_delete | boolean | 否 |  |

**响应字段**

- `data.role_key`: string — 策略唯一标识，后端自动生成（格式 strategy_<8位>）
- `data.description`: string — 策略描述（必填非空）
- `data.audience`: object — 策略受众：所有人 或 指定用户/组
- `data.data_range`: string — all=所有行；specified=按 conditions 过滤 可选值: all, specified
- `data.conditions`: array — 行级过滤条件，data_range=specified 时非空
- `data.column_permissions`: object — 每列访问级别，key=column_key，value ∈ visible / editable / hidden
- `data.allow_create`: boolean — 是否允许创建记录
- `data.allow_delete`: boolean — 是否允许删除记录
- `data.allow_schema_update`: boolean — 是否允许改 schema
- `data.allow_schema_delete`: boolean — 是否允许删 schema

```bash
emoo api POST /v1/data/table/{table_key}/permissions
```

#### `DELETE /data/table/{table_key}/permissions/{role_key}`

物理删除权限策略。跨表保护：若该 role 同时命中其他表，拒绝删除 (4209)

**认证:** Bearer Token + Emoo-User-Id

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| table_key | string | 是 | 数据表 key |
| role_key | string | 是 | 策略 id |

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| table_key | string | 是 | 数据表 key |
| role_key | string | 是 | 策略 ID |

**响应字段**

- `data.role_key`: string
- `data.deleted`: boolean

```bash
emoo api DELETE /v1/data/table/{table_key}/permissions/{role_key}
```

#### `PUT /data/table/{table_key}/permissions/{role_key}`

整策略覆盖更新。跨表保护：若该 role 同时命中其他表，拒绝更新 (4209)

**认证:** Bearer Token + Emoo-User-Id

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| table_key | string | 是 | 数据表 key |
| role_key | string | 是 | 策略 id（来自 list） |

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| table_key | string | 是 | 数据表 key |
| role_key | string | 是 | 策略 ID |

**Body 参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| description | string | 是 | 策略描述（必填非空） |
| audience | object | 是 | 策略受众：所有人 或 指定用户/组 |
| data_range | string | 是 | 可选值: all, specified |
| conditions | array | 否 |  |
| column_permissions | object | 是 |  |
| allow_create | boolean | 否 |  |
| allow_delete | boolean | 否 |  |
| allow_schema_update | boolean | 否 |  |
| allow_schema_delete | boolean | 否 |  |

**响应字段**

- `data.role_key`: string — 策略唯一标识，后端自动生成（格式 strategy_<8位>）
- `data.description`: string — 策略描述（必填非空）
- `data.audience`: object — 策略受众：所有人 或 指定用户/组
- `data.data_range`: string — all=所有行；specified=按 conditions 过滤 可选值: all, specified
- `data.conditions`: array — 行级过滤条件，data_range=specified 时非空
- `data.column_permissions`: object — 每列访问级别，key=column_key，value ∈ visible / editable / hidden
- `data.allow_create`: boolean — 是否允许创建记录
- `data.allow_delete`: boolean — 是否允许删除记录
- `data.allow_schema_update`: boolean — 是否允许改 schema
- `data.allow_schema_delete`: boolean — 是否允许删 schema

```bash
emoo api PUT /v1/data/table/{table_key}/permissions/{role_key}
```

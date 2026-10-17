# emoo OpenAPI 调用指南

本文档是 emoo OpenAPI 的**开发指南**：认证方式、错误码策略、跨模块共性概念、模块导航。各接口的字段定义以 `*.swagger.json` 为唯一信源（供 Apifox 等工具导入），本文件不重复字段表。

## 基础信息

- **SaaS 版本地址**: `https://app.emooai.com/open-api`
- **私有部署版本**: `https://<您的部署域名>/open-api`
- **数据格式**: JSON
- **字符编码**: UTF-8
- **接口测试**: [Apifox 在线调试](http://open.emooai.com)

---

## 认证方式

emoo OpenAPI 支持两种认证方式：

### 方式一：Client ID + Client Secret（OAuth 客户端模式）

适用于服务端对服务端的集成场景。

#### 1. 获取凭证

在工作区管理后台创建 OAuth 客户端，获得 `client_id` 和 `client_secret`。

#### 2. 获取 Access Token

接口定义见 [认证模块](openapi_auth.swagger.json)（`GET /auth/token`）。

```bash
curl -X GET "https://app.emooai.com/open-api/v1/auth/token?client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET"
```

响应（`expires_in` 秒，默认 7200 = 2 小时）：

```json
{
  "code": 200,
  "message": "success",
  "data": { "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", "expires_in": 7200, "token_type": "Bearer" }
}
```

#### 3. 使用 Token 调用 API

```bash
curl -X POST "https://app.emooai.com/open-api/v1/search" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"keyword": "搜索关键词"}'
```

#### 4. 指定用户身份（必填）

OAuth 客户端模式必须通过请求头指定用户身份：

```
Emoo-User-Id: <用户的 open_id>
```

**必填接口**：搜索、数据拉取、数据操作、对话、用户管理、文件、应用与文档组等所有需用户上下文的接口。

**可选接口**：消息推送（`POST /message`）可通过请求体 `emoo_user_id` 覆盖请求头。

不传 `Emoo-User-Id` 时返回 `4084 invalid_open_api_user_id`（HTTP 401）。

---

### 方式二：API Key

适用于需要绑定特定用户身份的集成场景。

#### 1. 获取 API Key

在工作区管理后台创建 API Key，创建时绑定用户。创建成功后系统返回完整的 Key（以 `emoo_` 开头）。

> **重要**: API Key 只在创建时显示一次，请妥善保存。

#### 2. 使用 API Key 调用 API

直接使用 API Key 作为 Bearer Token，**自动继承绑定用户权限**，无需 `Emoo-User-Id`：

```bash
curl -X POST "https://app.emooai.com/open-api/v1/search" \
  -H "Authorization: Bearer emoo_YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"keyword": "搜索关键词"}'
```

---

### 认证方式对比

| 特性         | Client ID/Secret     | API Key          |
| ------------ | -------------------- | ---------------- |
| 适用场景     | 服务端集成           | 用户级集成       |
| 用户身份     | 必须传 `Emoo-User-Id` | 自动绑定         |
| Token 有效期 | 2 小时               | 可设置过期时间   |
| 权限继承     | OAuth 客户端 + 指定用户 | 绑定用户       |

---

## 错误码策略

emoo OpenAPI 的 HTTP 状态码与业务错误码分离：

- **HTTP 200**：处理成功（body.code=200）或**业务错误**（body.code=4xxx）。除认证外所有错误都走 200。
- **HTTP 401**：仅认证失败（`4084 invalid_open_api_user_id`、OAuth token 失效）。

调用方判断成败看 `body.code == 200`，**不能**只看 HTTP 状态。

**错误响应格式**：

```json
{ "code": 4xxx, "message": "error_name", "data": null }
```

### 常见业务错误码

| code | message                    | 触发场景                                      |
| ---- | -------------------------- | --------------------------------------------- |
| 4006 | workspace_not_found        | workspace 不存在或被删除                      |
| 4007 | user_not_found             | open_id 在 workspace 中无对应用户             |
| 4008 | ws_app_not_found           | ws_app_key 不存在                             |
| 4012 | data_not_found             | emoo_user_id 找不到对应用户                   |
| 4015 | invalid_params             | 参数校验失败（具体原因见 data.reason）        |
| 4029 | ws_group_name_exists       | 角色名重复                                    |
| 4031 | ws_group_not_found         | ws_group_id 不存在                            |
| 4042 | permission_denied          | 权限不足（如非超管调超管接口）                |
| 4084 | invalid_open_api_user_id   | 缺 Emoo-User-Id / 用户不存在（HTTP 401）      |
| 4xxx | base_table_not_found 等    | 各模块的资源不存在错误，详见对应 swagger      |

模块专属错误码（如 4133 base_table_not_found、4205 base_folder_not_found、4210 base_open_id_invalid 等）见各 swagger.json 的 200 响应 description。

---

## 跨模块共性概念

### 用户标识统一用 open_id

emoo OpenAPI **对外统一用 `open_id`** 标识用户，后端自动翻译为内部 `ws_user_id`。涉及位置：

- **USER 类型字段的写入**（[数据操作](openapi_kb_table_record.swagger.json)）：fields 里 USER 字段的 value 传 open_id
- **USER 类型字段的过滤**（数据操作 list records）：filters 里 USER 字段的 value 传 open_id
- **USER 类型字段的返回**：响应里 USER 字段值是 `{id: open_id, name}`，**id 是 open_id 字符串，不是 integer**
- **记录系统字段** `created_by` / `updated_by`（数据操作）：结构 `{id: open_id, name}`
- **消息推送**（[消息推送](openapi_notification.swagger.json)）：`emoo_user_id` 用 open_id
- **角色成员管理**（[通讯录](openapi_contacts.swagger.json)）：`open_ids` 数组用 open_id
- **权限策略受众**（[表权限管理](openapi_kb_table_permission.swagger.json)）：`audience.user_open_ids` 用 open_id

### filter_conditions / filters 格式

两个模块都支持字段过滤，但格式不同：

**搜索能力（[search](openapi_search.swagger.json) / [data cursor](openapi_search.swagger.json)）**：`filter_conditions` 是**二维数组**，外层 OR、内层 AND：

```json
"filter_conditions": [
  [ {"field": "ws_app.ws_app_key", "operator": "eq", "value": "wapp_xxx"} ],
  [ {"field": "doc_group.id", "operator": "eq", "value": 100} ]
]
```

operator 6 种：`eq` / `neq` / `in` / `nin` / `gte` / `lte`。完整 field 列表见 search.swagger.json 的 `FilterCondition.field` enum。

**数据操作（[list records](openapi_kb_table_record.swagger.json)）**：`filters` 是**字符串数组**，每条格式 `field:op:value`：

```json
"filters": ["age:gte:18", "name:eq:张三"]
```

op 8 种：`eq` / `neq` / `in` / `not_in` / `gte` / `lte` / `is_empty` / `is_not_empty`。in/not_in 的 value 用逗号分隔多值。

### 数据字段类型多态（data 模块返回值）

[数据操作](openapi_kb_table_record.swagger.json) 响应 `fields` 内每个值由 `column.type` + `column.multiple` 决定形态：

| column.type | 单值（multiple=false）            | 多值（multiple=true）              |
| ----------- | --------------------------------- | ---------------------------------- |
| string / number / boolean / date / time / datetime | 标量值                            | 标量数组                           |
| select      | label string                      | label string[]                     |
| user        | `{id: open_id, name}`             | `[{id, name}, ...]`                |
| group       | `{id: ws_group_id, name}`         | `[{id, name}, ...]`                |
| reference   | `{id: record_key, title}`         | `[{id, title}, ...]`               |
| file        | `{file_key, name, size, url}`     | `[{...}, ...]`                     |

入参 fields 的 key 既支持 column_key 也支持 column_name（后端自动翻译）。USER 字段入参 value 传 open_id（不是 ws_user_id）。

### SSE 流式响应（chat）

[对话能力](openapi_chat.swagger.json) 的 `POST /chat/messages` 支持 `stream=true` 走 SSE。事件类型 5 种：

| 事件        | 数据                       | 说明                |
| ----------- | -------------------------- | ------------------- |
| `status`    | 状态字符串                 | 处理状态更新        |
| `message_id`| int                        | 本次消息 ID         |
| `token`     | 文本片段                   | AI 增量输出         |
| `done`      | 完成标记                   | 流结束              |
| `error`     | 错误信息                   | 异常                |

非流式（`stream=false` 或不传）走常规 JSON 一次性返回。

### 权限模型（permission）

[表权限管理](openapi_kb_table_permission.swagger.json) 暴露表维度的高层抽象，底层是 role+binding+policy 三件套：

- **role_key** 格式：`strategy_<8位>`，由后端自动生成，创建时不可指定
- **跨表保护**：更新/删除策略时，后端校验底层 role 是否只服务于当前表，命中其他表会拒绝（4209 base_role_cross_table_conflict）
- **空策略兜底**：column_permissions 至少一列非 hidden 或某个 allow_*=true，否则 4015
- **data_range=specified** 时 conditions 必填非空
- **description** 必填非空（serializer `allow_blank=False`）

### Folder 树形约束

[Folder 管理](openapi_kb_folder.swagger.json) 的树形层级：

- 最深 **10 层**（超出返 4207 base_folder_depth_exceeded）
- 移动时禁止成环（parent_id 是自身或子孙时返 4208 base_folder_cycle_detected）
- 删除 folder 时子孙级联删除，下属 table/document 上浮到祖父（**不删除业务数据**）
- 写操作限 workspace 超管（WS_OWNER / WS_ADMIN），读（items）所有成员可调

---

## 最佳实践

1. **Token 缓存**: Client ID/Secret 模式获取的 Token 有效期 2 小时，建议缓存复用，避免频繁请求
2. **API Key 安全**: API Key 只在创建时显示一次，请妥善保存，不要泄露
3. **大数据量拉取**: 文档用 `/data` 游标接口（cursor 分页）；记录用 `/data/records/list` 分页
4. **流式响应**: 对话场景建议使用 `stream=true`，提升用户体验
5. **判断成败看 body.code**: HTTP 200 也可能是业务错误，必须检查 `body.code == 200`
6. **批量更新失败检查**: `PUT /ws-user` 返回失败条目数组（成功时为 `[]`），不会整体回滚，调用方需检查数组是否为空

---

## API 模块

各模块接口定义以对应 `*.swagger.json` 为唯一信源（导入 Apifox 即可调试）。仅 [文件管理流程](openapi_kb_file.md) 保留为人类可读的流程说明。

- [认证](openapi_auth.swagger.json) — OAuth 客户端模式获取 access_token（无需 Bearer）
- [搜索能力](openapi_search.swagger.json) — 文档检索、游标分页批量拉取
- [对话能力](openapi_chat.swagger.json) — AI 对话创建、查询、消息发送（支持 SSE 流式）
- [通讯录](openapi_contacts.swagger.json) — 工作区用户（ws_user）查询/批量更新 + 角色（ws_group）CRUD 与成员管理
- [消息推送](openapi_notification.swagger.json) — 推送普通消息或 Agent 消息
- [表记录](openapi_kb_table_record.swagger.json) — 数据表记录的插入 / 更新 / 删除 / 查询
- [文件管理](openapi_kb_file.swagger.json) + [流程说明](openapi_kb_file.md) — 客户端直传对象存储
- [Folder 管理](openapi_kb_folder.swagger.json) — table 与 document 共享的树形容器
- [表与列管理](openapi_kb_table.swagger.json) — 数据表与列的 schema CRUD
- [表权限管理](openapi_kb_table_permission.swagger.json) — 数据表访问控制策略
- [Agent 管理](openapi_agent.swagger.json) — webhook / dify / coze / timus 集成型 agent
- [应用与文档组](openapi_app.swagger.json) — 工作区下应用（ws_app）与文档组（doc_group）查询

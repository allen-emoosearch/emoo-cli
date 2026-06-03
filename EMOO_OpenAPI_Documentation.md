# EMOO 开放平台 API 文档

> **Base URL:** `https://app.emoosearch.com/open-api/v1`
> **认证方式:** Bearer Token (HTTP `Authorization: Bearer <token>`)
> **文档来源:** https://open.emoosearch.com
> **生成日期:** 2026-05-29

---

## 目录

- [1. 鉴权](#1-鉴权)
  - [1.1 获取企业令牌](#11-获取企业令牌)
- [2. 通讯录](#2-通讯录)
  - [2.1 获取通讯录成员](#21-获取通讯录成员)
  - [2.2 更新成员信息](#22-更新成员信息)
- [3. 数据](#3-数据)
  - [3.1 搜索数据](#31-搜索数据)
  - [3.2 获取数据](#32-获取数据)
- [4. 对话](#4-对话)
  - [4.1 获取用户对话列表](#41-获取用户对话列表)
  - [4.2 创建对话](#42-创建对话)
  - [4.3 发送对话消息](#43-发送对话消息)
- [5. 消息](#5-消息)
  - [5.1 主动推送消息给指定用户](#51-主动推送消息给指定用户)
- [6. EMOO Base](#6-emoo-base)
  - [6.1 新建 Record](#61-新建-record)
  - [6.2 更新 Record](#62-更新-record)
  - [6.3 批量更新 Record](#63-批量更新-record)
  - [6.4 删除 Record](#64-删除-record)
  - [6.5 查询 Record 列表](#65-查询-record-列表)
  - [6.6 创建表](#66-创建表)
  - [6.7 获取表列表](#67-获取表列表)
  - [6.8 更新表](#68-更新表)
  - [6.9 删除表](#69-删除表)
  - [6.10 获取表详情](#610-获取表详情)
  - [6.11 添加列](#611-添加列)
  - [6.12 更新列](#612-更新列)
  - [6.13 删除列](#613-删除列)
- [7. 应用管理](#7-应用管理)
  - [7.1 获取应用列表](#71-获取应用列表)
  - [7.2 获取文档组列表](#72-获取文档组列表)
- [8. 数据模型](#8-数据模型)
  - [8.1 DocDetailInfo](#81-docdetailinfo)
  - [8.2 DocFilterCondition](#82-docfiltercondition)
  - [8.3 WsGroupBaseInfo](#83-wsgroupbaseinfo)
  - [8.4 WsUserDetailInfo](#84-wsuserdetailinfo)
  - [8.5 WsUserUpdate](#85-wsuserupdate)
  - [8.6 WsAppInfo](#86-wsappinfo)
  - [8.7 DocGroupInfo](#87-docgroupinfo)
- [9. 全局错误码](#9-全局错误码)
- [10. 通用说明](#10-通用说明)

---

## 1. 鉴权

### 1.1 获取企业令牌

> 获取 API 访问令牌，默认有效期 2 小时（7200 秒）。

| 项目 | 内容 |
|------|------|
| **方法** | `GET` |
| **路径** | `/auth/token` |
| **认证** | 无需认证 |

**Query 参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `grant_type` | string | 否 | 固定为 `client_credentials`，默认也是这个值 |
| `client_id` | string | 是 | 客户端标识 |
| `client_secret` | string | 是 | 客户端密钥 |

**请求示例 (Shell)：**

```bash
curl -X GET "https://app.emoosearch.com/open-api/v1/auth/token?grant_type=client_credentials&client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET"
```

**返回字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | integer | 状态码 |
| `message` | string | 状态信息 |
| `data.access_token` | string | 访问令牌 |
| `data.token_type` | string | 令牌类型（目前仅返回 `Bearer`） |
| `data.expires_in` | integer | 有效时间（秒），默认 7200 |

**返回示例：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "access_token": "eyJhbGciOi...",
    "token_type": "Bearer",
    "expires_in": 7200
  }
}
```

---

## 2. 通讯录

### 2.1 获取通讯录成员

| 项目 | 内容 |
|------|------|
| **方法** | `GET` |
| **路径** | `/ws-user` |
| **认证** | Bearer Token |

**Query 参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `page_size` | integer | 否 | 每页数据量，最大 100，默认 50 |
| `current_page` | integer | 否 | 当前页码，从 1 开始，默认 1 |
| `keyword` | string | 否 | 搜索关键词，不传则获取企业所有成员 |

**返回字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | integer | 状态码 |
| `message` | string | 状态信息 |
| `data.total` | integer | 总数据量 |
| `data.page_size` | integer | 每页数据量（最大 100） |
| `data.current_page` | integer | 当前页码（从 1 开始） |
| `data.total_pages` | integer | 总页数 |
| `data.results` | array | 成员列表，元素类型见 [WsUserDetailInfo](#84-wsuserdetailinfo) |

---

### 2.2 更新成员信息

| 项目 | 内容 |
|------|------|
| **方法** | `PUT` |
| **路径** | `/ws-user` |
| **认证** | Bearer Token |

**Body 参数（JSON 数组）：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `open_id` | string | 是 | 成员在当前工作区中的唯一标识 |
| `ws_username` | string | 否 | 用户在工作区中显示的名称 |
| `ext_info` | object | 否 | 扩展信息（自由格式 key-value） |

**请求示例：**

```json
[
  {
    "open_id": "abc123",
    "ws_username": "新用户名",
    "ext_info": { "key": "value" }
  }
]
```

**返回字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | integer | 状态码 |
| `message` | string | 状态信息 |
| `data` | null | 始终为 null |

---

## 3. 数据

### 3.1 搜索数据

> 搜索企业绑定的所有数据源。为保护用户个人数据安全，仅支持搜索企业绑定的数据源，不支持搜索个人绑定的数据源。

| 项目 | 内容 |
|------|------|
| **方法** | `POST` |
| **路径** | `/search` |
| **认证** | Bearer Token |

**Header 参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `Emoo-User-Id` | string | 是 | 用户 open_id（同一用户在不同租户中 open_id 不同） |

**Body 参数（JSON）：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `page_size` | integer | 是 | 每页条数（最大 100） |
| `current_page` | integer | 是 | 页码，从 1 开始 |
| `keyword` | string | 是 | 搜索关键词 |
| `ws_agent_key` | string | 否 | Dify/Coze/Timus 等平台需传入，用于按 Agent 数据权限过滤 |
| `text_format` | string | 否 | `plain`（默认）或 `markdown`，控制 text 类型文档的返回格式 |
| `filter_conditions` | array | 否 | 过滤条件，外层数组 OR，内层数组 AND，元素见 [DocFilterCondition](#82-docfiltercondition) |

**请求示例：**

```json
{
  "page_size": 20,
  "current_page": 1,
  "keyword": "关键词",
  "text_format": "markdown",
  "filter_conditions": [
    [
      { "field": "ws_app.ws_app_key", "operator": "eq", "value": "app_key_xxx" }
    ]
  ]
}
```

**返回字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | integer | 状态码 |
| `message` | string | 状态信息 |
| `data.total` | integer | 总记录数 |
| `data.page_size` | integer | 每页条数（最大 100） |
| `data.current_page` | integer | 当前页码 |
| `data.total_pages` | integer | 总页数 |
| `data.results` | array | 文档列表，元素类型见 [DocDetailInfo](#81-docdetailinfo) |

---

### 3.2 获取数据

> 通过游标分页获取文档数据，支持与 `/search` 相同的过滤条件。

| 项目 | 内容 |
|------|------|
| **方法** | `POST` |
| **路径** | `/data` |
| **认证** | Bearer Token |

**Header 参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `Emoo-User-Id` | string | 是 | 用户 open_id |

**Body 参数（JSON）：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `page_size` | integer | 是 | 每页条数（最大 200） |
| `cursor` | string | 否 | 分页游标，空则从头开始 |
| `text_format` | string | 否 | `plain`（默认）或 `markdown` |
| `filter_conditions` | array | 否 | 过滤条件，结构同 [DocFilterCondition](#82-docfiltercondition) |

**请求示例：**

```json
{
  "page_size": 50,
  "cursor": "",
  "text_format": "plain",
  "filter_conditions": [
    [
      { "field": "app_updated_at", "operator": "gte", "value": "2024-01-01T00:00:00+08:00" }
    ]
  ]
}
```

**返回字段：** 结构同 [搜索数据](#31-搜索数据)，`data.results` 元素类型见 [DocDetailInfo](#81-docdetailinfo)。

---

## 4. 对话

### 4.1 获取用户对话列表

> 最多返回前 50 个对话。

| 项目 | 内容 |
|------|------|
| **方法** | `GET` |
| **路径** | `/chat` |
| **认证** | Bearer Token |

**Header 参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `Emoo-User-Id` | string | 是 | 用户 open_id |

**Query 参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `page_size` | integer | 否 | 每页条数，默认 50 |
| `current_page` | integer | 否 | 页码，从 1 开始，默认 1 |

**返回字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | integer | 状态码 |
| `message` | string | 状态信息 |
| `data.total` | integer | 总数据量 |
| `data.page_size` | integer | 每页数据量（最大 100） |
| `data.current_page` | integer | 当前页码 |
| `data.total_pages` | integer | 总页数 |
| `data.results[].id` | integer | 对话 ID |
| `data.results[].title` | string | 对话标题 |
| `data.results[].created_at` | string | 创建时间 |
| `data.results[].updated_at` | string | 最近更新时间 |

---

### 4.2 创建对话

| 项目 | 内容 |
|------|------|
| **方法** | `POST` |
| **路径** | `/chat` |
| **认证** | Bearer Token |

**Header 参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `Emoo-User-Id` | string | 是 | 用户 open_id |

**Body 参数（JSON）：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `title` | string | 否 | 对话标题（可选） |

**请求示例：**

```json
{
  "title": "新对话"
}
```

**返回字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | integer | 状态码 |
| `message` | string | 状态信息 |
| `data.chat_id` | integer | 新建对话的 ID，后续对话时需使用 |

---

### 4.3 发送对话消息

> 向指定对话发送消息并获取 AI 回复。**注意：当前不支持 SSE 流式返回，只支持一次性返回。**

| 项目 | 内容 |
|------|------|
| **方法** | `POST` |
| **路径** | `/chat/messages` |
| **认证** | Bearer Token |

**Header 参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `Emoo-User-Id` | string | 是 | 用户 open_id |

**Body 参数（JSON）：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `query` | string | 是 | 提问/消息内容 |
| `chat_id` | integer | 否 | 对话 ID，为空则创建新对话 |
| `file_list` | array | 否 | 引用文件列表，最多 10 个，支持 pdf、txt、markdown、office 和常见图片 |
| `ws_agent_key` | string | 否 | 指定 Agent 回复，默认使用 emoo 默认 Agent |
| `stream` | boolean | 否 | 是否 SSE 流式，**默认 false，当前不支持 SSE** |

**请求示例：**

```json
{
  "query": "你好，请介绍一下你自己",
  "chat_id": 12345,
  "file_list": [],
  "ws_agent_key": "",
  "stream": false
}
```

**返回字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | integer | 状态码 |
| `message` | string | 状态信息 |
| `data.chat_id` | integer | 对话 ID |
| `data.complete_response` | string | AI 回复内容（可能包含 `[xxx]` 格式的引用标记，可按需正则替换去除） |
| `data.message_id` | string | 本条消息唯一 ID |

---

## 5. 消息

### 5.1 主动推送消息给指定用户

| 项目 | 内容 |
|------|------|
| **方法** | `POST` |
| **路径** | `/message` |
| **认证** | Bearer Token |

**Body 参数（JSON）：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `message_type` | string | 是 | 消息类型：`normal`（普通通知）或 `agent`（Agent 主动推送） |
| `content` | string | 是 | 消息正文，最长 300 字符。Agent 类型消息在推送预览中仅显示纯文本（最長 300），在对话中保留完整 markdown |
| `emoo_user_id` | string | 否 | 接收者的 Emoo 用户 ID |
| `normal_message_info` | object | 条件 | 当 `message_type` 为 `normal` 时必填 |
| `normal_message_info.from_title` | string | 是 | 来源名称 |
| `normal_message_info.from_image_url` | string | 否 | 来源头像 URL，不传则使用工作区默认 Logo |
| `normal_message_info.detail_link` | string | 否 | 详情链接 |
| `agent_message_info` | object | 条件 | 当 `message_type` 为 `agent` 时必填 |
| `agent_message_info.ws_agent_key` | string | 是 | Agent 的 Key |
| `agent_message_info.chat_id` | string | 否 | 目标对话 ID，不传则创建新对话 |

**请求示例（普通消息）：**

```json
{
  "message_type": "normal",
  "content": "您有一条新的通知",
  "emoo_user_id": "user_xxx",
  "normal_message_info": {
    "from_title": "系统通知",
    "from_image_url": "",
    "detail_link": "https://example.com/detail"
  }
}
```

**请求示例（Agent 消息）：**

```json
{
  "message_type": "agent",
  "content": "您好，以下是本周的工作总结...",
  "emoo_user_id": "user_xxx",
  "agent_message_info": {
    "ws_agent_key": "agent_key_xxx",
    "chat_id": "12345"
  }
}
```

**返回字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | integer | 状态码 |
| `message` | string | 状态信息 |
| `data.message_id` | integer | 新创建的消息 ID |
| `data.chat_id` | integer | 关联的对话 ID（agent 类型一定返回） |
| `data.chat_message_id` | integer | 对话内消息 ID（agent 类型一定返回） |

---

## 6. EMOO Base

### 6.1 新建 Record

> **状态：developing（开发中）**

| 项目 | 内容 |
|------|------|
| **方法** | `POST` |
| **路径** | `/data/records` |
| **认证** | Bearer Token |

**Header 参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `Emoo-User-Id` | string | 是 | 用户 open_id |

**Body 参数（JSON）：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `table_key` | string | 条件 | 表的系统标识，与 `table_name` 二选一 |
| `table_name` | string | 条件 | 表的显示名称，与 `table_key` 二选一 |
| `records` | array | 是 | 记录列表，1-100 条。每条为 key-value 对象，key 可以是 `column_key` 或 `column_name`，value 根据列类型为 `string`/`number`/`boolean`/`array` |

**请求示例：**

```json
{
  "table_name": "线上线索",
  "records": [
    {
      "姓名": "张三",
      "联系方式": "13800138000"
    },
    {
      "姓名": "李四",
      "联系方式": "13900139000"
    }
  ]
}
```

**返回字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | integer | 状态码 |
| `message` | string | 状态信息 |
| `data` | object | 响应数据（目前为空对象） |

---

### 6.2 更新 Record

> 更新单条数据表记录。

| 项目 | 内容 |
|------|------|
| **方法** | `PUT` |
| **路径** | `/data/records` |
| **认证** | Bearer Token |

**Header 参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `Emoo-User-Id` | string | 是 | 用户 open_id |

**Body 参数（JSON）：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `table_key` | string | 条件 | 表的系统标识，与 `table_name` 二选一 |
| `table_name` | string | 条件 | 表的显示名称，与 `table_key` 二选一 |
| `record_key` | string | 条件 | 记录标识（与 `record_title` 二选一，优先使用） |
| `record_title` | string | 条件 | 记录标题（依赖 title column，与 `record_key` 二选一） |
| `fields` | object | 是 | 需要更新的字段 key-value 对象 |

**请求示例：**

```json
{
  "table_name": "线上线索",
  "record_key": "rec_xxx",
  "fields": {
    "姓名": "李四",
    "联系方式": "13900139000"
  }
}
```

**返回字段：** 同 [6.1 新建 Record](#61-新建-record)。

---

### 6.3 批量更新 Record

> 批量更新多条数据表记录（最多 100 条）。

| 项目 | 内容 |
|------|------|
| **方法** | `POST` |
| **路径** | `/data/records/batch-update` |
| **认证** | Bearer Token |

**Header 参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `Emoo-User-Id` | string | 是 | 用户 open_id |

**Body 参数（JSON）：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `table_key` | string | 条件 | 表的系统标识，与 `table_name` 二选一 |
| `table_name` | string | 条件 | 表的显示名称，与 `table_key` 二选一 |
| `records` | array | 是 | 记录数组，每条含 `record_key`/`record_title` 和 `fields`，最多 100 条 |

**请求示例：**

```json
{
  "table_name": "线上线索",
  "records": [
    { "record_key": "rec_xxx", "fields": { "姓名": "李四" } },
    { "record_key": "rec_yyy", "fields": { "姓名": "王五" } }
  ]
}
```

**返回字段：** 同 [6.1 新建 Record](#61-新建-record)。

---

### 6.4 删除 Record

> 删除数据表记录（最多 100 条）。

| 项目 | 内容 |
|------|------|
| **方法** | `DELETE` |
| **路径** | `/data/records` |
| **认证** | Bearer Token |

**Header 参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `Emoo-User-Id` | string | 是 | 用户 open_id |

**Body 参数（JSON）：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `table_key` | string | 条件 | 表的系统标识，与 `table_name` 二选一 |
| `table_name` | string | 条件 | 表的显示名称，与 `table_key` 二选一 |
| `record_keys` | array | 是 | 记录标识数组，最多 100 条 |

**请求示例：**

```json
{
  "table_name": "线上线索",
  "record_keys": ["rec_xxx", "rec_yyy"]
}
```

**返回字段：** 同 [6.1 新建 Record](#61-新建-record)。

---

### 6.5 查询 Record 列表

> 查询数据表记录列表，支持分页、过滤和排序。

| 项目 | 内容 |
|------|------|
| **方法** | `POST` |
| **路径** | `/data/records/list` |
| **认证** | Bearer Token |

**Header 参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `Emoo-User-Id` | string | 是 | 用户 open_id |

**Body 参数（JSON）：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `table_key` | string | 条件 | 表的系统标识，与 `table_name` 二选一 |
| `table_name` | string | 条件 | 表的显示名称，与 `table_key` 二选一 |
| `page_size` | integer | 否 | 每页数量，最大 100，默认 20 |
| `current_page` | integer | 否 | 页码，从 1 开始，默认 1 |
| `filters` | array | 否 | 过滤条件数组，格式: `字段:操作符:值`（如 `["status:eq:active"]`） |
| `sort` | string | 否 | 排序（如 `created_at:desc`） |

**请求示例：**

```json
{
  "table_name": "线上线索",
  "page_size": 20,
  "current_page": 1,
  "filters": ["status:eq:active"],
  "sort": "created_at:desc"
}
```

**返回字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | integer | 状态码 |
| `message` | string | 状态信息 |
| `data.total` | integer | 总记录数 |
| `data.results` | array | 记录列表 |

---

### 6.6 创建表

> **状态：Developing** — 创建数据表，可同时指定初始列定义。

| 项目 | 内容 |
|------|------|
| **方法** | `POST` |
| **路径** | `/data/table` |
| **认证** | Bearer Token |

**Header 参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `Emoo-User-Id` | string | 是 | 用户 open_id |

**Body 参数（JSON）：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `table_name` | string | 是 | 表名称 |
| `extra` | object | 否 | 扩展元数据 |
| `columns` | array[ColumnDef] | 否 | 初始列定义数组 |

**ColumnDef 字段：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `column_name` | string | 是 | 列名称 |
| `type` | enum | 是 | 列类型：`string`/`number`/`boolean`/`date`/`time`/`datetime`/`reference`/`file`/`user`/`group`/`select` |
| `title_column` | boolean | 否 | 是否为标题列，默认 false |
| `multiple` | boolean | 否 | 是否多选，默认 false |
| `reference_table_key` | string | 否 | 关联表 key（reference 类型） |
| `options` | object | 否 | 列选项（select 类型） |
| `extra` | object | 否 | 扩展元数据 |

**请求示例：**

```json
{
  "table_name": "员工管理",
  "columns": [
    {"column_name": "姓名", "type": "string", "title_column": true},
    {"column_name": "年龄", "type": "number"},
    {"column_name": "部门", "type": "select", "options": {"options": [{"label": "技术部", "value": "1"}]}}
  ]
}
```

**返回字段：** `data` 为 TableWithColumns — `table_key`、`table_name`、`extra`、`column_count`、`record_count`、`created_at`、`updated_at`、`columns[]`

---

### 6.7 获取表列表

> **状态：Developing** — 分页获取数据表列表。

| 项目 | 内容 |
|------|------|
| **方法** | `GET` |
| **路径** | `/data/table` |
| **认证** | Bearer Token |

**Query 参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `page_size` | integer | 否 | 每页数量，默认 20，最大 100 |
| `current_page` | integer | 否 | 页码，默认 1 |

**返回字段：** 分页结构 + `data.results[]` 为 TableBrief — `table_key`、`table_name`、`extra`、`column_count`、`record_count`、`created_at`、`updated_at`

---

### 6.8 更新表

> **状态：Developing** — 更新表名称或扩展元数据。

| 项目 | 内容 |
|------|------|
| **方法** | `PUT` |
| **路径** | `/data/table` |
| **认证** | Bearer Token |

**Body 参数（JSON）：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `table_key` | string | 条件 | 表标识（与 `table_name` 二选一） |
| `table_name` | string | 条件 | 表名称（与 `table_key` 二选一） |
| `new_table_name` | string | 条件 | 新表名（与 `extra` 二选一） |
| `extra` | object | 条件 | 扩展元数据（与 `new_table_name` 二选一） |

**请求示例：**

```json
{
  "table_key": "tb_xxx",
  "new_table_name": "员工花名册"
}
```

---

### 6.9 删除表

> **状态：Developing** — 软删除数据表。

| 项目 | 内容 |
|------|------|
| **方法** | `DELETE` |
| **路径** | `/data/table` |
| **认证** | Bearer Token |

**Body 参数（JSON）：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `table_key` | string | 条件 | 表标识（与 `table_name` 二选一） |
| `table_name` | string | 条件 | 表名称（与 `table_key` 二选一） |

---

### 6.10 获取表详情

> **状态：Developing** — 获取表详情（含完整列信息）。

| 项目 | 内容 |
|------|------|
| **方法** | `GET` |
| **路径** | `/data/table` |
| **认证** | Bearer Token |

**Query 参数：** 与 [6.9 删除表](#69-删除表) 相同（`table_key`/`table_name` 二选一）

**返回字段：** `data` 为 TableWithColumns

---

### 6.11 添加列

> **状态：Developing** — 向数据表添加一列。

| 项目 | 内容 |
|------|------|
| **方法** | `POST` |
| **路径** | `/data/table/columns` |
| **认证** | Bearer Token |

**Body 参数（JSON）：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `table_key` | string | 条件 | 表标识（与 `table_name` 二选一） |
| `table_name` | string | 条件 | 表名称（与 `table_key` 二选一） |
| `column_name` | string | 是 | 列名称 |
| `type` | enum | 是 | 列类型（同创建表） |
| `title_column` | boolean | 否 | 是否为标题列 |
| `multiple` | boolean | 否 | 是否多选 |
| `reference_table_key` | string | 否 | 关联表 key |
| `options` | object | 否 | 列选项 |
| `extra` | object | 否 | 扩展元数据 |

**返回字段：** `data` 为 ColumnInfo — `column_key`、`column_name`、`type`、`table_key`、`title_column`、`multiple`、`order`、`reference_table_key`、`options`、`extra`

---

### 6.12 更新列

> **状态：Developing** — 更新列属性。

| 项目 | 内容 |
|------|------|
| **方法** | `PUT` |
| **路径** | `/data/table/columns` |
| **认证** | Bearer Token |

**Body 参数（JSON）：** `table_key`/`table_name`（二选一）+ `column_key`/`column_name`（二选一）+ 可选的 `new_column_name`/`extra`

---

### 6.13 删除列

> **状态：Developing** — 软删除列。

| 项目 | 内容 |
|------|------|
| **方法** | `DELETE` |
| **路径** | `/data/table/columns` |
| **认证** | Bearer Token |

**Body 参数（JSON）：** `table_key`/`table_name`（二选一）+ `column_key`/`column_name`（二选一）

---

## 7. 应用管理

### 7.1 获取应用列表

> 获取工作区所有应用及其文档组/文档数量概览。

| 项目 | 内容 |
|------|------|
| **方法** | `GET` |
| **路径** | `/apps` |
| **认证** | Bearer Token |

**返回字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | integer | 状态码 |
| `message` | string | 状态信息 |
| `data[].id` | integer | 应用记录 ID |
| `data[].ws_app_key` | string | 应用的 Ws App Key |
| `data[].title` | string | 应用名称 |
| `data[].doc_group_count` | integer | 文档组数量 |
| `data[].doc_count` | integer | 文档总数量 |

---

### 7.2 获取文档组列表

> 获取指定应用下的所有文档组（分页）。

| 项目 | 内容 |
|------|------|
| **方法** | `GET` |
| **路径** | `/app/{ws_app_key}/doc-groups` |
| **认证** | Bearer Token |

**Path 参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `ws_app_key` | string | 是 | 应用的 Ws App Key |

**Query 参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| `page_size` | integer | 否 | 每页数量，最大 200，默认 100 |
| `current_page` | integer | 否 | 页码，从 1 开始，默认 1 |

**返回字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | integer | 状态码 |
| `message` | string | 状态信息 |
| `data.total` | integer | 总数据量 |
| `data.results[].app_group_id` | string | 文档组在源应用中的 ID |
| `data.results[].app_group_name` | string | 文档组名称 |
| `data.results[].app_group_desc` | string | 文档组描述 |
| `data.results[].url` | string | 访问链接 |
| `data.results[].doc_count` | integer | 文档数量 |
| `data.results[].created_at` | string | 创建时间 |
| `data.results[].updated_at` | string | 更新时间 |

---

## 8. 数据模型

### 8.1 DocDetailInfo

文档详情信息。

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `id` | integer | 是 | EMOO 中文档的 ID（唯一） |
| `app_doc_id` | string | 是 | 文档在源应用中的 ID |
| `title` | string | 是 | 文档标题 |
| `url` | string | 否 | 文档访问链接（部分连接器可能为空） |
| `content_type` | string | 是 | 文档内容类型，枚举：`text` (文本)、`json` (JSON) |
| `content` | string | 否 | 文档内容。text 类型根据 `text_format` 返回纯文本或 markdown；json 类型返回嵌套 JSON 字符串 |
| `app_created_at` | string | 是 | 文档在源应用中的创建时间 |
| `app_updated_at` | string | 是 | 文档在源应用中的最近更新时间 |
| `ws_app` | object | 否 | 文档所属应用信息，见 [WsAppInfo](#86-wsappinfo) |
| `doc_group` | object | 否 | 文档所属文档组信息，见 [DocGroupInfo](#87-docgroupinfo) |

---

### 8.2 DocFilterCondition

文档过滤条件，用于 `/search` 和 `/data` 接口。

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `field` | string | 是 | 过滤字段（见下方枚举） |
| `operator` | string | 是 | 比较运算符（见下方枚举） |
| `value` | string | 是 | 比较值 |

**`field` 枚举值：**

| 值 | 说明 |
|------|------|
| `id` | 文档在 EMOO 中的 ID（唯一） |
| `app_doc_id` | 文档在源应用中的 ID（同一源应用内唯一，EMOO 中可能重复） |
| `doc_group.id` | EMOO 中的文档组 ID（唯一） |
| `doc_group.app_group_id` | 文档组在源应用中的 ID（源应用内唯一，EMOO 中可能重复） |
| `app_updated_at` | 文档在源应用中的更新时间 |
| `app_created_at` | 文档在源应用中的创建时间 |
| `ws_app.ws_app_key` | 应用的 Key |

**`operator` 枚举值：**

| 值 | 说明 |
|------|------|
| `eq` | 等于 |
| `neq` | 不等于 |
| `in` | 属于 |
| `nin` | 不属于 |
| `gte` | 大于等于 |
| `lte` | 小于等于 |

---

### 8.3 WsGroupBaseInfo

工作区角色/群组基础信息。

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `id` | integer | 是 | 群组 ID |
| `group_name` | string | 是 | 角色名称 |
| `workspace_id` | integer | 是 | 所属工作区 ID |
| `created_at` | string | 是 | 创建时间（ISO 8601 格式，如 `2024-09-09T01:28:35+00:00`） |
| `updated_at` | string | 是 | 更新时间 |
| `avatar_url` | string | 否 | 头像 URL |
| `group_desc` | string | 否 | 角色描述 |

---

### 8.4 WsUserDetailInfo

工作区成员详细信息。

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `open_id` | string | 是 | 成员在当前工作区中的唯一标识 |
| `user_id` | integer | 是 | 成员在用户系统中的唯一标识 |
| `workspace_id` | integer | 是 | 所属工作区 ID |
| `ws_user_type` | integer | 是 | 角色类型（见下方枚举） |
| `ws_username` | string | 是 | 工作区中的用户名 |
| `created_at` | string | 是 | 创建时间 |
| `updated_at` | string | 是 | 更新时间 |
| `ws_group_list` | array | 否 | 所属角色列表，元素为 [WsGroupBaseInfo](#83-wsgroupbaseinfo) |
| `email` | string | 否 | 邮箱 |
| `mobile_num` | string | 否 | 手机号 |
| `ext_info` | object | 否 | 扩展信息（含 `key` 字段） |

**`ws_user_type` 枚举：**

| 值 | 含义 |
|:--:|------|
| 1 | 普通成员 |
| 2 | 管理员 |
| 3 | 工作区拥有者 |

---

### 8.5 WsUserUpdate

更新成员信息的请求体元素。

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `open_id` | string | 是 | 成员在当前工作区中的唯一标识 |
| `ws_username` | string | 否 | 用户在工作区中显示的名称 |
| `ext_info` | object | 否 | 扩展信息（自由格式 key-value） |

---

### 8.6 WsAppInfo

应用信息。

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `id` | integer | 是 | 应用记录 ID |
| `title` | string | 是 | 应用名称 |
| `ws_app_key` | string | 是 | 应用的 Ws App Key |
| `app_id` | integer | 是 | 所属数据源的 ID |
| `app_name` | integer | 是 | 所属数据源名称（注：文档定义为 integer，实际返回应为 string） |

---

### 8.7 DocGroupInfo

文档组信息。

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `id` | integer | 是 | 文档组 ID |
| `app_group_id` | string | 是 | 文档组在源应用中的 ID（可用于筛选指定文档组数据） |
| `app_group_name` | string | 是 | 文档组名称 |
| `app_group_desc` | string | 否 | 文档组描述 |
| `url` | string | 否 | 访问链接 |

---

### 8.8 TableIdentifier

表标识 — 用于在所有 EMOO Base 接口中定位目标表。

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `table_key` | string | 条件 | 表系统标识（与 `table_name` 二选一） |
| `table_name` | string | 条件 | 表显示名称（与 `table_key` 二选一） |

---

### 8.9 TableBrief

表简要信息（列表返回）。

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `table_key` | string | 是 | 表系统标识 |
| `table_name` | string | 是 | 表名称 |
| `extra` | object | 否 | 扩展元数据 |
| `column_count` | integer | 是 | 列数量 |
| `record_count` | integer | 是 | 记录总数 |
| `created_at` | string | 是 | 创建时间 |
| `updated_at` | string | 是 | 更新时间 |

---

### 8.10 ColumnDef

列定义 — 创建表或添加列时使用。

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `column_name` | string | 是 | 列名称 |
| `type` | enum | 是 | 列类型：`string`/`number`/`boolean`/`date`/`time`/`datetime`/`reference`/`file`/`user`/`group`/`select` |
| `title_column` | boolean | 否 | 是否为标题列，默认 false |
| `multiple` | boolean | 否 | 是否多选，默认 false |
| `reference_table_key` | string | 否 | 关联表 key |
| `options` | object | 否 | 列选项 |
| `extra` | object | 否 | 扩展元数据 |

---

### 8.11 ColumnInfo

列详情信息（响应返回）。

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `column_key` | string | 是 | 列系统标识 |
| `column_name` | string | 是 | 列名称 |
| `type` | string | 是 | 列类型 |
| `table_key` | string | 是 | 所属表 key |
| `title_column` | boolean | 是 | 是否为标题列 |
| `multiple` | boolean | 是 | 是否多选 |
| `order` | integer | 否 | 排序序号 |
| `reference_table_key` | string | 否 | 关联表 key |
| `reference_table_name` | string | 否 | 关联表名称 |
| `options` | object | 否 | 列选项 |
| `extra` | object | 否 | 扩展元数据 |
| `created_at` | string | 是 | 创建时间 |
| `updated_at` | string | 是 | 更新时间 |

---

### 8.12 TableWithColumns

表详情（含完整列信息）。

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `table_key` | string | 是 | 表系统标识 |
| `table_name` | string | 是 | 表名称 |
| `extra` | object | 否 | 扩展元数据 |
| `column_count` | integer | 是 | 列数量 |
| `record_count` | integer | 是 | 记录总数 |
| `created_at` | string | 是 | 创建时间 |
| `updated_at` | string | 是 | 更新时间 |
| `columns` | array[ColumnInfo] | 否 | 列定义数组，元素见 [ColumnInfo](#811-columninfo) |

---

## 9. 全局错误码

所有接口在 `code` 字段中可能返回以下值：

| 错误码 | 说明 |
|:------:|------|
| `200` | 成功 |
| `4083` | OPEN API 提供的 API Token 无效 |
| `4084` | OPEN API 提供的 Emoo-User-Id 无效 |
| `4092` | 提供的 ws_agent_key 不存在 |
| `4044` | 对话消息不能为空 |

> **注意：** 所有错误码均在 HTTP 200 响应中通过 `code` 字段返回，不会使用 HTTP 4xx/5xx 状态码。

---

## 10. 通用说明

### 10.1 认证流程

1. 调用 `GET /auth/token` 获取 `access_token`，有效期 2 小时
2. 所有后续请求在 Header 中携带 `Authorization: Bearer <access_token>`
3. 涉及用户身份的接口需额外在 Header 中传入 `Emoo-User-Id`

### 10.2 分页方式

- **页码分页：** `/search`、`/ws-user`、`/chat`(GET) 使用 `current_page` + `page_size`
- **游标分页：** `/data` 使用 `cursor` + `page_size`

### 10.3 过滤条件语法

`filter_conditions` 是一个二维数组：
- **外层数组：** OR 逻辑（满足任意一组条件即返回）
- **内层数组：** AND 逻辑（需同时满足组内所有条件）

示例 — 查询"app_key 为 X 且更新时间在 2024 年之后"的文档：

```json
"filter_conditions": [
  [
    { "field": "ws_app.ws_app_key", "operator": "eq", "value": "X" },
    { "field": "app_updated_at", "operator": "gte", "value": "2024-01-01T00:00:00+08:00" }
  ]
]
```

### 10.4 数据安全

- 仅支持搜索企业绑定的数据源，不支持搜索个人绑定的数据源
- 同一用户在不同租户（企业）中的 `open_id` 不同

### 10.5 EMOO Base 字段类型与写入格式

通过 `record-create` / `record-update` 写入时，各字段类型需使用以下格式：

| 类型 | 写入格式 | 示例 | 返回格式 | 备注 |
|------|----------|------|----------|------|
| `string` | 字符串 | `"hello"` | `"hello"` | |
| `number` | 数字 | `123.45` | `123.45` | |
| `boolean` | 布尔 | `true` / `false` | `1` / `0` | 返回为整数 |
| `date` | 字符串 | `"2026-06-15"` | `"2026-06-15"` | YYYY-MM-DD |
| `time` | 字符串 | `"14:30:00"` | `"14:30:00"` | HH:MM:SS |
| `datetime` | 字符串 | `"2026-06-15 14:30:00"` | `"2026-06-15 14:30:00"` | |
| `select` | **简单值**（非数组） | `"a"` (option value) | `["选项A"]` (label 数组) | ⚠️ 不能用 `["a"]`，会报"选项值无效" |
| `reference` | **数组** | `["record_key"]` | `["record_key"]` | ⚠️ 必须用数组 |
| `user` | **数字** (user_id) | `123` | `[123]` | ⚠️ open_id 格式不支持，需用数字 ID |
| `group` | **数字** (group_id) | `1` | `[1]` | ⚠️ 需用数字 ID |
| `file` | 字符串 URL | `"https://..."` | `["https://..."]` | |

> **关键规则**: select 用裸值，reference 用数组，user/group 用数字 ID。select 与 reference 的格式不对称是最容易踩的坑。

---

## API 接口总览

| 分类 | 方法 | 路径 | 说明 | 状态 |
|------|:----:|------|------|:----:|
| 鉴权 | GET | `/auth/token` | 获取企业令牌 | Released |
| 通讯录 | GET | `/ws-user` | 获取通讯录成员 | Released |
| 通讯录 | PUT | `/ws-user` | 更新成员信息 | Released |
| 数据 | POST | `/search` | 搜索数据 | Released |
| 数据 | POST | `/data` | 获取数据 | Released |
| 对话 | GET | `/chat` | 获取用户对话列表 | Released |
| 对话 | POST | `/chat` | 创建对话 | Released |
| 对话 | POST | `/chat/messages` | 发送对话消息 | Released |
| 消息 | POST | `/message` | 主动推送消息给指定用户 | Released |
| EMOO Base | POST | `/data/records` | 新建 Record | Developing |
| EMOO Base | PUT | `/data/records` | 更新 Record | Developing |
| EMOO Base | POST | `/data/records/batch-update` | 批量更新 Record | Developing |
| EMOO Base | DELETE | `/data/records` | 删除 Record | Developing |
| EMOO Base | POST | `/data/records/list` | 查询 Record 列表 | Developing |
| EMOO Base | POST | `/data/table` | 创建表 | Developing |
| EMOO Base | GET | `/data/table` | 获取表列表 | Developing |
| EMOO Base | PUT | `/data/table` | 更新表 | Developing |
| EMOO Base | DELETE | `/data/table` | 删除表 | Developing |
| EMOO Base | GET | `/data/table` | 获取表详情 | Developing |
| EMOO Base | POST | `/data/table/columns` | 添加列 | Developing |
| EMOO Base | PUT | `/data/table/columns` | 更新列 | Developing |
| EMOO Base | DELETE | `/data/table/columns` | 删除列 | Developing |
| 应用管理 | GET | `/apps` | 获取应用列表 | Released |
| 应用管理 | GET | `/app/{ws_app_key}/doc-groups` | 获取文档组列表 | Released |

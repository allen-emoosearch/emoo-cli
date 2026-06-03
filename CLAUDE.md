# EMOO CLI

`emoo` is a command-line tool for the EMOO OpenAPI platform. It manages auth tokens automatically.

**CRITICAL:** This package is installed in non-editable mode. After any source code change,
you MUST run `pip install --force-reinstall .` from the project root, otherwise the
installed `emoo` command will still run the stale code.

## Prerequisites

- Config stored at `~/.emoo/config.json`
- Two auth modes: API Key (recommended, no `--user-id` needed) or OAuth2 (needs `--user-id`)
- All commands auto-refresh OAuth2 tokens 60s before expiry

## Quick reference

```
emoo auth login --api-key <key>                  # API Key 登录 (推荐)
emoo auth login [--client-id <id>]               # OAuth2 登录
emoo auth status                                  # 查看认证状态 + token 有效期
emoo auth set-default-user-id <open_id>          # 设置默认 User ID (OAuth2)

emoo api GET /v1/<path>                           # L3 通用透传 (覆盖 100% API)
emoo api POST /v1/<path> -d '<json>'              # L3 POST 透传 (body 支持 string/file/stdin)
emoo api PUT /v1/<path> -d '<json>'               # L3 PUT 透传
emoo api DELETE /v1/<path>                        # L3 DELETE 透传

emoo schema list                                  # 列出所有已知端点
emoo schema <endpoint>                            # 端点详情 (支持模糊匹配)
emoo schema data.search                           # 查看 search 的参数/body/响应/过滤

emoo app list                                     # 列出所有 ws_app_key (含文档数)
emoo app doc-groups -k <ws_app_key>              # 列出应用的文档组 (分页)
emoo app overview [--max-docs 500] [-o map.md]   # 遍历文档生成知识地图

emoo skill init                                   # 初始化 + 注册 symlink 到 Claude Code
emoo skill list [--category <c>] [--type <t>]     # 列出已安装的 skill
emoo skill show <name>                            # 显示 skill MD 内容
emoo skill run <name> [--params ...]              # 执行 skill 搜索
emoo skill create <name>                          # 创建 skill 脚手架
emoo skill register [--unregister]                # Claude Code 集成注册/取消
emoo skill pipeline knowledge-map                 # 生成增强知识图谱 (JSON + MD)
emoo skill pipeline intent "<query>"              # 意图分析 → 搜索方案
emoo skill pipeline search -p plan.json           # 执行搜索方案，聚合多 app

emoo contact list [--keyword <kw>] [--page-size 50] [--current-page 1]
emoo contact update <open_id> [--username <name>] [--ext-info '<json>']

emoo data search -k <keyword> [--page-size 20] [--current-page 1] [--text-format plain|markdown] [-f '<filter>'] [--max-results <N>]
emoo data get [--page-size 50] [--cursor <cursor>] [--text-format plain|markdown] [-f '<filter>'] [--max-results <N>]

emoo chat list [--page-size 50] [--current-page 1]
emoo chat create [--title <title>]
emoo chat send -q <query> [--chat-id <id>] [--ws-agent-key <key>] [--file-list "a,b"]

emoo message push -t normal|agent -c <content> [--from-title <t>] [--agent-key <k>] [--dry-run]

emoo base record-create --table-name <name> -r '<json-array>'
emoo base record-update --table-name <name> --record-key <key> -f '<json>'
emoo base record-batch-update --table-name <name> -r '<json-array>'
emoo base record-delete --table-name <name> -k '<json-array>'
emoo base record-list --table-name <name> [-f <filter>] [--sort <sort>] [--page-size 20]
emoo base table-create -n <name> [--columns '<json>'] [--extra '<json>']
emoo base table-list [--page-size 20]
emoo base table-update [--table-key <key>] [--new-table-name <name>]
emoo base table-delete [--table-key <key>]
emoo base table-get [--table-key <key>]
emoo base column-add [--table-key <key>] -n <name> -t <type> [--options]
emoo base column-update [--table-key <key>] [--column-key <key>]
emoo base column-delete [--table-key <key>] [--column-key <key>]
```

## Global flags

| Flag | Effect |
|------|--------|
| `--json` | Output raw JSON on stdout; all progress/errors on stderr |
| `--user-id <id>` | Set `Emoo-User-Id` header (OAuth2 mode) |
| `--base-url <url>` | Override API base URL |

Env vars: `EMOO_USER_ID`, `EMOO_BASE_URL`, `EMOO_API_KEY`, `EMOO_CLIENT_ID`, `EMOO_CLIENT_SECRET`.

## Architecture: Three-layer command model

```
L3 api       GET/POST/PUT/DELETE /v1/...    一条命令覆盖 100% API，零等待
L2 commands  data search / chat send / ...  结构化命令，参数校验，Rich 表格
L1 skill     skill run <name> / pipeline    MD 驱动，智能默认值，Claude Code 集成
```

### Agent-native contracts

- **stdout = data, stderr = progress/errors** — `--json` 模式下绝不混合
- **Structured errors** — every error extends `EmooError` with a `hint` field telling agents how to fix
- **Schema introspection** — `emoo schema <endpoint>` to look up params before calling
- **Dry-run** — `--dry-run` on side-effect commands (chat send, message push, base write, api POST/PUT/DELETE)

## Auth flow

### API Key (recommended)

```bash
emoo auth login --api-key emoo_xxx
```

- API Key is used directly as `Bearer` token
- No `Emoo-User-Id` header needed
- No expiry, no refresh needed

### OAuth2

1. `emoo auth login --client-id <id> --client-secret <secret>`
   - Credentials + token saved to `~/.emoo/config.json`
   - Token auto-refreshes 60s before expiry
   - Auto-retry on 4083: refresh token and replay once
2. Every command needs `--user-id <open_id>` (or `EMOO_USER_ID` env var)

## Common patterns

### L3 passthrough — call any endpoint without waiting for a command wrapper

```bash
emoo api GET /v1/apps
emoo api POST /v1/search -d '{"keyword":"test","page_size":5,"current_page":1}'
emoo api POST /v1/search -d ./body.json          # from file
echo '{"keyword":"test"}' | emoo api POST /v1/search -d -  # from stdin
emoo api POST /v1/chat/messages -d '{"query":"hi"}' --dry-run
```

### Schema introspection — look up before calling, don't guess fields

```bash
emoo schema list               # all endpoints
emoo schema data.search        # params, body, response, filter fields/operators
emoo schema search             # fuzzy match ("search" → "data.search")
emoo --json schema data.search # machine-readable for agents
```

### Search with filter conditions

Filter conditions use 2D array: outer=OR, inner=AND.

```bash
emoo data search -k "报告" -f '[[{"field":"ws_app.ws_app_key","operator":"eq","value":"abc123"}]]'

# From file
echo '[{"field":"app_updated_at","operator":"gte","value":"2024-01-01"}]' > /tmp/f.json
emoo data search -k "报告" -f /tmp/f.json

# Short form (auto-wrapped)
emoo data search -k "报告" -f '{"field":"ws_app.ws_app_key","operator":"eq","value":"abc123"}'
```

### Auto-pagination and the 500-record cap

`/search` has a **hard 500-record cap** that auto-pagination cannot break. `/data` (cursor-based) has **no hard cap**.

Without `--max-results`, if search results hit 500, CLI warns on stderr:

```
⚠ 结果可能不完整: API 单次上限 500 条，当前已返回 200 条。
```

With `--max-results <N>` on `data search`, CLI auto-paginates but still caps at 500, and warns:

```
⚠ 结果可能不完整: search 端点硬上限 500 条，自动翻页也无法突破。
  建议: 用 emoo data get (游标翻页无此限制) 配合日期过滤分段拉取。
```

For >500 records, always use `data get` with `--max-results`:

```bash
# search — 500 hard cap, set _truncated=true when hit
emoo data search -k "上海" --max-results 2000

# data get — cursor-based, no hard cap, truly paginates to exhaustion
emoo data get -f '<filter>' --max-results 10000
```

### Dry-run — preview without executing

```bash
emoo chat send -q "你好" --dry-run
emoo message push -t normal -c "通知" --from-title "test" --dry-run
emoo api POST /v1/chat/messages -d '{"query":"hi"}' --dry-run
```

### Skill pipeline — adaptive multi-app search

```bash
emoo skill pipeline knowledge-map --max-doc-groups 200 -o /tmp/km
emoo skill pipeline intent "示例门店店3月营收"
emoo skill pipeline search -p plan.json --csv output.csv
```

## File structure

```
src/
  cli.py                    # Entry point, EmooError catcher, --json flag
  client.py                 # EmooClient — auth, auto-refresh, retry, request()
  errors.py                 # EmooError hierarchy (Auth, Permission, NotFound, Validation, Server)
  formatters.py             # Rich table / JSON output helpers
  commands/
    auth.py                 # auth login / status / set-default-user-id
    api.py                  # L3 passthrough (GET/POST/PUT/DELETE)
    schema_cmd.py           # schema list / <endpoint> introspection
    endpoints.json          # 12 endpoint schemas (method, path, params, body, response)
    data.py                 # data search / get
    chat.py                 # chat list / create / send (with --dry-run)
    message.py              # message push (with --dry-run)
    contact.py              # contact list / update
    app.py                  # app overview / list / doc-groups
    skill.py                # skill init/list/show/run/create/register + pipeline sub-group
    base_cmd.py             # base record-create/update/batch-update/delete/list
  skills/
    loader.py               # MD skill parser (YAML frontmatter)
    runner.py               # Skill executor (template → app resolve → search → CSV)
    registry.py             # Claude Code symlink registration
    knowledge_map.py         # Pipeline: generate knowledge map
    intent.py               # Pipeline: intent analysis
    search.py               # Pipeline: execute search plan
```

## Error codes

### Business error codes (HTTP 200 + code field)

| Code | Class | Meaning |
|:----:|-------|---------|
| 200 | — | Success |
| 4083 | AuthError | Invalid API Token — re-run `emoo auth login` |
| 4084 | AuthError | Invalid Emoo-User-Id |
| 4008 | NotFoundError | App does not exist |
| 4042 | PermissionError | No permission to access this app |
| 4092 | NotFoundError | ws_agent_key does not exist |
| 4044 | ValidationError | Message/chat content is empty |
| 4133 | NotFoundError | Table does not exist |

### HTTP status codes

| Status | Class | Meaning |
|:------:|-------|---------|
| 400 | ValidationError | Bad request parameters |
| 401 | AuthError | Authentication failed |
| 403 | PermissionError | No permission |
| 404 | NotFoundError | Resource not found |
| 500 | ServerError | Internal server error |

Every error carries a `hint` field with actionable fix instructions for AI agents.

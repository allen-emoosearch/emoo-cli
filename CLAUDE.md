# EMOO CLI

`emoo` is a command-line tool for the EMOO OpenAPI platform. It manages auth tokens automatically.

## Prerequisites

- Config stored at `~/.emoo/config.json`
- Before any data/chat/contact commands, the user must:
  1. Run `emoo auth login` to store client credentials and get a token
  2. Know their `Emoo-User-Id` (open_id) for the target tenant

## Quick reference

```
emoo auth login          # store client_id/client_secret, fetch token
emoo auth status         # show token expiry / config

emoo contact list [--keyword <kw>] [--page-size 50] [--current-page 1]
emoo contact update <open_id> [--username <name>] [--ext-info '<json>']

emoo data search -k <keyword> [--text-format plain|markdown] [--ws-agent-key <key>] [-f '<filter-json>']
emoo data get [--page-size 50] [--cursor <cursor>] [-f '<filter-json>']

emoo chat list [--page-size 50] [--current-page 1]
emoo chat create [--title <title>]
emoo chat send -q <query> [--chat-id <id>] [--ws-agent-key <key>] [--file-list "a,b"]

emoo message push -t normal|agent -c <content> [--from-title <t>] [--agent-key <k>]

emoo base record-create --table-name <name> -r '<json-array>'
```

## Global flags

| Flag | Effect |
|------|--------|
| `--json` | Output raw JSON instead of rich tables |
| `--user-id <id>` | Set `Emoo-User-Id` header for this call |
| `--base-url <url>` | Override API base URL (default: `https://app.emoosearch.com/open-api/v1`) |

All three can also be set via environment variables: `EMOO_USER_ID`, `EMOO_BASE_URL`.

## Auth flow (critical)

1. User calls `emoo auth login --client-id <id> --client-secret <secret>`
   - This stores credentials + fetched token in `~/.emoo/config.json`
   - Token auto-refreshes 60s before expiry on any subsequent call
2. Every other command requires `--user-id <open_id>` (or `EMOO_USER_ID` env var)
   - This is the `open_id` of the user whose identity the API call runs under
   - The same user in different tenants has different `open_id`s

## Common patterns

### Search with filter conditions

Filter conditions use 2D array: outer=OR, inner=AND.

```
emoo data search -k "报告" --user-id <id> -f '[[{"field":"ws_app.ws_app_key","operator":"eq","value":"abc123"}]]'
```

Loading filters from file (pipe JSON in):
```
echo '[{"field":"app_updated_at","operator":"gte","value":"2024-01-01"}]' > /tmp/f.json
emoo data search -k "报告" --user-id <id> -f /tmp/f.json
```

### Send a chat message
```
emoo chat send -q "总结一下上周的销售数据" --user-id <id> --chat-id 42
```

### Push a normal notification
```
emoo message push -t normal -c "审批已通过" --user-id <id> --from-title "OA系统"
```

### Push an agent message
```
emoo message push -t agent -c "您好，我是AI助手" --user-id <id> --agent-key <ws_agent_key>
```

## Error codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 4083 | Invalid API Token — re-run `emoo auth login` |
| 4084 | Invalid Emoo-User-Id |
| 4092 | ws_agent_key does not exist |
| 4044 | Message content is empty |

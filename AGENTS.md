# AGENTS.md — EMOO CLI 贡献者规约

给 AI Agent 和贡献者的统一规范。

## 架构原则

- **三层命令模型**: L3 透传 (`emoo api`) → L2 生成命令 (手写) → L1 快捷命令 (skill)
- **stdout=数据, stderr=进度/错误**: `--json` 模式下绝不混入 — 所有进度消息用 `_progress()` 写 stderr
- **错误必须结构化**: 每条错误继承 `EmooError`，带 `hint` 字段告诉调用者怎么修
- **先查再调**: 用 `emoo schema <endpoint>` 查参数，不要猜字段
- **副作用可预览**: `--dry-run` 在 chat send / message push / base write / api POST

## 代码风格

```
src/
  cli.py                    # main() 入口，EmooError 捕获，--json 全局标志
  client.py                 # EmooClient — OAuth2/API Key 双认证，auto-refresh，retry
  errors.py                 # EmooError 类层级 (Auth, Permission, NotFound, Validation, Server)
  formatters.py             # output() — Rich 表格 / JSON 自适应
  commands/
    auth.py                 # login / status / set-default-user-id
    api.py                  # L3 透传: GET/POST/PUT/DELETE，body 支持 string/file/stdin
    schema_cmd.py           # schema 自省: list + 端点详情 + 模糊匹配
    endpoints.json          # 16 端点 schema (method, path, params, body, response)
    data.py                 # search + get
    chat.py                 # list / create / send (--dry-run)
    message.py              # push (--dry-run)
    contact.py              # list / update
    app.py                  # overview / list / doc-groups (overview 支持 --json)
    skill.py                # init/list/show/run/create/register + pipeline 子组
    base_cmd.py             # record-create/update/batch-update/delete/list
  skills/
    loader.py               # MD skill 解析 (YAML frontmatter)
    runner.py               # Skill 执行 (模板→app 匹配→搜索→CSV)
    registry.py             # Claude Code symlink 注册
    knowledge_map.py         # Pipeline: 扫描工作区生成知识图谱
    intent.py               # Pipeline: 自然语言意图分析
    search.py               # Pipeline: 执行搜索方案聚合多 app 结果
```

## 关键约束

- **安装模式**: 非 editable 安装，改源码后必须 `pip install --force-reinstall .`
- **错误处理**: 使用 `from_api_response()` 构建错误，AI Agent 依赖 `hint` 字段自愈
- **API 端点**: 文档在 `EMOO_OpenAPI_Documentation.md`，schema 在 `src/commands/endpoints.json`
- **进度消息**: 所有进度/信息类消息必须通过 `_progress()` 写 stderr，不能直接 `click.echo()`
- **JSON 模式**: 每个命令必须检查 `ctx.obj.get("as_json")`，输出结构化 JSON 到 stdout

## 测试

- 多租户测试: API Key 模式 + OAuth2 模式，覆盖不同自定义域名
- 配置切换: 通过 `~/.emoo/config.json` 切换不同工作区进行回归测试
- 每个命令验证: 正常调用、`--json` 输出、`--dry-run` 预览、错误场景

## 提交规范

- 格式: `type: 中文描述`
- 类型: feat, fix, docs, refactor
- Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>

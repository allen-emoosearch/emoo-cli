# AGENTS.md — EMOO CLI 贡献者规约

给 AI Agent 和贡献者的统一规范。

## 架构原则

- **三层命令模型**: L3 透传 (`emoo api`) → L2 生成命令 (手写) → L1 快捷命令 (skill)
- **stdout=数据, stderr=进度/错误**: JSON 模式下绝不混入
- **错误必须结构化**: 每条错误带 `hint` 告诉调用者怎么修
- **先查再调**: 用 `emoo schema <endpoint>` 查参数，不要猜字段

## 代码风格

- `src/client.py` — API 客户端 (鉴权、重试、错误映射)
- `src/errors.py` — 结构化错误层级
- `src/commands/` — Click 命令组，按业务域分文件
- `src/skills/` — Skill 系统 (loader, runner, registry, pipeline)

## 关键约束

- **安装模式**: 本包为非 editable 安装，改源码后必须 `pip install --force-reinstall .`
- **错误处理**: 使用 `from_api_response()` 构建错误，AI Agent 依赖 hint 字段
- **API 端点**: 文档在 `EMOO_OpenAPI_Documentation.md`，schema 在 `src/commands/endpoints.json`

## 测试

- 多租户测试: 轻流 (qingflow) + 煲仔皇 (baozaihuang)
- 每个命令至少验证: 正常调用、JSON 输出、错误场景

## 提交规范

- 格式: `type: 中文描述`
- 类型: feat, fix, docs, refactor
- Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>

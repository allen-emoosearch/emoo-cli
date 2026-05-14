# emoo-cli

EMOO 开放平台命令行工具，支持鉴权、通讯录、数据搜索、对话、消息推送等全部 OpenAPI 接口。

## 安装

```bash
# 方式一：pip 直接安装
pip install git+https://github.com/<your-username>/emoo-cli.git

# 方式二：克隆后安装
git clone https://github.com/<your-username>/emoo-cli.git
cd emoo-cli
pip install .
```

## 快速开始

```bash
# 1. 登录获取 Token
emoo auth login --client-id <your-client-id> --client-secret <your-client-secret>

# 2. 搜索数据
emoo data search -k "关键词" --user-id <open_id>

# 3. 发送对话
emoo chat send -q "你好" --user-id <open_id>

# 4. 查看所有命令
emoo --help
```

## 环境变量

| 变量 | 说明 |
|------|------|
| `EMOO_CLIENT_ID` | 客户端 ID |
| `EMOO_CLIENT_SECRET` | 客户端密钥 |
| `EMOO_USER_ID` | 默认 Emoo-User-Id |
| `EMOO_BASE_URL` | API 地址 (默认 `https://app.emoosearch.com/open-api/v1`) |

## 命令列表

| 命令 | 说明 |
|------|------|
| `emoo auth login` | 登录获取 Token |
| `emoo auth status` | 查看 Token 状态 |
| `emoo contact list` | 获取通讯录成员 |
| `emoo contact update` | 更新成员信息 |
| `emoo data search` | 搜索数据 |
| `emoo data get` | 获取数据 (游标分页) |
| `emoo chat list` | 获取对话列表 |
| `emoo chat create` | 创建对话 |
| `emoo chat send` | 发送对话消息 |
| `emoo message push` | 推送消息 |
| `emoo base record-create` | 新建 Record |

## 输出格式

默认使用表格美化输出，添加 `--json` 输出原始 JSON：

```bash
emoo data search -k "报告" --user-id xxx --json
```

## 过滤条件

`-f` 参数支持 JSON 字符串或文件路径，外层数组 OR，内层数组 AND：

```bash
# 直接传 JSON
emoo data search -k "报告" -f '[[{"field":"ws_app.ws_app_key","operator":"eq","value":"abc"}]]'

# 从文件读取
emoo data search -k "报告" -f ./filter.json
```

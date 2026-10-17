#!/usr/bin/env python3
"""Sync EMOO OpenAPI docs from open.emooai.com.

The docs site exposes an llms.txt index plus one Markdown file per endpoint.
Each Markdown file embeds an OpenAPI YAML fragment. This script merges those
fragments into a single spec and regenerates src/commands/endpoints.json.

Usage:
    python scripts/sync_api_docs.py                # fetch + regenerate
    python scripts/sync_api_docs.py --check        # exit 1 if registry differs
    python scripts/sync_api_docs.py --offline      # reuse cached markdown

Requires PyYAML (dev-only):  pip install pyyaml
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("需要 PyYAML: pip install pyyaml")

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "src" / "commands" / "endpoints.json"
SPEC_OUT = ROOT / "docs" / "openapi.json"
CACHE_DIR = ROOT / ".cache" / "emoo-docs"

LLMS_URL = "https://open.emooai.com/llms.txt"
LINK_RE = re.compile(r"\((https://open\.emooai\.com/[^)]+\.md)\)")
YAML_RE = re.compile(r"```yaml\s*\n(.*?)\n```", re.S)

# CLI registry key for every live operation. Keys are stable API for agents
# (emoo schema <key>), so keep them even when paths or operationIds change.
KEY_MAP: dict[tuple[str, str], str] = {
    # auth / app / agent
    ("GET", "/auth/token"): "auth.token",
    ("GET", "/apps"): "app.list",
    ("GET", "/app/{ws_app_key}/doc-groups"): "app.doc-groups",
    ("GET", "/agents"): "agent.list",
    ("POST", "/agents"): "agent.create",
    ("GET", "/agents/{ws_agent_key}"): "agent.get",
    ("PATCH", "/agents/{ws_agent_key}"): "agent.update",
    ("DELETE", "/agents/{ws_agent_key}"): "agent.delete",
    # chat
    ("GET", "/chat"): "chat.list",
    ("POST", "/chat"): "chat.create",
    ("POST", "/chat/messages"): "chat.send",
    ("POST", "/chat/agent-messages"): "chat.agent-message",
    # contact / role
    ("GET", "/ws-user"): "contact.list",
    ("PUT", "/ws-user"): "contact.update",
    ("POST", "/ws-user/batch-get"): "contact.batch-get",
    ("GET", "/ws-groups"): "role.list",
    ("POST", "/ws-groups"): "role.create",
    ("PATCH", "/ws-groups/{ws_group_id}"): "role.update",
    ("DELETE", "/ws-groups/{ws_group_id}"): "role.delete",
    ("GET", "/ws-groups/{ws_group_id}/members"): "role.members-list",
    ("POST", "/ws-groups/{ws_group_id}/members"): "role.members-add",
    ("DELETE", "/ws-groups/{ws_group_id}/members/{open_id}"): "role.members-remove",
    ("POST", "/ws-groups/batch-get"): "role.batch-get",
    # search / data
    ("POST", "/search"): "data.search",
    ("POST", "/data"): "data.get",
    ("POST", "/search/aggregate"): "data.aggregate",
    # file
    ("POST", "/data/files/upload-credentials"): "file.credentials",
    ("POST", "/data/files/confirm"): "file.confirm",
    ("GET", "/data/files/download-url"): "file.download-url",
    ("POST", "/data/files/extract-content"): "file.extract",
    ("POST", "/data/kb-file"): "file.register",
    ("DELETE", "/data/kb-file"): "file.delete",
    ("GET", "/data/kb-file/{doc_key}/permission"): "file.permission-get",
    ("PUT", "/data/kb-file/{doc_key}/permission"): "file.permission-set",
    # folder
    ("GET", "/data/folder/items"): "folder.list",
    ("POST", "/data/folder"): "folder.create",
    ("PUT", "/data/folder"): "folder.update",
    ("DELETE", "/data/folder"): "folder.delete",
    # message
    ("POST", "/message"): "message.push",
    ("POST", "/message/batch"): "message.batch",
    ("POST", "/message/status"): "message.status",
    ("POST", "/message/status/query"): "message.status-query",
    # base records
    ("POST", "/data/records"): "base.record-create",
    ("PUT", "/data/records"): "base.record-update",
    ("POST", "/data/records/batch-update"): "base.record-batch-update",
    ("DELETE", "/data/records"): "base.record-delete",
    ("POST", "/data/records/list"): "base.record-list",
    # base tables / columns / permissions
    ("POST", "/data/table"): "base.table-create",
    ("GET", "/data/table"): "base.table-list",
    ("PUT", "/data/table"): "base.table-update",
    ("DELETE", "/data/table"): "base.table-delete",
    ("GET", "/data/table/detail"): "base.table-get",
    ("POST", "/data/table/columns"): "base.column-add",
    ("PUT", "/data/table/columns"): "base.column-update",
    ("DELETE", "/data/table/columns"): "base.column-delete",
    ("GET", "/data/table/{table_key}/permissions"): "base.permission-list",
    ("POST", "/data/table/{table_key}/permissions"): "base.permission-create",
    ("PUT", "/data/table/{table_key}/permissions/{role_key}"): "base.permission-update",
    ("DELETE", "/data/table/{table_key}/permissions/{role_key}"): "base.permission-delete",
    # work items (CLI group: todo)
    ("GET", "/work_item"): "todo.list",
    ("POST", "/work_item"): "todo.create",
    ("PUT", "/work_item/{item_id}"): "todo.update",
    ("DELETE", "/work_item/{item_id}"): "todo.delete",
    ("GET", "/work_item/tags"): "todo.tag-list",
    ("POST", "/work_item/tags"): "todo.tag-create",
    ("PUT", "/work_item/tags/{tag_id}"): "todo.tag-update",
    ("DELETE", "/work_item/tags/{tag_id}"): "todo.tag-delete",
    ("POST", "/work_item/tags/order"): "todo.tag-reorder",
    # shortcuts
    ("GET", "/shortcut"): "shortcut.list",
    ("POST", "/shortcut"): "shortcut.create",
    ("PUT", "/shortcut/{shortcut_id}"): "shortcut.update",
    ("DELETE", "/shortcut/{shortcut_id}"): "shortcut.delete",
    ("POST", "/shortcut/order"): "shortcut.reorder",
}

DESCRIPTION_OVERRIDES = {
    ("POST", "/message"): "推送消息并落工作项（normal/agent；thread_key 幂等，due_at 截止时间）",
}

AUTH_FREE = {("GET", "/auth/token")}
# Service-to-service endpoints where Emoo-User-Id is optional.
USER_ID_OPTIONAL = {
    ("POST", "/message"),
    ("POST", "/message/batch"),
    ("POST", "/message/status"),
    ("POST", "/message/status/query"),
    ("POST", "/chat/agent-messages"),
}


def fetch(url: str, retries: int = 3) -> str:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "emoo-cli-docs-sync/1.0"})
            with urllib.request.urlopen(req, timeout=40) as resp:
                return resp.read().decode("utf-8", "ignore")
        except Exception as exc:  # noqa: BLE001 - retry all transient failures
            last = exc
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"下载失败 {url}: {last}")


def fetch_all_markdown(offline: bool) -> list[str]:
    if offline:
        files = sorted(CACHE_DIR.glob("*.md"))
        if not files:
            sys.exit(f"--offline 需要缓存文件: {CACHE_DIR}")
        return [p.read_text(encoding="utf-8") for p in files]

    llms = fetch(LLMS_URL)
    links = sorted(set(LINK_RE.findall(llms)))
    if not links:
        sys.exit("llms.txt 中未找到 .md 链接")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def one(url: str) -> str:
        name = url.rsplit("/", 1)[-1]
        path = CACHE_DIR / name
        if path.exists() and path.stat().st_size > 50:
            return path.read_text(encoding="utf-8")
        text = fetch(url)
        path.write_text(text, encoding="utf-8")
        return text

    with ThreadPoolExecutor(max_workers=6) as pool:
        docs = list(pool.map(one, links))
    print(f"已抓取 {len(docs)} 份 Markdown 文档 -> {CACHE_DIR}", file=sys.stderr)
    return docs


def extract_yaml(text: str) -> dict | None:
    match = YAML_RE.search(text)
    if not match:
        return None
    try:
        doc = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        print(f"  ⚠ YAML 解析失败: {exc}", file=sys.stderr)
        return None
    return doc if isinstance(doc, dict) else None


def merge_specs(docs: list[str]) -> dict:
    merged: dict = {
        "openapi": "3.0.3",
        "info": {
            "title": "EMOO 开放平台 OpenAPI",
            "version": "2026-10-17",
            "description": "由 scripts/sync_api_docs.py 从 open.emooai.com 自动合并生成。",
        },
        "servers": [
            {"url": "https://app.emooai.com/open-api/v1", "description": "SaaS 生产"},
        ],
        "paths": {},
        "components": {"schemas": {}},
    }
    api_paths = 0
    for doc in docs:
        for path, item in (doc.get("paths") or {}).items():
            api_paths += 1
            target = merged["paths"].setdefault(path, {})
            item = dict(item or {})
            path_params = item.pop("parameters", None)
            for method, op in item.items():
                if method.lower() not in ("get", "post", "put", "patch", "delete"):
                    continue
                op = dict(op or {})
                if path_params and not op.get("parameters"):
                    op["parameters"] = path_params
                target[method.lower()] = op
        schemas = ((doc.get("components") or {}).get("schemas") or {})
        merged["components"]["schemas"].update(schemas)
    print(f"合并完成: {len(merged['paths'])} 个路径 / "
          f"{sum(len(v) for v in merged['paths'].values())} 个操作 / "
          f"{len(merged['components']['schemas'])} 个 schema", file=sys.stderr)
    return merged


def resolve(schema, spec: dict, seen: set[str] | None = None) -> dict:
    """Resolve $ref / allOf into a flat-ish schema dict."""
    if not isinstance(schema, dict):
        return {}
    if "$ref" in schema:
        name = schema["$ref"].split("/")[-1]
        if seen is None:
            seen = set()
        if name in seen:
            return {}
        return resolve(spec["components"]["schemas"].get(name, {}), spec, seen | {name})
    if "allOf" in schema:
        out: dict = {}
        for sub in schema["allOf"]:
            resolved = resolve(sub, spec, seen)
            out.setdefault("properties", {}).update(resolved.get("properties") or {})
            out.setdefault("required", [])
            out["required"].extend(resolved.get("required") or [])
            for key in ("type", "description", "enum"):
                if key in resolved and key not in out:
                    out[key] = resolved[key]
        for key, value in schema.items():
            if key != "allOf" and key not in out:
                out[key] = value
        return out
    return schema


def schema_type(schema, spec: dict) -> str:
    schema = resolve(schema, spec)
    if "oneOf" in schema or "anyOf" in schema:
        branches = schema.get("oneOf") or schema.get("anyOf") or []
        types = {schema_type(b, spec) for b in branches}
        types.discard("any")
        if len(types) == 1:
            return next(iter(types))
        if types:
            return "|".join(sorted(types))
    typ = schema.get("type")
    if isinstance(typ, list):
        typ = "|".join(t for t in typ if t != "null") or "null"
    if not typ:
        if "properties" in schema:
            typ = "object"
        elif "items" in schema:
            typ = "array"
        elif "enum" in schema:
            typ = "string"
        else:
            typ = "any"
    if typ == "array":
        item = resolve(schema.get("items") or {}, spec)
        item_type = item.get("type")
        if item_type:
            typ = f"array[{item_type}]"
        else:
            typ = "array"
    return typ


def collect_properties(schema, spec: dict) -> tuple[dict, dict[str, bool | str]]:
    """Return top-level properties + required flags.

    For oneOf/anyOf branches, a field required in every branch is True,
    required in some branches is "条件", otherwise False.
    """
    schema = resolve(schema, spec)
    props: dict = {}
    required: dict[str, bool | str] = {}
    branches = schema.get("oneOf") or schema.get("anyOf")
    if branches:
        branch_results = [collect_properties(branch, spec) for branch in branches]
        counts: dict[str, int] = {}
        for bprops, breq in branch_results:
            for name, sub in bprops.items():
                if name not in props:
                    props[name] = sub
                    continue
                # Merge enums from multiple oneOf branches (e.g. normal/agent).
                merged = dict(props[name])
                enums: list = []
                for sch in (props[name], sub):
                    enums.extend(resolve(sch, spec).get("enum") or [])
                if enums:
                    merged["enum"] = list(dict.fromkeys(enums))
                props[name] = merged
            for name, flag in breq.items():
                if flag:
                    counts[name] = counts.get(name, 0) + 1
        for name in props:
            hits = counts.get(name, 0)
            required[name] = True if hits == len(branches) else ("条件" if hits else False)
        return props, required
    props.update(schema.get("properties") or {})
    req_names = set(schema.get("required") or [])
    for name in props:
        required[name] = name in req_names
    return props, required


def field_desc(schema, spec: dict, explicit: str = "") -> str:
    schema = resolve(schema, spec)
    desc = (explicit or schema.get("description") or "").strip().replace("\n", " ")
    if "enum" in schema:
        desc = f"{desc} 可选值: {', '.join(map(str, schema['enum']))}".strip()
    if "minimum" in schema:
        desc = f"{desc} 最小: {schema['minimum']}".strip()
    if "maxItems" in schema:
        desc = f"{desc} 最多: {schema['maxItems']} 项".strip()
    if "maxLength" in schema:
        desc = f"{desc} 最长: {schema['maxLength']}".strip()
    return desc[:220]


def param_desc(param: dict, spec: dict) -> str:
    return field_desc(param.get("schema") or {}, spec, param.get("description") or "")


def build_entry(method: str, path: str, op: dict, spec: dict) -> dict:
    params = op.get("parameters") or []
    path_params, query_params = [], []
    for raw in params:
        param = resolve(raw, spec)
        location = param.get("in")
        if location == "header":
            continue
        target = path_params if location == "path" else query_params
        if location not in ("path", "query"):
            continue
        target.append({
            "name": param.get("name", ""),
            "type": schema_type(param.get("schema") or {}, spec),
            "required": bool(param.get("required")),
            "desc": param_desc(param, spec),
        })

    body: list[dict] = []
    request_body = resolve(op.get("requestBody") or {}, spec)
    content = request_body.get("content") or {}
    body_schema = None
    for media_type, media in content.items():
        if "json" in media_type or media_type == "*/*":
            body_schema = media.get("schema")
            break
    if body_schema is None and content:
        body_schema = next(iter(content.values())).get("schema")
    if body_schema:
        props, required = collect_properties(body_schema, spec)
        for name, sub in props.items():
            body.append({
                "name": name,
                "type": schema_type(sub, spec),
                "required": required.get(name, False),
                "desc": field_desc(sub, spec),
            })

    response: dict[str, str] = {}
    resp = (op.get("responses") or {}).get("200") or {}
    for media_type, media in (resp.get("content") or {}).items():
        data_schema = None
        props, _ = collect_properties(media.get("schema") or {}, spec)
        if "data" in props:
            data_schema = props["data"]
        if data_schema is None:
            continue
        data_schema = resolve(data_schema, spec)
        if data_schema.get("type") == "array" or "items" in data_schema:
            item = resolve(data_schema.get("items") or {}, spec)
            iprops = item.get("properties") or {}
            for name, sub in iprops.items():
                desc = field_desc(sub, spec)
                response[f"data[].{name}"] = f"{schema_type(sub, spec)}" + (f" — {desc}" if desc else "")
        else:
            dprops = data_schema.get("properties") or {}
            for name, sub in dprops.items():
                resolved_sub = resolve(sub, spec)
                desc = field_desc(sub, spec)
                response[f"data.{name}"] = f"{schema_type(sub, spec)}" + (f" — {desc}" if desc else "")
                if name == "results" and ("items" in resolved_sub):
                    item = resolve(resolved_sub.get("items") or {}, spec)
                    for iname, isub in (item.get("properties") or {}).items():
                        idesc = field_desc(isub, spec)
                        response[f"data.results[].{iname}"] = (
                            f"{schema_type(isub, spec)}" + (f" — {idesc}" if idesc else "")
                        )
        break

    summary = (op.get("summary") or "").strip()
    description = (op.get("description") or "").strip().replace("\n", " ")
    if summary and description:
        first = re.split(r"[。；;]", description, maxsplit=1)[0]
        desc = f"{summary} — {first}" if first and first != summary else summary
    else:
        desc = summary or description
    desc = DESCRIPTION_OVERRIDES.get((method, path), desc)
    desc = re.sub(r"\s+", " ", desc)[:300]

    entry: dict = {
        "method": method,
        "path": path,
        "auth_required": (method, path) not in AUTH_FREE,
        "user_id_required": (method, path) not in AUTH_FREE | USER_ID_OPTIONAL,
        "description": desc,
    }
    if path_params:
        entry["path_params"] = path_params
    if query_params:
        entry["params"] = query_params
    if body:
        entry["body"] = body
    if response:
        entry["response"] = response
    return entry


def generate_registry(spec: dict, old: dict) -> dict:
    registry: dict[str, dict] = {}
    unmapped: list[str] = []
    for path, item in sorted(spec["paths"].items()):
        for method, op in sorted(item.items()):
            key_tuple = (method.upper(), path)
            key = KEY_MAP.get(key_tuple)
            if not key:
                unmapped.append(f"{method.upper()} {path}")
                continue
            entry = build_entry(method.upper(), path, op, spec)
            if key in old:
                # Preserve curated metadata that the live docs do not carry.
                merged = dict(old[key])
                merged.update(entry)
                for extra in ("filter_fields", "filter_operators"):
                    if extra in old[key]:
                        merged[extra] = old[key][extra]
                # Keep hand-written descriptions when they add information.
                old_desc = (old[key].get("description") or "").strip()
                if old_desc and key_tuple not in DESCRIPTION_OVERRIDES \
                        and old_desc not in entry.get("description", ""):
                    merged["description"] = old_desc
                registry[key] = merged
            else:
                registry[key] = entry
    if unmapped:
        print("⚠ 以下操作未在 KEY_MAP 中登记，已跳过:", file=sys.stderr)
        for item in unmapped:
            print(f"  {item}", file=sys.stderr)
    return dict(sorted(registry.items()))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="只比对，不写文件；有差异时退出码 1")
    parser.add_argument("--offline", action="store_true", help="使用 .cache/emoo-docs 中的缓存")
    args = parser.parse_args()

    docs = fetch_all_markdown(args.offline)
    parsed = [doc for doc in (extract_yaml(text) for text in docs) if doc]
    spec = merge_specs(parsed)

    old = json.loads(REGISTRY.read_text(encoding="utf-8")) if REGISTRY.exists() else {}
    registry = generate_registry(spec, old)

    if args.check:
        added = sorted(set(registry) - set(old))
        removed = sorted(set(old) - set(registry))
        changed = sorted(k for k in set(old) & set(registry) if old[k] != registry[k])
        if added or removed or changed:
            print(f"端点注册表有差异: +{len(added)} -{len(removed)} ~{len(changed)}")
            for k in added:
                print(f"  + {k}")
            for k in removed:
                print(f"  - {k}")
            for k in changed:
                print(f"  ~ {k}")
            return 1
        print("端点注册表已是最新")
        return 0

    SPEC_OUT.parent.mkdir(parents=True, exist_ok=True)
    SPEC_OUT.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REGISTRY.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已写入 {SPEC_OUT.relative_to(ROOT)} ({SPEC_OUT.stat().st_size // 1024} KB)")
    print(f"已写入 {REGISTRY.relative_to(ROOT)} ({len(registry)} endpoints)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

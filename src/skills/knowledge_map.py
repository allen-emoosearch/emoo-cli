"""Knowledge map generation: scan all apps + doc groups + Base tables.

Produces two output files in the output directory:
  - emoo_knowledge_map.json  (machine-readable, consumed by intent analysis)
  - emoo_knowledge_map.md    (human-readable summary)
"""

import json
import os
import time
from collections import Counter
from typing import Optional


def _sample_titles(client, ws_app_key: str, doc_group_id: str,
                   group_name: str = "", limit: int = 5) -> list[str]:
    """Sample document titles from a doc group by searching with its group_id."""
    kw = group_name[:2] if group_name else "一"
    try:
        resp = client.post("/search", body={
            "keyword": kw,
            "page_size": min(limit, 10),
            "current_page": 1,
            "text_format": "plain",
            "filter_conditions": [[
                {"field": "ws_app.ws_app_key", "operator": "eq", "value": ws_app_key},
                {"field": "doc_group.app_group_id", "operator": "eq", "value": doc_group_id},
            ]],
        })
        results = resp.get("data", {}).get("results", [])
        return [r.get("title", "") for r in results if r.get("title")]
    except Exception:
        return []


def _scan_base_tables(client) -> list[dict]:
    """Scan all Base tables with field-level sniffing.

    For each table: fetch sample records, extract field names/types,
    enumerate low-cardinality field values, and collect content samples.
    """
    tables = []
    try:
        tbl_resp = client.get("/data/table", params={"page_size": 100})
        base_tables = tbl_resp.get("data", {}).get("results", [])
    except Exception:
        return tables

    for t in base_tables:
        tbl_name = t.get("table_name", "")
        tbl_key = t.get("table_key", "")
        t_entry = {
            "table_key": tbl_key,
            "table_name": tbl_name,
            "column_count": t.get("column_count", 0),
            "record_count": t.get("record_count", 0),
            "fields": [],
        }

        if tbl_name and tbl_key and t.get("record_count", 0) > 0:
            _sniff_table(client, tbl_name, t_entry)

        tables.append(t_entry)
    return tables


def _sniff_table(client, table_name: str, t_entry: dict, sample_size: int = 50):
    """Fetch sample records and analyse field patterns."""
    all_fields = {}
    all_records = []

    try:
        for page in range(1, 6):  # up to 5 pages * 20 = 100 records
            resp = client.post("/data/records/list", body={
                "table_name": table_name,
                "page_size": min(sample_size, 20),
                "current_page": page,
            })
            recs = resp.get("data", {}).get("results", [])
            if not recs:
                break
            all_records.extend(recs)
            if len(all_records) >= sample_size:
                break
    except Exception:
        pass

    if not all_records:
        return

    # Collect all field values
    for r in all_records[:sample_size]:
        fields = r.get("fields", {})
        for fname, fval in fields.items():
            if fname not in all_fields:
                all_fields[fname] = []
            all_fields[fname].append(fval)

    # Build field profiles
    for fname, values in all_fields.items():
        non_none = [v for v in values if v is not None]

        # Determine type
        types = {type(v).__name__ for v in non_none}
        if len(types) == 1:
            ftype = types.pop()
        else:
            ftype = "mixed"

        if not non_none:
            f_entry = {"name": fname, "type": "unknown", "nullable": True, "samples": []}
        elif isinstance(non_none[0], list):
            inner_types = {type(x).__name__ for v in non_none for x in v if x is not None}
            ftype = f"list[{','.join(inner_types)}]"
            f_entry = {
                "name": fname, "type": ftype, "nullable": len(non_none) < len(values),
                "samples": [str(v)[:80] for v in non_none[:3]],
            }
        elif ftype in ("int", "float"):
            nums = [float(v) for v in non_none]
            f_entry = {
                "name": fname, "type": "number",
                "nullable": len(non_none) < len(values),
                "samples": non_none[:3],
                "min": min(nums), "max": max(nums), "avg": round(sum(nums) / len(nums), 2),
            }
        elif ftype == "str":
            n_unique = len(set(non_none))
            str_lens = [len(str(v)) for v in non_none]
            f_entry = {
                "name": fname, "type": "string",
                "nullable": len(non_none) < len(values),
                "unique_count": n_unique,
                "avg_length": round(sum(str_lens) / len(str_lens)),
                "samples": [str(v)[:120] for v in non_none[:3]],
            }
            # Low-cardinality: list value distribution
            if n_unique <= 30 and n_unique < len(non_none) * 0.8:
                dist = Counter(str(v) for v in non_none)
                f_entry["value_distribution"] = [
                    {"value": k, "count": c} for k, c in dist.most_common(15)
                ]
        elif ftype == "bool":
            true_count = sum(1 for v in non_none if v)
            f_entry = {
                "name": fname, "type": "boolean",
                "nullable": len(non_none) < len(values),
                "true_ratio": round(true_count / len(non_none), 2),
            }
        else:
            f_entry = {
                "name": fname, "type": ftype,
                "nullable": len(non_none) < len(values),
                "samples": [str(v)[:80] for v in non_none[:3]],
            }

        t_entry["fields"].append(f_entry)


def _build_markdown(km: dict) -> str:
    """Render knowledge map dict as markdown."""
    gen_time = km.get("generated_at", "")
    apps = km.get("apps", [])
    total_docs = sum(a.get("doc_count", 0) for a in apps)

    lines = [
        "# EMOO 增强知识图谱",
        "",
        f"> 生成时间: {gen_time}  |  应用数: {len(apps)}  |  文档总数: {total_docs}",
        "",
        "---",
        "",
        "## 应用总览",
        "",
        "| # | 应用名称 | ws_app_key | 文档组数 | 文档数 | 主要内容 |",
        "|---|---------|-----------|---------|-------|---------|",
    ]

    for i, a in enumerate(apps, 1):
        key_short = a["ws_app_key"][:14] + "..."
        samples = "、".join(a.get("sample_titles", [])[:3]) or "—"
        lines.append(
            f"| {i} | {a['title']} | {key_short} | "
            f"{a.get('doc_group_count', 0)} | {a.get('doc_count', 0)} | {samples} |"
        )

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 各应用文档组详情")
    lines.append("")

    for a in apps:
        lines.append(f"### {a['title']}")
        lines.append("")
        lines.append(f"- **ws_app_key**: `{a['ws_app_key']}`")
        lines.append(f"- **文档总数**: {a.get('doc_count', 0)}")
        lines.append("")
        groups = a.get("doc_groups", [])
        if groups:
            lines.append("| 文档组 | 描述 | 文档数 | 示例内容 |")
            lines.append("|--------|------|--------|---------|")
            for g in groups:
                desc = (g.get("desc") or "")[:40]
                samples = "、".join(g.get("sample_titles", [])[:2]) or "—"
                lines.append(
                    f"| {g.get('app_group_name', '')} | {desc} | "
                    f"{g.get('doc_count', 0)} | {samples} |"
                )
        else:
            lines.append("_无文档组数据_")
        lines.append("")

    # Base tables
    base_tables = km.get("base_tables", [])
    if base_tables:
        lines.append("---")
        lines.append("")
        lines.append("## EMOO Base 数据表")
        lines.append("")
        lines.append(f"| # | 表名 | table_key | 列数 | 记录数 |")
        lines.append("|---|------|-----------|------|--------|")
        for i, t in enumerate(base_tables, 1):
            key_short = t["table_key"][:14] + "..." if t.get("table_key") else "—"
            lines.append(
                f"| {i} | {t['table_name']} | {key_short} | "
                f"{t.get('column_count', 0)} | {t.get('record_count', 0)} |"
            )
        lines.append("")
        for t in base_tables:
            lines.append(f"### {t['table_name']}")
            lines.append(f"- **table_key**: `{t['table_key']}`")
            lines.append(f"- **列数**: {t.get('column_count', 0)}  |  **记录数**: {t.get('record_count', 0)}")
            fields = t.get("fields", [])
            if fields:
                lines.append("")
                lines.append("| 字段名 | 类型 | 详情 |")
                lines.append("|--------|------|------|")
                for f in fields:
                    detail = ""
                    if "value_distribution" in f:
                        top_vals = ", ".join(
                            f"{v['value']}({v['count']})"
                            for v in f.get("value_distribution", [])[:5]
                        )
                        detail = f"枚举: {top_vals}"
                    elif f["type"] == "number":
                        detail = f"范围 {f.get('min','?')}~{f.get('max','?')}, 均 {f.get('avg','?')}"
                    elif f["type"] == "string":
                        detail = f"{f.get('unique_count','?')}个唯一值, 均长{f.get('avg_length','?')}"
                    elif f["type"] == "boolean":
                        detail = f"true占比 {f.get('true_ratio','?')}"
                    if f.get("samples"):
                        s = "; ".join(str(x)[:60] for x in f["samples"][:2])
                        detail += f"  | 例: {s}"
                    lines.append(f"| {f['name']} | {f['type']} | {detail[:120]} |")
            lines.append(f"\n```bash\n# 查询此表\nemoo base record-list --table-name \"{t['table_name']}\" --page-size 20\n# 按时间/类型过滤\nemoo base record-list --table-name \"{t['table_name']}\" -f \"msgtime:gte:2026-06-01,msgtype:eq:text\"\n```")
            lines.append("")

    # Search suggestions
    lines.append("---")
    lines.append("")
    lines.append("## 搜索建议")
    lines.append("")
    lines.append("常用过滤维度:")
    lines.append("")
    for a in apps:
        lines.append(f"```bash")
        lines.append(f"# {a['title']}")
        lines.append(f"emoo data search -k \"关键词\" \\")
        lines.append(f"  -f '{{\"field\":\"ws_app.ws_app_key\",\"operator\":\"eq\",\"value\":\"{a['ws_app_key']}\"}}'")
        lines.append(f"```")
        lines.append("")

    return "\n".join(lines)


def generate_knowledge_map(
    client,
    max_sample_per_group: int = 5,
    output_dir: str = ".",
    max_doc_groups: int = 200,
) -> str:
    """Generate enhanced knowledge map for the workspace.

    Args:
        client: EmooClient instance
        max_sample_per_group: max titles to sample from each doc group
        output_dir: directory for output files
        max_doc_groups: max total doc groups to sample (safety limit)

    Returns:
        Path to the generated JSON file
    """
    km = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "apps": [],
        "base_tables": [],
    }

    # Step 0: scan Base tables
    try:
        print("正在扫描 Base 数据表...")
        base_tables = _scan_base_tables(client)
        km["base_tables"] = base_tables
        if base_tables:
            total_recs = sum(t.get("record_count", 0) for t in base_tables)
            print(f"  Base 表: {len(base_tables)} 个, 共 {total_recs} 条记录")
    except Exception:
        pass

    # Step 1: list all apps
    resp = client.get("/apps")
    apps = resp.get("data", [])
    if not isinstance(apps, list):
        apps = []

    total_groups_sampled = 0

    for app in sorted(apps, key=lambda x: x.get("title", "")):
        ws_app_key = app.get("ws_app_key", "")
        app_title = app.get("title", "")
        app_entry = {
            "ws_app_key": ws_app_key,
            "title": app_title,
            "doc_count": app.get("doc_count", 0),
            "doc_group_count": app.get("doc_group_count", 0),
            "doc_groups": [],
            "sample_titles": [],
        }

        # Step 2: list doc groups for this app
        try:
            dg_resp = client.get(f"/app/{ws_app_key}/doc-groups", params={
                "page_size": 200,
                "current_page": 1,
            })
            dg_data = dg_resp.get("data", {})
            doc_groups = dg_data.get("results", [])
        except Exception:
            doc_groups = []

        # Step 3: sample titles from each doc group (respecting limits)
        for dg in doc_groups:
            gid = dg.get("app_group_id", "")
            gname = dg.get("app_group_name", "")
            if total_groups_sampled < max_doc_groups and gid:
                samples = _sample_titles(client, ws_app_key, gid, gname, max_sample_per_group)
                total_groups_sampled += 1
            else:
                samples = []

            app_entry["doc_groups"].append({
                "app_group_id": gid,
                "app_group_name": gname,
                "desc": dg.get("app_group_desc") or "",
                "url": dg.get("url", ""),
                "doc_count": dg.get("doc_count", 0),
                "sample_titles": samples,
            })

            # Also accumulate app-level sample titles
            for s in samples:
                if s not in app_entry["sample_titles"]:
                    app_entry["sample_titles"].append(s)
                    if len(app_entry["sample_titles"]) >= 10:
                        break

        # If no doc groups sampled yet, do a blanket app-level search for titles
        if not app_entry["sample_titles"] and app_entry["doc_count"] > 0:
            try:
                sr = client.post("/search", body={
                    "keyword": app_title[:2] or "一",
                    "page_size": 10,
                    "current_page": 1,
                    "text_format": "plain",
                    "filter_conditions": [[
                        {"field": "ws_app.ws_app_key", "operator": "eq", "value": ws_app_key},
                    ]],
                })
                for r in sr.get("data", {}).get("results", []):
                    t = r.get("title", "")
                    if t:
                        app_entry["sample_titles"].append(t)
            except Exception:
                pass

        km["apps"].append(app_entry)

    # Write JSON
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, "emoo_knowledge_map.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(km, f, ensure_ascii=False, indent=2)

    # Write Markdown
    md_path = os.path.join(output_dir, "emoo_knowledge_map.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(_build_markdown(km))

    return json_path

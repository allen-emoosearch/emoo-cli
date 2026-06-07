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


def _classify_table(field_names: set) -> str:
    """Classify a Base table as 'chat' (conversation log) or 'structured' (business data).

    Chat indicators: msgid + msgtype + content + from_user (企微 archive signature)
    Structured: everything else (CRM, projects, inventory, etc.)
    """
    chat_keys = {"msgid", "msgtype", "from_user", "content", "action", "roomid", "seq"}
    if len(field_names & chat_keys) >= 4:
        return "chat"
    return "structured"


def _scan_base_tables(client) -> list[dict]:
    """Scan all Base tables, classify, and apply appropriate sniffing strategy.

    - Chat tables: conversation threading + topic extraction
    - Structured tables: field profiles + sample row analysis
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
            "type": "empty",
        }

        if tbl_name and tbl_key and t.get("record_count", 0) > 0:
            _sniff_table(client, tbl_name, t_entry, sample_size=20)
            field_names = {f["name"] for f in t_entry["fields"]}
            tbl_type = _classify_table(field_names)
            t_entry["type"] = tbl_type

            if tbl_type == "chat":
                print(f"    🗨️ 检测到聊天表: {tbl_name}, 进行对话线程分析...")
                _sniff_chat(client, tbl_name, t_entry)
            else:
                print(f"    📊 检测到结构化表: {tbl_name}, 进行字段+样本分析...")
                # Re-sniff with more samples for deeper analysis
                t_entry["fields"] = []
                _sniff_table(client, tbl_name, t_entry, sample_size=50)
                _sniff_sample_rows(client, tbl_name, t_entry)

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


def _sniff_chat(client, table_name: str, t_entry: dict):
    """Analyze a chat-like Base table with conversation threading.

    Strategy:
    1. Fetch recent records grouped by roomid
    2. Sort each room by msgtime
    3. Split into conversation threads (gap > 1 hour = new thread)
    4. Extract topic keywords, participants, date range for each thread
    5. Summarize the most active threads
    """
    all_records = []
    try:
        page = 1
        max_pages = 10  # 10 pages × 100 = 1000 records for chat sniffing
        while page <= max_pages:
            resp = client.post("/data/records/list", body={
                "table_name": table_name,
                "page_size": 100, "current_page": page,
            })
            recs = resp.get("data", {}).get("results", [])
            if not recs: break
            all_records.extend(recs)
            page += 1
    except Exception:
        pass

    if not all_records:
        return

    # Group by roomid
    rooms = {}
    for r in all_records:
        f = r.get("fields", {})
        rid = f.get("roomid", "_no_room")
        if rid not in rooms:
            rooms[rid] = []
        rooms[rid].append(f)

    # Build room summaries
    room_summaries = []
    for rid, msgs in sorted(rooms.items(), key=lambda x: -len(x[1])):
        msgs.sort(key=lambda m: (m.get("msgtime") or "", m.get("seq") or 0))

        # Detect threads: gap > 1 hour = new thread
        threads = []
        current = []
        for m in msgs:
            if m.get("msgtype") != "text":
                continue  # only thread text messages
            if current:
                last_t = _parse_time(current[-1].get("msgtime", ""))
                this_t = _parse_time(m.get("msgtime", ""))
                if last_t and this_t and (this_t - last_t).total_seconds() > 10800:  # 3 hour gap = new thread
                    if len(current) >= 3:
                        threads.append(current)
                    current = []
            current.append(m)
        if len(current) >= 3:
            threads.append(current)

        # Monthly active users
        users = Counter(m.get("from_user", "?") for m in msgs)
        msgtypes = Counter(m.get("msgtype", "?") for m in msgs)
        dates = [m["msgtime"][:10] for m in msgs if m.get("msgtime")]
        date_range = f"{min(dates)} ~ {max(dates)}" if dates else "?"

        summary = {
            "roomid": rid,
            "total_msgs": len(msgs),
            "user_count": len(users),
            "top_users": [{"user": u, "count": c} for u, c in users.most_common(5)],
            "msgtype_dist": dict(msgtypes.most_common(5)),
            "date_range": date_range,
            "thread_count": len(threads),
            "threads": [],
        }

        # Summarize each thread
        for ti, thread in enumerate(threads[:5]):  # top 5 threads
            participants = list(set(m.get("from_user", "?") for m in thread))
            t_dates = sorted(set(m.get("msgtime", "")[:10] for m in thread if m.get("msgtime")))
            # Extract topic: first meaningful message + most frequent keywords
            topic_msgs = [str(m.get("content", "")) for m in thread if m.get("content")]
            keywords = _extract_keywords(" ".join(topic_msgs[:10]))
            first_msg = topic_msgs[0][:100] if topic_msgs else ""
            summary["threads"].append({
                "index": ti + 1,
                "msgs": len(thread),
                "participants": participants,
                "dates": t_dates,
                "keywords": keywords[:8],
                "first_msg": first_msg,
                "samples": topic_msgs[:3],
            })

        room_summaries.append(summary)

    t_entry["rooms"] = room_summaries
    t_entry["total_rooms"] = len(rooms)


def _parse_time(ts: str):
    """Parse a time string like '2026-05-30' or '2026-05-30T14:00:00'."""
    if not ts:
        return None
    try:
        from datetime import datetime
        ts_clean = ts.replace("T", " ")[:19]
        return datetime.strptime(ts_clean, "%Y-%m-%d %H:%M:%S")
    except Exception:
        try:
            return datetime.strptime(ts[:10], "%Y-%m-%d")
        except Exception:
            return None


def _extract_keywords(text: str, min_len: int = 2) -> list[str]:
    """Extract meaningful Chinese keywords from text using punctuation-based segmentation."""
    import re
    # Split by Chinese/English punctuation, whitespace, and digits
    segments = re.split(r'[，。！？、；：""''「」『』【】（）《》\s\d，\.\!\?\;\:\"\'\(\)\[\]\{\}]+', text)
    words = [s.strip() for s in segments if s.strip()]
    # Keep only segments with Chinese chars and >= min_len
    result = [w for w in words if len(w) >= min_len and re.search(r'[一-鿿]', w)]
    # Deduplicate preserving order
    seen = set()
    unique = []
    for w in result:
        if w not in seen:
            seen.add(w)
            unique.append(w)
    return unique


def _sniff_sample_rows(client, table_name: str, t_entry: dict):
    """Fetch sample rows (full records) for structured tables to show data patterns."""
    try:
        resp = client.post("/data/records/list", body={
            "table_name": table_name, "page_size": 5, "current_page": 1,
        })
        recs = resp.get("data", {}).get("results", [])
        if recs:
            t_entry["sample_rows"] = [
                {k: str(v)[:100] for k, v in r.get("fields", {}).items()}
                for r in recs[:3]
            ]
    except Exception:
        pass


def _render_chat_table(t: dict, lines: list):
    """Render a chat-type Base table with room + thread analysis."""
    rooms = t.get("rooms", [])
    fields = t.get("fields", [])

    if fields:
        lines.append("")
        lines.append("| 字段 | 类型 | 分析 |")
        lines.append("|------|------|------|")
        for f in fields:
            detail = ""
            if f.get("value_distribution"):
                top = f["value_distribution"][:5]
                detail = "枚举: " + ", ".join(f"{v['value']}({v['count']})" for v in top)
            elif f["type"] == "number":
                detail = f"{f.get('min','?')}~{f.get('max','?')}, 均{f.get('avg','?')}"
            lines.append(f"| {f['name']} | {f['type']} | {detail[:120]} |")

    if not rooms:
        return

    lines.append("")
    lines.append(f"**{len(rooms)} 个聊天群**:")
    for room in rooms[:8]:
        rid_short = room["roomid"][:16] + "..." if len(room.get("roomid", "")) > 16 else room.get("roomid", "")
        top_users = ", ".join(f"{u['user']}({u['count']})" for u in room.get("top_users", [])[:4])
        mtypes = ", ".join(f"{k}:{v}" for k, v in list(room.get("msgtype_dist", {}).items())[:4])
        lines.append(f"- **群 {rid_short}**: {room['total_msgs']}条消息, {room['user_count']}人, {room['date_range']}")
        lines.append(f"  - 主要用户: {top_users}")
        lines.append(f"  - 消息类型: {mtypes}")
        lines.append(f"  - {room.get('thread_count', 0)} 个对话线程")

        for th in room.get("threads", [])[:3]:
            kw = ", ".join(th.get("keywords", [])[:5])
            participants = ", ".join(th.get("participants", [])[:5])
            lines.append(f"  - **线程{th['index']}**: {th['msgs']}条, 参与: {participants}")
            lines.append(f"    - 关键词: {kw}")
            lines.append(f"    - 首条: _{th.get('first_msg', '')[:120]}_")

    lines.append("")


def _render_structured_table(t: dict, lines: list):
    """Render a structured (spreadsheet) Base table with field analysis + sample rows."""
    fields = t.get("fields", [])
    rows = t.get("sample_rows", [])

    if fields:
        lines.append("")
        lines.append("| 字段 | 类型 | 分析 |")
        lines.append("|------|------|------|")
        for f in fields:
            detail = ""
            if f.get("value_distribution"):
                top = f["value_distribution"][:5]
                detail = "枚举: " + ", ".join(f"{v['value']}({v['count']})" for v in top)
            elif f["type"] == "number":
                detail = f"范围 {f.get('min','?')}~{f.get('max','?')}, 均 {f.get('avg','?')}"
            elif f["type"] == "string":
                detail = f"{f.get('unique_count','?')}个唯一值, 均长{f.get('avg_length','?')}"
            if f.get("samples"):
                s = "; ".join(str(x)[:60] for x in f["samples"][:2])
                detail += f"  | 例: {s}"
            lines.append(f"| {f['name']} | {f['type']} | {detail[:120]} |")

    if rows:
        lines.append("")
        lines.append("**样本数据行**:")
        for i, row in enumerate(rows[:3], 1):
            lines.append(f"- 行 {i}:")
            for k, v in row.items():
                lines.append(f"  - {k}: {v}")
        lines.append("")


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
            tbl_type = t.get("type", "empty")
            type_label = {"chat": "🗨️ 聊天记录", "structured": "📊 结构化数据", "empty": "📭 空表"}.get(tbl_type, tbl_type)
            lines.append(f"### {t['table_name']} ({type_label})")
            lines.append(f"- **table_key**: `{t['table_key']}`")
            lines.append(f"- **列数**: {t.get('column_count', 0)}  |  **记录数**: {t.get('record_count', 0)}")

            if tbl_type == "chat":
                _render_chat_table(t, lines)
            elif tbl_type == "structured":
                _render_structured_table(t, lines)

            lines.append(f"\n```bash\n# 查询此表\nemoo base record-list --table-name \"{t['table_name']}\" --page-size 20\n```")
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

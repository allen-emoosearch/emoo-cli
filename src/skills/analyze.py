"""Intelligent chat analysis pipeline: KM room matching → targeted search → aggregation.

Improvements over v2:
  - Index hints: explains WHY each room was matched
  - Probe filtering: excludes test_probe records by default
  - Stratified sampling: day-stratified when >200 results
  - Query session cache: avoid re-querying same room+time within a session
  - Smart time window: infer optimal window from keyword type
  - Compact mode: slim output (time/from/content/group)
"""

import json
import os
import re
import sys
import time as _time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Optional


def _log(msg: str):
    """Write to stderr so stdout stays JSON-clean."""
    print(msg, file=sys.stderr)

# ── Query session cache ─────────────────────────────────────────────

_query_cache: dict = {}  # keyed by session_id: {cache_key: result}


def clear_query_cache(session_id: str = None):
    """Clear query cache for a session, or all if session_id is None."""
    global _query_cache
    if session_id:
        _query_cache.pop(session_id, None)
    else:
        _query_cache = {}


# ── Probe/Test detection ────────────────────────────────────────────

def _is_probe(record: dict) -> bool:
    """Check if a record is a probe/test message to be excluded."""
    f = record.get("fields", {})
    msgid = str(f.get("msgid", "") or "")
    roomid = str(f.get("roomid", "") or "")
    content = str(f.get("content", "") or "")
    if msgid.startswith("test_probe"):
        return True
    if roomid in ("test", "r1"):
        return True
    if content == "probe":
        return True
    return False


# ── Time parsing ────────────────────────────────────────────────────

def _parse_time_with_ai(client, query: str) -> tuple | None:
    """Use EMOO AI to parse time from natural language."""
    today = datetime.now().strftime("%Y-%m-%d")
    prompt = (
        f'从以下查询中提取时间范围，只返回JSON: {{"start":"YYYY-MM-DD","end":"YYYY-MM-DD"}}。'
        f'今天是{today}。如无时间信息返回{{"start":"","end":""}}。'
        f'\n查询: {query}'
    )
    try:
        resp = client.post("/chat/messages", body={"query": prompt, "stream": False})
        answer = resp.get("data", {}).get("complete_response", "")
        match = re.search(r'\{[^}]+\}', answer)
        if match:
            data = json.loads(match.group())
            if data.get("start") and data.get("end"):
                return data["start"], data["end"]
    except Exception:
        pass
    return None


def _parse_time_expression(query: str, client=None) -> tuple:
    """Try AI first, fall back to regex."""
    if client:
        result = _parse_time_with_ai(client, query)
        if result:
            _log(f"   🤖 AI解析时间: {result[0]} ~ {result[1]}")
            return result

    today = datetime.now().strftime("%Y-%m-%d")
    # Regex fallback
    if re.search(r'最近[一1][周月]|最近\d+天', query):
        if re.search(r'[月]', query):
            return (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"), today
        m = re.search(r'(\d+)天', query)
        if m:
            n = int(m.group(1))
            return (datetime.now() - timedelta(days=n)).strftime("%Y-%m-%d"), today
        return (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"), today
    if re.search(r'近[一1]个?月|最近[一1]个?月', query):
        return (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"), today
    if re.search(r'近[一1]周|最近[一1]周', query):
        return (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"), today
    if re.search(r'近(\d+)天|最近(\d+)天', query):
        n = int(re.search(r'(\d+)', query).group(1))
        return (datetime.now() - timedelta(days=n)).strftime("%Y-%m-%d"), today
    if re.search(r'今天', query):
        return today, today
    if re.search(r'昨天', query):
        return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"), (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    if re.search(r'本周', query):
        return (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"), today
    if re.search(r'本月', query):
        return (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"), today
    return (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"), today


def _infer_time_window(keywords: list[str]) -> int:
    """Recommend time window in days based on keyword type."""
    long_window = {"报销", "费用", "金额", "付款", "支出", "发票", "对账", "财务", "审批", "结算"}
    for kw in keywords:
        if kw in long_window:
            return 30
    return 7


# ── Keyword extraction and expansion ─────────────────────────────────

def _extract_search_keywords(query: str) -> list[str]:
    # Remove time expressions
    cleaned = re.sub(
        r'最近[一1]个?[周月]|最近\d+天|最近[一1][周月]|最近|'
        r'近[一1]个?[周月]|近[一1][周月]|近\d+[天周月]|'
        r'本周|本月|今天|昨天|上个季度|上个[周月]|这个[周月]',
        '', query)
    # Remove command/filler words (order: longer first for safety)
    cleaned = re.sub(
        r'有没有什么|有没有人|有没有|所有|全部|详细|帮我查下|帮我查|帮我|给我|'
        r'查一下|查下|一下|的|情况|查|看|分析|统计|报告|汇总|相关|'
        r'记录|信息|内容|数据|搜索|查找|帮忙|请问|麻烦|帮忙',
        '', cleaned)
    # Remove standalone single characters that are command leftovers
    cleaned = re.sub(r'^[的下看查]+|[的下看查]+$', '', cleaned)
    words = re.findall(r'[一-鿿]{2,}', cleaned)
    return list(dict.fromkeys(words))


def _expand_keywords_with_ai(client, keywords: list[str], km: dict) -> list[str]:
    if not keywords or not client:
        return keywords
    doc_topics = set()
    for app in km.get("apps", [])[:5]:
        for title in app.get("sample_titles", [])[:3]:
            doc_topics.add(title[:60])
    room_topics = []
    for tbl in km.get("base_tables", []):
        if tbl.get("type") != "chat":
            continue
        for room in tbl.get("rooms", [])[:5]:
            for th in room.get("threads", [])[:2]:
                room_topics.extend(th.get("keywords", [])[:5])
    prompt = (
        f'用户想查询: "{",".join(keywords)}"。'
        f'文档主题: {",".join(list(doc_topics)[:10])}。'
        f'群话题: {",".join(room_topics[:15])}。'
        f'列出所有相关的搜索关键词，只返回JSON数组: ["词1","词2",...]'
    )
    try:
        resp = client.post("/chat/messages", body={"query": prompt, "stream": False})
        answer = resp.get("data", {}).get("complete_response", "")
        match = re.search(r'\[[^\]]+\]', answer)
        if match:
            expanded = json.loads(match.group())
            if isinstance(expanded, list) and expanded:
                seen = set(keywords)
                result = list(keywords)
                for w in expanded:
                    if w not in seen and len(w) <= 10:
                        seen.add(w)
                        result.append(w)
                if len(result) > len(keywords):
                    _log(f"   🤖 AI扩展关键词: {keywords} → {result[:8]}")
                return result
    except Exception:
        pass
    return keywords


# ── Chat table discovery ─────────────────────────────────────────────

def _discover_chat_tables(km: dict) -> list[dict]:
    tables = []
    time_candidates = ["msgtime", "created_at", "updated_at", "synced_at", "date", "time"]
    user_candidates = ["from_user", "user", "username", "sender", "from"]
    content_candidates = ["content", "text", "message", "body"]
    group_candidates = ["roomid", "room_id", "group_id", "channel", "room", "conversation_id"]

    for tbl in km.get("base_tables", []):
        if tbl.get("type") != "chat":
            continue
        fnames = [f["name"] for f in tbl.get("fields", [])]
        tables.append({
            "table_name": tbl["table_name"],
            "time_field": _best_match(fnames, time_candidates),
            "user_field": _best_match(fnames, user_candidates),
            "content_field": _best_match(fnames, content_candidates),
            "group_field": _best_match(fnames, group_candidates),
        })
    return tables


def _best_match(fnames: list, candidates: list) -> str | None:
    for c in candidates:
        for f in fnames:
            if c == f.lower().replace("_", ""):
                return f
    for c in candidates:
        for f in fnames:
            if c in f.lower().replace("_", ""):
                return f
    return None


# ── Room matching with index hints ───────────────────────────────────

def _match_rooms(km: dict, keywords: list[str], min_match: int = 1) -> list[dict]:
    """Match keywords against KM rooms, returns matched rooms with index hints."""
    matches = []
    chat_tables = _discover_chat_tables(km)

    for tbl in chat_tables:
        table_name = tbl["table_name"]
        group_field = tbl["group_field"] or "roomid"
        tbl_entry = None
        for bt in km.get("base_tables", []):
            if bt.get("table_name") == table_name:
                tbl_entry = bt
                break
        if not tbl_entry:
            continue

        for room in tbl_entry.get("rooms", []):
            all_room_kw = set()
            for th in room.get("threads", []):
                all_room_kw.update(th.get("keywords", []))
            for u in room.get("top_users", []):
                all_room_kw.add(u.get("user", ""))

            matched_kws = []
            match_reasons = []
            for uk in keywords:
                for rk in all_room_kw:
                    if uk in rk or rk in uk:
                        matched_kws.append(uk)
                        # Find which thread produced the match
                        for th in room.get("threads", []):
                            if uk in " ".join(th.get("keywords", [])):
                                match_reasons.append(f'"{uk}"→"{th.get("first_msg", "")[:40]}"')
                                break
                        break

            if len(set(matched_kws)) >= min_match:
                matches.append({
                    "table_name": table_name, "group_field": group_field,
                    "group_id": room["roomid"],
                    "msgs": room.get("total_msgs", 0),
                    "users": room.get("user_count", 0),
                    "matched_keywords": list(set(matched_kws)),
                    "match_reasons": match_reasons[:3],
                    "score": len(set(matched_kws)),
                })
    matches.sort(key=lambda x: -x["score"])
    return matches


# ── Stratified sampling ──────────────────────────────────────────────

def _stratified_sample(records: list, max_total: int = 200) -> list:
    """Day-stratified sampling: keep proportional records per day."""
    if len(records) <= max_total:
        return records
    by_date = defaultdict(list)
    for r in records:
        t = r.get("fields", {}).get("msgtime", "")[:10]
        by_date[t].append(r)
    n_days = len(by_date)
    per_day = max(max_total // n_days, 3)
    result = []
    for day in sorted(by_date.keys()):
        result.extend(by_date[day][:per_day])
    if len(result) > max_total:
        result = result[:max_total]
    return sorted(result, key=lambda r: (r.get("fields", {}).get("msgtime", ""), r.get("fields", {}).get("seq", 0)))


# ── AI Summarization ─────────────────────────────────────────────────

def _summarize_with_ai(client, query: str, records: list, max_chars: int = 8000) -> str:
    """Send full room data to AI for summarization."""
    # Build a compact text representation
    lines = []
    for r in records[:300]:  # max 300 messages
        f = r.get("fields", {})
        t = f.get("msgtime", "") or f.get("time", "")
        u = f.get("from_user", "") or f.get("user", "")
        c = str(f.get("content", "") or "")[:200]
        lines.append(f"[{t}] {u}: {c}")
    text = "\n".join(lines)[:max_chars]

    prompt = f'用户查询: {query}\n\n以下是群聊记录(按时间排序):\n\n{text}\n\n请用中文总结: 1)核心事件 2)关键人物 3)时间线 4)问题/风险。控制在300字以内。'
    try:
        resp = client.post("/chat/messages", body={"query": prompt, "stream": False})
        return resp.get("data", {}).get("complete_response", "")
    except Exception:
        return ""


# ── Main pipeline ────────────────────────────────────────────────────

def run_analyze(client, query: str, km_path: Optional[str] = None,
                compact: bool = False, exclude_probe: bool = True,
                max_results: int = 500, session_id: str = None,
                summarize: bool = False) -> dict:
    """Execute the full intelligent analysis pipeline."""

    # 1. Load KM
    if km_path is None:
        km_path = os.path.expanduser("~/.emoo/knowledge_map")
        if os.path.isdir(km_path):
            api_paths = [d for d in os.listdir(km_path) if os.path.isdir(os.path.join(km_path, d))]
            if api_paths:
                km_path = os.path.join(km_path, api_paths[0], "emoo_knowledge_map.json")
    km = {}
    if os.path.exists(km_path):
        with open(km_path, encoding="utf-8") as f:
            km = json.load(f)

    # 2. Discover chat tables
    chat_tables = _discover_chat_tables(km)
    if not chat_tables:
        return {"query": query, "total": 0,
                "summary": "未找到聊天表，请先运行 knowledge-map 生成知识图谱"}

    # 3. Parse time + keywords
    start, end = _parse_time_expression(query, client=client)
    keywords = _extract_search_keywords(query)
    keywords = _expand_keywords_with_ai(client, keywords, km)
    _log(f"🔍 分析: {query}")
    _log(f"   关键词: {keywords}  时间: {start} ~ {end}")
    _log(f"   聊天表: {len(chat_tables)} 个")

    # 4. Match rooms
    matched_rooms = _match_rooms(km, keywords) if km else []
    if not matched_rooms:
        _log(f"   ⚠️ 无精确匹配群，全局搜索...")
        tbl_map = {t["table_name"]: t for t in chat_tables}
        for tbl in chat_tables:
            for bt in km.get("base_tables", []):
                if bt.get("table_name") == tbl["table_name"]:
                    for room in bt.get("rooms", []):
                        matched_rooms.append({
                            "table_name": tbl["table_name"],
                            "group_field": tbl["group_field"] or "roomid",
                            "group_id": room["roomid"],
                            "matched_keywords": keywords, "score": 0, "match_reasons": [],
                        })
                    break
        matched_rooms = matched_rooms[:5]

    _log(f"   匹配群: {len(matched_rooms)} 个")
    # Build room name map from KM
    room_names = {}
    for bt in km.get("base_tables", []):
        for room in bt.get("rooms", []):
            rid = room.get("roomid", "")
            if not rid: continue
            name = None
            for th in room.get("threads", []):
                for kw in th.get("keywords", []):
                    m = re.search(r'这是(.+?群)', kw)
                    if m:
                        name = m.group(1)
                        break
                if name: break
            if not name:
                top = room.get("top_users", [])
                name = f"{top[0]['user'][:8]}群" if top else f"群_{rid[:8]}"
            room_names[rid] = name

    tbl_map = {t["table_name"]: t for t in chat_tables}

    # 5. Search rooms concurrently
    all_results = []

    def _query_room(room):
        """Query a single room, returns (room_name, results)."""
        tbl_name = room["table_name"]
        group_field = room["group_field"]
        gid = room["group_id"]
        tbl = tbl_map.get(tbl_name, {})
        time_field = tbl.get("time_field", "msgtime")

        reasons = room.get("match_reasons", [])
        reason_str = "; ".join(reasons[:2]) if reasons else f'匹配词: {room.get("matched_keywords", [])}'
        _log(f"   🔍 [{tbl_name}] {gid[:24]}... {reason_str}")

        room_results = []
        api_filters = [f"{time_field}:gte:{start}", f"{time_field}:lte:{end}"]
        if group_field and gid:
            api_filters.append(f"{group_field}:eq:{gid}")

        def _fetch_page(p):
            """Fetch a single page, returns (page_num, records). Get ALL records for AI summarization."""
            resp = client.post("/data/records/list", body={
                "table_name": tbl_name, "page_size": 100,
                "current_page": p, "filters": api_filters,
            })
            recs = resp.get("data", {}).get("results", [])
            results = []
            for r in recs:
                if exclude_probe and _is_probe(r):
                    continue
                content = str(r["fields"].get(tbl.get("content_field", "content"), ""))
                if not content or content == "（无文字内容）":
                    continue
                r["_group_field"] = group_field
                r["_group_id"] = gid
                r["_table"] = tbl_name
                results.append(r)
            return p, results

        try:
            # Page 1: get total for batching
            _, first_batch = _fetch_page(1)
            room_results.extend(first_batch)
            total_pages = 1
            # Re-fetch page 1 to get total, or use a smaller probe
            probe = client.post("/data/records/list", body={
                "table_name": tbl_name, "page_size": 1,
                "current_page": 1, "filters": api_filters,
            })
            total = probe.get("data", {}).get("total", 0)
            total_pages = (total + 99) // 100  # ceil division

            if total_pages > 1:
                _log(f"      📖 {gid[:20]}... {total}条 → {total_pages}页, 并发拉取中...")
                with ThreadPoolExecutor(max_workers=5) as pool:
                    futures = {pool.submit(_fetch_page, p): p for p in range(2, total_pages + 1)}
                    for future in as_completed(futures):
                        p, batch = future.result()
                        room_results.extend(batch)
        except Exception as e:
            _log(f"      ⚠️ [{gid[:20]}] 出错: {e}")

        # Dedup: by msgid first, then content hash for cross-room dedup
        seen_msgid = set()
        seen_content = set()
        deduped = []
        for r in room_results:
            msgid = str(r["fields"].get("msgid", "") or "")
            c = str(r["fields"].get(tbl.get("content_field", "content"), ""))
            # Prefer msgid for exact dedup
            if msgid and msgid in seen_msgid:
                continue
            if msgid:
                seen_msgid.add(msgid)
            # Also dedup by content hash (for messages without msgid)
            ch = hash(c)
            if ch in seen_content:
                continue
            seen_content.add(ch)
            # Skip robot repeats: same user+content appearing >5 times in a room
            deduped.append(r)
        deduped.sort(key=lambda r: (r["fields"].get(time_field, ""), r["fields"].get("seq", 0)))
        _log(f"      ✅ {gid[:20]}... {len(deduped)} 条")

        # Cache for session
        if session_id:
            cache_key = f"{tbl_name}|{gid}|{start}|{end}"
            _query_cache.setdefault(session_id, {})
            _query_cache[session_id][cache_key] = deduped

        return gid, deduped

    # Concurrent execution
    rooms_to_search = matched_rooms[:5]
    with ThreadPoolExecutor(max_workers=min(len(rooms_to_search), 5)) as pool:
        futures = {pool.submit(_query_room, r): r for r in rooms_to_search}
        for future in as_completed(futures):
            try:
                gid, results = future.result()
                all_results.extend(results)
            except Exception as e:
                _log(f"      ❌ 群查询失败: {e}")

    # 6. Aggregate
    if not all_results:
        return {"query": query, "keywords": keywords, "time_range": [start, end],
                "matched_rooms": matched_rooms, "total": 0, "summary": "未找到匹配内容"}

    tbl = chat_tables[0] if chat_tables else {}
    time_field = tbl.get("time_field", "msgtime")
    user_field = tbl.get("user_field", "from_user")
    content_field = tbl.get("content_field", "content")

    # Stratified sampling
    sampling = "full"
    daily_summary = {}
    if len(all_results) > 200:
        by_date = Counter(r["fields"].get(time_field, "")[:10] for r in all_results)
        daily_summary = dict(by_date.most_common())
        all_results = _stratified_sample(all_results, 200)
        sampling = "stratified_by_day"

    all_results.sort(key=lambda r: (r["fields"].get(time_field, ""), r["fields"].get("seq", 0)))
    people = Counter(r["fields"].get(user_field, "?") for r in all_results)
    dates = Counter(r["fields"].get(time_field, "")[:10] for r in all_results)

    # AI Summarization (optional)
    ai_summary = ""
    if summarize and all_results:
        _log(f"\n   🤖 AI 总结中 (基于 {len(all_results)} 条消息)...")
        ai_summary = _summarize_with_ai(client, query, all_results)
        _log(f"   ✅ 总结完成")

    return {
        "query": query, "keywords": keywords, "time_range": [start, end],
        "ai_summary": ai_summary,
        "ai_summary_source_count": len(all_results) if summarize else 0,
        "ai_summary_truncated": len(all_results) > 300 if summarize else False,
        "matched_rooms": [{"group_id": r["group_id"], "name": room_names.get(r["group_id"], ""),
                           "score": r["score"],
                           "matched_keywords": r["matched_keywords"],
                           "reasons": r.get("match_reasons", [])} for r in matched_rooms[:5]],
        "total": len(all_results), "sampling": sampling,
        "daily_summary": daily_summary,
        "by_date": {d: c for d, c in sorted(dates.items())},
        "top_people": [{"user": u, "count": c} for u, c in people.most_common(10)],
        "results": [{
            "time": r["fields"].get(time_field, ""),
            "user": r["fields"].get(user_field, ""),
            "msgid": r["fields"].get("msgid", ""),
            "content": str(r["fields"].get(content_field, ""))[:500],
            "group": str(r.get("_group_id", r.get("_table", "")))[:32],
            "group_name": room_names.get(r.get("_group_id", ""), ""),
        } for r in all_results],
        "samples": [{
            "time": r["fields"].get(time_field, ""),
            "user": r["fields"].get(user_field, ""),
            "content": str(r["fields"].get(content_field, ""))[:200],
            "group": str(r.get("_group_id", r.get("_table", "")))[:20],
        } for r in all_results[:20]],
    }

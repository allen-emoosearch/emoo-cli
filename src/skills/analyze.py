"""Intelligent chat analysis pipeline: KM room matching → targeted search → aggregation.

Flow:
  1. Load knowledge map (cached)
  2. Match user query against room keywords/topics
  3. For matched rooms: query records with time + content filters
  4. Aggregate across rooms: dedup, summarize, present
"""

import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Optional


def _parse_time_expression(query: str) -> tuple:
    """Parse time expressions from natural language query.
    Returns (start_date, end_date) as YYYY-MM-DD strings.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    # "近一周" / "最近7天" / "本周"
    if re.search(r'近[一1]周|最近7天|本周', query):
        start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        return start, today
    # "近一个月" / "最近30天" / "本月"
    if re.search(r'近[一1]个?月|最近30天|本月', query):
        start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        return start, today
    # "昨天"
    if re.search(r'昨天', query):
        return yesterday, yesterday
    # "今天"
    if re.search(r'今天', query):
        return today, today
    # "近3天" / "最近N天"
    m = re.search(r'近(\d+)天|最近(\d+)天', query)
    if m:
        n = int(m.group(1) or m.group(2))
        start = (datetime.now() - timedelta(days=n)).strftime("%Y-%m-%d")
        return start, today
    # Default: last 7 days
    return (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"), today


def _extract_search_keywords(query: str) -> list[str]:
    """Extract meaningful search keywords from the query, excluding time words."""
    # Remove time expressions (longest patterns first!)
    cleaned = re.sub(
        r'最近[一1]个[周月]|最近[一1][周月]|最近\d+天|'
        r'近[一1]个[周月]|近[一1][周月]|近\d+天|'
        r'本周|本月|今天|昨天|最近',
        '', query)
    # Remove common filler
    cleaned = re.sub(r'的|情况|一下|帮我|查|看|分析', '', cleaned)
    # Extract Chinese words >= 2 chars
    words = re.findall(r'[一-鿿]{2,}', cleaned)
    return list(dict.fromkeys(words))  # dedup preserving order


def _match_rooms(km: dict, keywords: list[str], min_match: int = 1) -> list[dict]:
    """Match user keywords against room keywords from knowledge map.
    Returns list of matched rooms with relevance scores.
    """
    base_tables = km.get("base_tables", [])
    matches = []

    for tbl in base_tables:
        if tbl.get("type") != "chat":
            continue
        for room in tbl.get("rooms", []):
            # Collect all keywords from all threads
            all_room_kw = set()
            for th in room.get("threads", []):
                all_room_kw.update(th.get("keywords", []))
            # Also check top users
            for u in room.get("top_users", []):
                all_room_kw.add(u.get("user", ""))

            # Score: how many user keywords match room keywords
            matched = []
            for uk in keywords:
                for rk in all_room_kw:
                    if uk in rk or rk in uk:
                        matched.append(uk)
                        break

            if len(set(matched)) >= min_match:
                matches.append({
                    "roomid": room["roomid"],
                    "msgs": room.get("total_msgs", 0),
                    "users": room.get("user_count", 0),
                    "matched_keywords": list(set(matched)),
                    "score": len(set(matched)),
                    "threads": room.get("threads", []),
                })

    matches.sort(key=lambda x: -x["score"])
    return matches


def _discover_chat_tables(km: dict) -> list[dict]:
    """Discover chat-type Base tables from knowledge map.
    Returns list of {table_name, time_field, user_field, content_field, group_field}.
    """
    tables = []
    time_candidates = ["msgtime", "created_at", "updated_at", "synced_at", "date", "time"]
    user_candidates = ["from_user", "user", "username", "sender", "from"]
    content_candidates = ["content", "text", "message", "body", "msg"]
    group_candidates = ["roomid", "room_id", "group_id", "channel", "room"]

    for tbl in km.get("base_tables", []):
        if tbl.get("type") != "chat":
            continue
        fields = {f["name"]: f for f in tbl.get("fields", [])}

        discovered = {
            "table_name": tbl["table_name"],
            "time_field": None,
            "user_field": None,
            "content_field": None,
            "group_field": None,
        }

        # Discover by pattern matching — prefer exact/first-candidate matches
        def _best_match(fnames: list, candidates: list) -> str | None:
            for candidate in candidates:
                for fname in fnames:
                    if candidate == fname.lower().replace("_", ""):
                        return fname
            for candidate in candidates:
                for fname in fnames:
                    if candidate in fname.lower().replace("_", ""):
                        return fname
            return None

        fnames = list(fields.keys())
        discovered["time_field"] = _best_match(fnames, time_candidates)
        discovered["user_field"] = _best_match(fnames, user_candidates)
        discovered["content_field"] = _best_match(fnames, content_candidates)
        discovered["group_field"] = _best_match(fnames, group_candidates)

        # If room data exists, use roomid from there
        if tbl.get("rooms"):
            discovered["group_field"] = discovered["group_field"] or "roomid"

        if discovered["time_field"] and discovered["content_field"]:
            tables.append(discovered)

    return tables


def _match_rooms(km: dict, keywords: list[str], min_match: int = 1) -> list[dict]:
    """Match user keywords against room keywords from knowledge map.
    Returns list of matched rooms with table_name + group_field for querying.
    """
    matches = []
    chat_tables = _discover_chat_tables(km)

    for tbl in chat_tables:
        table_name = tbl["table_name"]
        group_field = tbl["group_field"] or "roomid"

        # Find the matching Base table entry
        tbl_entry = None
        for bt in km.get("base_tables", []):
            if bt.get("table_name") == table_name:
                tbl_entry = bt
                break
        if not tbl_entry:
            continue

        for room in tbl_entry.get("rooms", []):
            # Collect keywords from threads
            all_room_kw = set()
            for th in room.get("threads", []):
                all_room_kw.update(th.get("keywords", []))
            for u in room.get("top_users", []):
                all_room_kw.add(u.get("user", ""))

            # Match
            matched = []
            for uk in keywords:
                for rk in all_room_kw:
                    if uk in rk or rk in uk:
                        matched.append(uk)
                        break

            if len(set(matched)) >= min_match:
                matches.append({
                    "table_name": table_name,
                    "group_field": group_field,
                    "group_id": room["roomid"],
                    "msgs": room.get("total_msgs", 0),
                    "users": room.get("user_count", 0),
                    "matched_keywords": list(set(matched)),
                    "score": len(set(matched)),
                })

    matches.sort(key=lambda x: -x["score"])
    return matches


def run_analyze(client, query: str, km_path: Optional[str] = None) -> dict:
    """Execute the full intelligent analysis pipeline.

    Dynamically discovers chat tables, group fields, and time fields
    from the knowledge map — no hardcoded field names.
    """
    # 1. Load knowledge map
    if km_path is None:
        km_path = os.path.expanduser("~/.emoo/knowledge_map")
        if os.path.isdir(km_path):
            api_paths = [d for d in os.listdir(km_path)
                        if os.path.isdir(os.path.join(km_path, d))]
            if api_paths:
                km_path = os.path.join(km_path, api_paths[0],
                                       "emoo_knowledge_map.json")

    km = {}
    if os.path.exists(km_path):
        with open(km_path, encoding="utf-8") as f:
            km = json.load(f)

    # 2. Discover chat tables and their fields
    chat_tables = _discover_chat_tables(km)
    if not chat_tables:
        return {"query": query, "keywords": [], "time_range": [], "matched_rooms": [],
                "total": 0, "summary": "未找到聊天表，请先运行 knowledge-map 生成知识图谱"}

    # 3. Parse time + keywords
    start, end = _parse_time_expression(query)
    keywords = _extract_search_keywords(query)

    print(f"🔍 分析: {query}")
    print(f"   关键词: {keywords}")
    print(f"   时间: {start} ~ {end}")
    print(f"   聊天表: {len(chat_tables)} 个")

    # 4. Match rooms across all chat tables
    matched_rooms = _match_rooms(km, keywords) if km else []
    print(f"   匹配群: {len(matched_rooms)} 个")

    # 5. Search matched rooms (fallback to all rooms if none matched)
    all_results = []
    if matched_rooms:
        rooms_searched = matched_rooms[:5]
    else:
        # Fallback: search all known rooms
        print(f"   ⚠️ 无精确匹配群，全局搜索所有聊天群...")
        rooms_searched = []
        for tbl in chat_tables:
            tbl_entry = None
            for bt in km.get("base_tables", []):
                if bt.get("table_name") == tbl["table_name"]:
                    tbl_entry = bt
                    break
            if tbl_entry:
                for room in tbl_entry.get("rooms", []):
                    rooms_searched.append({
                        "table_name": tbl["table_name"],
                        "group_field": tbl["group_field"] or "roomid",
                        "group_id": room["roomid"],
                        "matched_keywords": keywords,
                        "score": 0,
                    })
        rooms_searched = rooms_searched[:5]  # limit to 5 rooms for speed

    # Build a lookup: table_name → discovered fields
    tbl_map = {t["table_name"]: t for t in chat_tables}

    for room in rooms_searched:
        tbl_name = room["table_name"]
        group_field = room["group_field"]
        gid = room["group_id"]
        tbl = tbl_map.get(tbl_name, {})
        time_field = tbl.get("time_field", "msgtime")

        print(f"   搜索 [{tbl_name}] {gid[:20]}... (关联词: {room['matched_keywords']})")

        page = 1
        room_results = []
        api_filters = [
            f"{time_field}:gte:{start}",
            f"{time_field}:lte:{end}",
        ]
        if group_field and gid:
            api_filters.append(f"{group_field}:eq:{gid}")

        # Limit pages for long time ranges (>7 days: 1 page, <=7: 3 pages)
        max_pages = 1 if (datetime.strptime(end, "%Y-%m-%d") - datetime.strptime(start, "%Y-%m-%d")).days > 7 else 3
        try:
            while page <= max_pages:
                resp = client.post("/data/records/list", body={
                    "table_name": tbl_name,
                    "page_size": 100,
                    "current_page": page,
                    "filters": api_filters,
                })
                data = resp.get("data", {})
                recs = data.get("results", [])
                if not recs:
                    break

                # Keyword filter (client-side)
                for r in recs:
                    content = str(r["fields"].get(tbl.get("content_field", "content"), ""))
                    if any(kw in content for kw in keywords):
                        r["_group_field"] = group_field
                        r["_group_id"] = gid
                        r["_table"] = tbl_name
                        room_results.append(r)

                page += 1
                if len(room_results) >= 200:
                    break
        except Exception as e:
            print(f"      ⚠️ 搜索出错: {e}, 跳过此群")

        # Dedup by content
        seen = set()
        unique = []
        for r in room_results:
            c = str(r["fields"].get(tbl.get("content_field", "content"), ""))
            h = hash(c)
            if h not in seen:
                seen.add(h)
                unique.append(r)

        user_field = tbl.get("user_field", "from_user")
        unique.sort(key=lambda r: (r["fields"].get(time_field, ""),
                                    r["fields"].get("seq", 0)))
        all_results.extend(unique)
        print(f"      找到 {len(unique)} 条 (去重后)")

    # 6. Aggregate using discovered fields
    if not all_results:
        return {
            "query": query, "keywords": keywords,
            "time_range": [start, end], "matched_rooms": matched_rooms,
            "total": 0, "summary": "未找到匹配内容",
        }

    # Use the first chat table's field mapping for extraction
    default_tbl = chat_tables[0] if chat_tables else {}
    time_field = default_tbl.get("time_field", "msgtime")
    user_field = default_tbl.get("user_field", "from_user")
    content_field = default_tbl.get("content_field", "content")

    all_results.sort(key=lambda r: (r["fields"].get(time_field, ""),
                                     r["fields"].get("seq", 0)))

    people = Counter(r["fields"].get(user_field, "?") for r in all_results)
    dates = Counter(r["fields"].get(time_field, "")[:10] for r in all_results
                    if r["fields"].get(time_field))

    return {
        "query": query,
        "keywords": keywords,
        "time_range": [start, end],
        "matched_rooms": [{
            "table": r["table_name"],
            "group_id": r["group_id"],
            "score": r["score"],
            "matched_keywords": r["matched_keywords"],
        } for r in matched_rooms[:5]],
        "total": len(all_results),
        "by_date": {d: c for d, c in sorted(dates.items())},
        "top_people": [{"user": u, "count": c} for u, c in people.most_common(10)],
        "samples": [{
            "table": r.get("_table", ""),
            "time": r["fields"].get(time_field, ""),
            "user": r["fields"].get(user_field, ""),
            "content": str(r["fields"].get(content_field, ""))[:200],
            "group": str(r.get("_group_id", ""))[:20],
        } for r in all_results[:20]],
    }

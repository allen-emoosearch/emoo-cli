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
    # Remove time expressions
    cleaned = re.sub(r'最近?[一1]?[周月个]|最近?\d*天|本周|本月|今天|昨天', '', query)
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


def run_analyze(client, query: str, km_path: Optional[str] = None) -> dict:
    """Execute the full intelligent analysis pipeline.

    Args:
        client: EmooClient instance
        query: natural language query
        km_path: path to knowledge map JSON

    Returns:
        dict with keys: query, keywords, time_range, matched_rooms, results, summary
    """
    from .knowledge_map import _extract_keywords as _kw_extract

    # 1. Load knowledge map
    if km_path is None:
        km_path = os.path.expanduser("~/.emoo/knowledge_map")
        # Find most recent namespace
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

    # 2. Parse time + keywords
    start, end = _parse_time_expression(query)
    keywords = _extract_search_keywords(query)

    print(f"🔍 分析: {query}")
    print(f"   关键词: {keywords}")
    print(f"   时间: {start} ~ {end}")

    # 3. Match rooms
    matched_rooms = _match_rooms(km, keywords) if km else []
    print(f"   匹配群: {len(matched_rooms)} 个")

    # 4. Search matched rooms
    all_results = []
    rooms_searched = matched_rooms[:5] if matched_rooms else []  # top 5 rooms

    for room in rooms_searched:
        rid = room["roomid"]
        print(f"   搜索群 {rid[:20]}... (关联词: {room['matched_keywords']})")

        # Build search keywords from matched terms
        search_kw = "|".join(room["matched_keywords"])

        # Fetch records for this room
        page = 1
        room_results = []
        while True:
            resp = client.post("/data/records/list", body={
                "table_name": "企微会话存档",
                "page_size": 100,
                "current_page": page,
                "filters": [
                    f"msgtime:gte:{start}",
                    f"msgtime:lte:{end}",
                    "msgtype:eq:text",
                ],
            })
            data = resp.get("data", {})
            recs = data.get("results", [])
            if not recs:
                break

            # Filter by roomid + keyword
            for r in recs:
                if r.get("fields", {}).get("roomid") != rid:
                    continue
                content = str(r.get("fields", {}).get("content", ""))
                if any(kw in content for kw in keywords):
                    room_results.append(r)

            page += 1
            if not data.get("has_more") and not data.get("total", 0) > page * 100:
                break

        # Dedup by content
        seen = set()
        unique = []
        for r in room_results:
            c = str(r["fields"].get("content", ""))
            h = hash(c)
            if h not in seen:
                seen.add(h)
                unique.append(r)

        unique.sort(key=lambda r: (r["fields"].get("msgtime", ""),
                                    r["fields"].get("seq", 0)))
        all_results.extend(unique)
        print(f"      找到 {len(unique)} 条 (去重后)")

    # 5. Aggregate
    if not all_results:
        return {
            "query": query,
            "keywords": keywords,
            "time_range": [start, end],
            "matched_rooms": matched_rooms,
            "total": 0,
            "summary": "未找到匹配内容",
        }

    all_results.sort(key=lambda r: (r["fields"].get("msgtime", ""),
                                     r["fields"].get("seq", 0)))

    # Extract structured info
    all_text = " ".join(str(r["fields"].get("content", "")) for r in all_results)

    # Key people
    people = Counter(r["fields"].get("from_user", "?") for r in all_results)
    # Dates distribution
    dates = Counter(r["fields"].get("msgtime", "")[:10] for r in all_results
                    if r["fields"].get("msgtime"))

    return {
        "query": query,
        "keywords": keywords,
        "time_range": [start, end],
        "matched_rooms": [{
            "roomid": r["roomid"],
            "score": r["score"],
            "matched_keywords": r["matched_keywords"],
        } for r in matched_rooms[:5]],
        "total": len(all_results),
        "by_date": {d: c for d, c in sorted(dates.items())},
        "top_people": [{"user": u, "count": c} for u, c in people.most_common(10)],
        "samples": [{
            "time": r["fields"].get("msgtime", ""),
            "user": r["fields"].get("from_user", ""),
            "content": str(r["fields"].get("content", ""))[:200],
            "room": r["fields"].get("roomid", "")[:20],
        } for r in all_results[:20]],
    }

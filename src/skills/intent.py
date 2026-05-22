"""Intent analysis: parse natural-language queries against a knowledge map.

Produces a structured search plan JSON that `execute_search_plan` can consume.
"""

import json
import os
import re
from datetime import datetime, timedelta
from typing import Optional


# Topic keyword → (suggested search keyword, preferred doc_group name patterns)
TOPIC_MAP: dict[str, list[tuple[str, list[str]]]] = {
    "营收":  [("营业情况", ["营业情况", "营收", "营业额", "销售数据", "日报"]),
             ("收入", ["收入", "营收"])],
    "营业额": [("营业情况", ["营业情况", "营收", "营业额", "销售数据", "日报"])],
    "销售":  [("营业情况", ["营业情况", "销售数据"]),
             ("销售方案", ["销售方案", "打折方案"])],
    "员工":  [("员工", ["员工", "人员", "人事", "考勤", "工资", "排班"])],
    "人事":  [("员工", ["员工", "人员", "人事", "考勤"])],
    "工资":  [("员工", ["工资", "薪酬", "绩效"])],
    "品项":  [("品项", ["品项", "菜品", "菜单", "做法"]),
             ("套餐", ["套餐"])],
    "菜品":  [("品项", ["品项", "菜品", "菜单"])],
    "库存":  [("供应链", ["供应链", "库存", "进货", "采购"])],
    "制度":  [("管理制度", ["制度", "政策", "规定", "流程", "手册"])],
    "政策":  [("管理制度", ["制度", "政策", "规定"])],
    "门店":  [("门店", ["门店", "店铺", "分店"]),
             ("营业情况", ["营业情况", "营收", "营业额"])],
}


def _parse_time(query: str) -> dict:
    """Extract time range from Chinese natural language.

    Returns {"from": "YYYY-MM-DD", "to": "YYYY-MM-DD"} or None if no time found.
    """
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # "2026年3月" or "2026年03月"
    m = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月', query)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        return {"from": f"{y}-{mo:02d}-01",
                "to": f"{y}-{mo:02d}-{_days_in_month(y, mo):02d}"}

    # "3月" (current year)
    m = re.search(r'(?<!\d)(\d{1,2})\s*月', query)
    if m:
        mo = int(m.group(1))
        y = now.year
        return {"from": f"{y}-{mo:02d}-01",
                "to": f"{y}-{mo:02d}-{_days_in_month(y, mo):02d}"}

    # "3月15日" or "3月15号"
    m = re.search(r'(?<!\d)(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]', query)
    if m:
        mo, d = int(m.group(1)), int(m.group(2))
        y = now.year
        return {"from": f"{y}-{mo:02d}-{d:02d}",
                "to": f"{y}-{mo:02d}-{d:02d}"}

    # "最近N天"
    m = re.search(r'最近\s*(\d+)\s*天', query)
    if m:
        n = int(m.group(1))
        return {"from": (today - timedelta(days=n)).strftime("%Y-%m-%d"),
                "to": today.strftime("%Y-%m-%d")}

    # "今天"
    if "今天" in query:
        return {"from": today.strftime("%Y-%m-%d"), "to": today.strftime("%Y-%m-%d")}

    # "昨天"
    if "昨天" in query:
        d = today - timedelta(days=1)
        return {"from": d.strftime("%Y-%m-%d"), "to": d.strftime("%Y-%m-%d")}

    # "上周"
    if "上周" in query:
        # Monday of last week → Sunday of last week
        days_since_monday = today.weekday()
        last_monday = today - timedelta(days=days_since_monday + 7)
        last_sunday = last_monday + timedelta(days=6)
        return {"from": last_monday.strftime("%Y-%m-%d"),
                "to": last_sunday.strftime("%Y-%m-%d")}

    # "本周"
    if "本周" in query:
        days_since_monday = today.weekday()
        this_monday = today - timedelta(days=days_since_monday)
        return {"from": this_monday.strftime("%Y-%m-%d"),
                "to": today.strftime("%Y-%m-%d")}

    # "这个月" / "本月"
    if "这个月" in query or "本月" in query:
        return {"from": f"{now.year}-{now.month:02d}-01",
                "to": today.strftime("%Y-%m-%d")}

    # "上个月" / "上月"
    if "上个月" in query or "上月" in query:
        if now.month == 1:
            y, mo = now.year - 1, 12
        else:
            y, mo = now.year, now.month - 1
        return {"from": f"{y}-{mo:02d}-01",
                "to": f"{y}-{mo:02d}-{_days_in_month(y, mo):02d}"}

    return {}


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (datetime(year, month + 1, 1) - timedelta(days=1)).day


def _extract_entities(query: str) -> dict:
    """Extract non-time entities from query: store names, topics, people."""
    # Remove time expressions to get cleaner entities
    cleaned = query
    for pat in [r'\d{4}\s*年\s*\d{1,2}\s*月', r'(?<!\d)\d{1,2}\s*月\s*\d{1,2}\s*[日号]',
                r'(?<!\d)\d{1,2}\s*月', r'最近\s*\d+\s*天',
                r'今天|昨天|明天|上周|本周|下周|这个月|本月|上个月|上月']:
        cleaned = re.sub(pat, '', cleaned)

    # Remove common filler words
    cleaned = re.sub(r'[的了吗呢啊查看看一下帮我找下搜索查询]', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # Detect topic keywords first (longer keywords first to avoid partial matches)
    topics = []
    topic_kws = sorted(TOPIC_MAP.keys(), key=len, reverse=True)
    for kw in topic_kws:
        if kw in cleaned:
            topics.append(kw)

    # Split tokens at topic keyword boundaries so "示例门店店营收" → "示例门店店"
    remaining = cleaned
    for kw in topics:
        remaining = remaining.replace(kw, ' ')

    # Tokenize remaining by separators
    tokens = [t.strip() for t in re.split(r'[，,、\s]+', remaining) if t.strip() and len(t.strip()) >= 2]

    # Build entity names — try to find multi-token store names
    names = tokens

    return {"names": names, "topics": topics}


def _score_match(query_tokens: list[str], target: str) -> float:
    """Score how well query tokens match a target string.  Returns 0.0 to 1.0."""
    if not target:
        return 0.0
    target_lower = target.lower()
    hits = 0
    for token in query_tokens:
        if token.lower() in target_lower:
            # Longer token matches are worth more
            hits += 1
        else:
            # Check partial character overlap (for fuzzy Chinese matching)
            overlap = sum(1 for c in token if c in target_lower)
            if overlap >= min(2, len(token)):
                hits += 0.5
    if not query_tokens:
        return 0.0
    return hits / len(query_tokens)


def analyze_intent(
    query: str,
    knowledge_map_path: str = "emoo_knowledge_map.json",
) -> dict:
    """Analyze user query against a knowledge map and produce a search plan.

    Args:
        query: natural-language search intent (e.g. "查示例门店店3月营收")
        knowledge_map_path: path to the JSON knowledge map file

    Returns:
        search plan dict with intent, entities, and plan steps
    """
    time_range = _parse_time(query)
    entities = _extract_entities(query)
    entities["time_range"] = time_range if time_range else None

    # Load knowledge map
    if not os.path.exists(knowledge_map_path):
        return {
            "intent": query,
            "entities": entities,
            "plan": [],
            "error": f"知识图谱文件不存在: {knowledge_map_path}\n"
                     f"请先运行: emoo skill knowledge-map"
        }

    with open(knowledge_map_path, encoding="utf-8") as f:
        km = json.load(f)

    apps = km.get("apps", [])
    if not apps:
        return {"intent": query, "entities": entities, "plan": [],
                "error": "知识图谱中没有应用数据"}

    query_tokens = entities.get("names", [])
    topics = entities.get("topics", [])
    all_tokens = query_tokens + topics

    # Build search plan steps with confidence scoring
    candidates = []

    for app in apps:
        ws_app_key = app.get("ws_app_key", "")
        app_title = app.get("title", "")

        # Score app-level match
        app_score = _score_match(all_tokens, app_title) if all_tokens else 0.1

        # Score against sample titles
        sample_score = max(
            (_score_match(all_tokens, t) for t in app.get("sample_titles", [])),
            default=0.0
        )

        # Score each doc group
        for dg in app.get("doc_groups", []):
            gname = dg.get("app_group_name", "")
            dg_score = _score_match(all_tokens, gname)

            # Also check topic mapping
            topic_boost = 0.0
            for topic in topics:
                for search_kw, patterns in TOPIC_MAP.get(topic, []):
                    if any(p in gname for p in patterns):
                        topic_boost = max(topic_boost, 0.5)

            # Check if any sample titles in this group match
            dg_sample_score = max(
                (_score_match(all_tokens, t) for t in dg.get("sample_titles", [])),
                default=0.0
            )

            combined = max(app_score * 0.3 + dg_score * 0.4 + dg_sample_score * 0.3,
                           dg_score, app_score) + topic_boost

            if combined > 0.0 or dg.get("doc_count", 0) > 0:
                candidates.append({
                    "ws_app_key": ws_app_key,
                    "ws_app_title": app_title,
                    "doc_group_id": dg.get("app_group_id", ""),
                    "doc_group_name": gname,
                    "doc_count": dg.get("doc_count", 0),
                    "confidence": min(combined, 1.0),
                })

        # If no doc groups, add app-level entry
        if not app.get("doc_groups"):
            if app_score > 0 or sample_score > 0 or app.get("doc_count", 0) > 0:
                candidates.append({
                    "ws_app_key": ws_app_key,
                    "ws_app_title": app_title,
                    "doc_group_id": "",
                    "doc_group_name": "",
                    "doc_count": app.get("doc_count", 0),
                    "confidence": max(app_score, sample_score),
                })

    # Sort by confidence, deduplicate
    candidates.sort(key=lambda x: (-x["confidence"], -x["doc_count"]))

    # Build plan steps
    plan = []
    seen_keys = set()
    step = 0

    for c in candidates:
        if c["confidence"] < 0.05 and step >= 3:
            continue  # Skip very low confidence if we already have decent matches

        dedup_key = (c["ws_app_key"], c["doc_group_id"])
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        step += 1
        keyword_parts = query_tokens.copy()

        # Add topic-mapped keywords
        for topic in topics:
            for search_kw, patterns in TOPIC_MAP.get(topic, []):
                if any(p in c["doc_group_name"] for p in patterns):
                    if search_kw not in keyword_parts:
                        keyword_parts.append(search_kw)

        filters = [[
            {"field": "ws_app.ws_app_key", "operator": "eq", "value": c["ws_app_key"]},
        ]]

        if c["doc_group_id"]:
            filters[0].append(
                {"field": "doc_group.app_group_id", "operator": "eq",
                 "value": c["doc_group_id"]}
            )

        if time_range:
            filters[0].append(
                {"field": "app_created_at", "operator": "gte",
                 "value": time_range["from"] + "T00:00:00+08:00"},
            )
            filters[0].append(
                {"field": "app_created_at", "operator": "lte",
                 "value": time_range["to"] + "T23:59:59+08:00"},
            )

        reason_parts = []
        if c["confidence"] >= 0.7:
            reason_parts.append(f"高匹配度({c['confidence']:.0%})")
        if c["doc_group_name"]:
            reason_parts.append(f"文档组'{c['doc_group_name']}'")
        reason_parts.append(f"{c['doc_count']}篇文档")

        plan.append({
            "step": step,
            "ws_app_key": c["ws_app_key"],
            "ws_app_title": c["ws_app_title"],
            "doc_group_id": c["doc_group_id"],
            "doc_group_name": c["doc_group_name"],
            "keyword": " ".join(keyword_parts),
            "filters": filters,
            "page_size": 200,
            "current_page": 1,
            "match_reason": "；".join(reason_parts),
            "confidence": round(c["confidence"], 2),
        })

    return {
        "intent": query,
        "entities": entities,
        "plan": plan,
    }

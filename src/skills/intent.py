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

    # "最近N天 / 近N周 / 近N个月"
    m = re.search(r'(?:最近|近)\s*(\d+)\s*(天|周|个月|月)', query)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        if unit == "天":
            start = today - timedelta(days=n)
        elif unit == "周":
            start = today - timedelta(days=n * 7)
        else:
            start = _months_ago(today, n)
        return {"from": start.strftime("%Y-%m-%d"), "to": today.strftime("%Y-%m-%d")}

    # "近一周 / 近一个月 / 近半年 / 近一年"
    for words, days in (
        (("近一周", "最近一周", "近7天"), 7),
        (("近一个月", "最近一个月", "近1个月", "近30天"), 30),
        (("近半年", "最近半年", "近6个月"), 182),
        (("近一年", "最近一年", "近12个月"), 365),
    ):
        if any(w in query for w in words):
            return {"from": (today - timedelta(days=days)).strftime("%Y-%m-%d"),
                    "to": today.strftime("%Y-%m-%d")}

    # "本季度" / "上个季度"
    if "本季度" in query or "这个季度" in query:
        q_start_month = ((now.month - 1) // 3) * 3 + 1
        return {"from": f"{now.year}-{q_start_month:02d}-01",
                "to": today.strftime("%Y-%m-%d")}
    if "上个季度" in query or "上季度" in query:
        q_index = (now.month - 1) // 3  # 0-based current quarter
        if q_index == 0:
            y, start_month = now.year - 1, 10
        else:
            y, start_month = now.year, (q_index - 1) * 3 + 1
        end_month = start_month + 2
        return {"from": f"{y}-{start_month:02d}-01",
                "to": f"{y}-{end_month:02d}-{_days_in_month(y, end_month):02d}"}

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


def _months_ago(reference: datetime, months: int) -> datetime:
    year = reference.year
    month = reference.month - months
    while month <= 0:
        month += 12
        year -= 1
    day = min(reference.day, _days_in_month(year, month))
    return reference.replace(year=year, month=month, day=day)


def _extract_entities(query: str) -> dict:
    """Extract non-time entities from query: store names, topics, people."""
    # Remove time expressions to get cleaner entities
    cleaned = query
    for pat in [r'\d{4}\s*年\s*\d{1,2}\s*月', r'(?<!\d)\d{1,2}\s*月\s*\d{1,2}\s*[日号]',
                r'(?<!\d)\d{1,2}\s*月', r'(?:最近|近)\s*\d+\s*(?:天|周|个月|月)',
                r'近一周|近一个月|近一年|近半年|最近一周|最近一个月|最近一年|最近半年',
                r'本季度|这个季度|上个季度|上季度',
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


# ── Aggregate intent (KM v2) ────────────────────────────────────────────────

_METRIC_KEYWORDS = {
    "avg": ["平均", "均值", "人均", "客单价"],
    "max": ["最高", "最大", "最贵", "峰值"],
    "min": ["最低", "最小", "最便宜", "谷值"],
    "values": ["有哪些", "枚举", "去重", "列表"],
    "sum": ["合计", "总额", "总计", "总和", "累计", "营收", "销售额",
            "总金额", "金额合计", "总花费", "支出", "总额度"],
    "count": ["多少", "数量", "个数", "条数", "几笔", "单量", "单数", "笔数", "次数"],
}
_RANKING_WORDS = ["排名", "排行", "前几", "top", "最多", "最少"]
_TREND_WORDS = ["趋势", "走势", "变化", "按月", "每月", "逐月", "按天", "每日",
                "按周", "每周", "按季度", "每季度", "按年", "每年"]
_TIME_INTERVAL = [
    (["按天", "每日", "每天", "逐日"], "day"),
    (["按周", "每周", "逐周"], "week"),
    (["按月", "每月", "逐月"], "month"),
    (["按季度", "每季度", "逐季"], "quarter"),
    (["按年", "每年", "逐年"], "year"),
]
_STOP_WORDS = set("""
查 查询 统计 汇总 计算 看看 一下 帮我 找 搜索 数据 情况 所有 全部 的 了 吗 呢 啊
合计 总额 总计 总和 累计 平均 均值 最高 最大 最低 最小 多少 数量 个数 条数 几笔
单量 单数 笔数 次数 排名 排行 前几 top 最多 最少 趋势 走势 变化 按月 每月 逐月
按天 每日 按周 每周 按季度 每季度 按年 每年 各 按 每个 分 额
""".split())


def _detect_metric_intent(query: str) -> Optional[dict]:
    """Detect a statistical/aggregate intent from the query.

    Returns None when the query looks like a normal document search.
    """
    q = query.lower()
    interval = None
    for words, unit in _TIME_INTERVAL:
        if any(w in query for w in words):
            interval = unit
            break

    is_trend = interval is not None or any(w in query for w in ("趋势", "走势", "变化"))
    is_ranking = any(w.lower() in q for w in _RANKING_WORDS) or bool(re.search(r"前\s*\d+", query))

    metric_type = None
    if is_trend:
        metric_type = "sum" if any(w in query for w in ("金额", "总额", "营收", "销售额", "数量", "消费")) else "count"
    elif is_ranking:
        metric_type = "sum" if any(w in query for w in ("金额", "总额", "营收", "销售额", "数量", "消费")) else "count"
    else:
        for name in ("avg", "max", "min", "values", "sum", "count"):
            if any(w in query for w in _METRIC_KEYWORDS[name]):
                metric_type = name
                break

    if metric_type is None:
        return None

    # Field hints: entities + metric synonyms.
    entity_names = _extract_entities(query).get("names", [])
    hints = [h for h in entity_names if h and h not in _STOP_WORDS]
    if "营收" in query or "营业额" in query:
        hints += ["营收", "收入", "销售额", "营业额", "金额"]
    if any(w in query for w in ("金额", "总额", "花费", "支出")):
        hints += ["金额", "含税金额", "总金额", "实付金额", "应付金额", "总额"]
    if "数量" in query or "销量" in query:
        hints += ["数量", "收货数量", "采购数量", "销售数量", "库存数量", "销量"]
    if "单价" in query:
        hints += ["单价", "价格"]
    if "客单价" in query or "人均" in query:
        hints += ["客单价", "人均消费", "人均"]
    if "毛利" in query:
        hints += ["毛利", "毛利额", "毛利率"]
    if "成本" in query:
        hints += ["成本", "成本额"]
    hints = list(dict.fromkeys(h for h in hints if h not in _STOP_WORDS))

    # Group hint: 各门店 / 按部门 / 分供应商.
    group_hint = None
    known_groups = ("门店", "部门", "供应商", "客户", "员工", "仓库", "档口",
                    "品类", "分类", "状态", "物料", "区域", "菜品", "订单", "项目")
    for cand in known_groups:
        if f"各{cand}" in query or f"按{cand}" in query or f"每个{cand}" in query:
            group_hint = cand
            break
    if not group_hint:
        m = re.search(
            r"(?:各|按|每个|分)([一-龥A-Za-z0-9_]{1,10}?)"
            r"(?:的|采购|销售|金额|数量|合计|统计|汇总|排名|趋势|变化|$)",
            query,
        )
        if m:
            group_hint = m.group(1)
    if not group_hint:
        for cand in known_groups:
            if cand in query:
                group_hint = cand
                break

    context_hints: list[str] = []
    for words, contexts in (
        (("订单", "单据", "单量", "单数", "笔数"), ["订单", "单据", "采购单", "销售单", "收货单"]),
        (("采购", "进货", "供应商"), ["采购", "进货", "供应商", "收货"]),
        (("销售", "营收", "营业额", "营业"), ["销售", "营业", "营收", "订单"]),
        (("员工", "人事", "考勤"), ["员工", "人事", "考勤"]),
        (("菜品", "菜单"), ["菜品", "菜单", "销售"]),
        (("会员", "储值", "卡"), ["会员", "储值", "卡"]),
    ):
        if any(w in query for w in words):
            context_hints.extend(contexts)
    context_hints = list(dict.fromkeys(context_hints))

    return {
        "metric_type": metric_type,
        "field_hints": hints,
        "group_hint": group_hint,
        "context_hints": context_hints,
        "interval": interval,
        "ranking": is_ranking,
        "trend": is_trend,
    }


def _field_score(field: dict, hints: list[str]) -> float:
    path = (field.get("path") or "").lower()
    name = (field.get("name") or "").lower()
    text = f"{path} {name}"
    score = 0.0
    for hint in hints:
        h = hint.lower().strip()
        if not h:
            continue
        if path == h:
            score += 4
        elif name == h and ".*." not in path:
            score += 4
        elif h in text:
            score += 2
        elif text and text in h:
            score += 1
    return score


def _metric_field_bonus(path: str) -> float:
    """Prefer primary amounts/revenue over discounts, tax and cost fields."""
    bonus = 0.0
    if re.search(r"(优惠|折扣|退款|退单|退货|税额|运费|成本|毛利)", path):
        bonus -= 2.0
    if re.search(r"(实收|应收|应付|总计|总额|总金额|销售金额|消费|营业额|营收|收入|销售额)$", path):
        bonus += 0.5
    return bonus


def _pick_numeric_field(fields: list[dict], hints: list[str]) -> Optional[dict]:
    candidates = [f for f in fields if f.get("type") in ("number", "mixed")]
    if not candidates:
        return None
    scored = sorted(
        candidates,
        key=lambda f: (
            -(_field_score(f, hints) + _metric_field_bonus(f.get("path") or "")),
            1 if ".*." in (f.get("path") or "") else 0,
            f.get("path", ""),
        ),
    )
    best = scored[0]
    return best if _field_score(best, hints) > 0 else None


def _group_field_bonus(path: str) -> float:
    """Prefer human-readable dimensions over IDs/codes."""
    bonus = 0.0
    if re.search(r"(ID|Id|id|编号|编码|code|Code|_no)$", path):
        bonus -= 2.0
    if re.search(r"(名称|姓名|描述|类型|状态|分类|品类|区域|供应商)$", path):
        bonus += 1.0
    return bonus


def _pick_group_field(fields: list[dict], hints: list[str]) -> Optional[dict]:
    candidates = [
        f for f in fields
        if f.get("type") in ("string", "mixed")
        and 0 < f.get("distinct_count", 0) <= 80
        and (f.get("path") or "").count(".*.") <= 1
    ]
    if not candidates:
        return None
    scored = sorted(
        candidates,
        key=lambda f: (
            -(_field_score(f, hints) + _group_field_bonus(f.get("path") or "")),
            1 if ".*." in (f.get("path") or "") else 0,
            -f.get("distinct_count", 0),
            f.get("path", ""),
        ),
    )
    best = scored[0]
    # With a hint, require some match; without one, accept the low-cardinality field.
    if hints and _field_score(best, hints) <= 0:
        return None
    return best


def _pick_date_field(fields: list[dict]) -> Optional[dict]:
    candidates = [f for f in fields if f.get("type") in ("date", "datetime")]
    if not candidates:
        return None
    scored = sorted(
        candidates,
        key=lambda f: (
            0 if any(k in (f.get("path") or "") for k in ("日期", "时间", "date", "time")) else 1,
            1 if ".*." in (f.get("path") or "") else 0,
            f.get("path", ""),
        ),
    )
    return scored[0]


def _build_aggregate_step(metric: dict, app: dict, doc_group: dict,
                          filters: list, query_tokens: list[str],
                          confidence: float) -> Optional[dict]:
    fields = doc_group.get("fields") or app.get("fields") or []
    if not fields:
        return None

    metric_type = metric["metric_type"]
    metric_field = None
    group_field = None
    interval = None

    if metric["trend"]:
        date_field = _pick_date_field(fields)
        if not date_field:
            return None
        group_field = date_field
        interval = metric.get("interval") or "month"
        metric_field = _pick_numeric_field(fields, metric["field_hints"])
        if metric_field is None:
            metric_type = "count"
        else:
            metric_type = "sum"
    elif metric_type == "values":
        metric_field = _pick_numeric_field(fields, metric["field_hints"]) or _pick_group_field(
            fields, metric["field_hints"])
        if not metric_field:
            return None
    else:
        if metric_type in ("sum", "avg", "max", "min"):
            metric_field = _pick_numeric_field(fields, metric["field_hints"])
            if not metric_field:
                return None
        if metric["group_hint"] or metric["ranking"]:
            group_field = _pick_group_field(fields, [metric["group_hint"]] if metric["group_hint"] else query_tokens)
            if not group_field:
                return None

    step = {
        "step": 0,
        "type": "aggregate",
        "ws_app_key": app.get("ws_app_key", ""),
        "ws_app_title": app.get("title", ""),
        "doc_group_id": doc_group.get("app_group_id", ""),
        "doc_group_name": doc_group.get("app_group_name", ""),
        "metric_type": metric_type,
        "metric_field": metric_field.get("path") if metric_field else None,
        "group_by_field": group_field.get("path") if group_field else None,
        "group_by_interval": interval,
        "filters": filters,
        "max_groups": 50,
        "max_values": 200,
        "match_reason": "",
        "confidence": round(confidence, 2),
    }

    reason = [f"{metric_type}"]
    if step["metric_field"]:
        reason.append(f"字段={step['metric_field']}")
    if step["group_by_field"]:
        reason.append(f"分组={step['group_by_field']}")
    if interval:
        reason.append(f"按{interval}")
    if doc_group.get("app_group_name"):
        reason.append(f"文档组'{doc_group['app_group_name']}'")
    step["match_reason"] = "；".join(reason)
    return step


def _build_aggregate_plan(metric: dict, apps: list[dict], candidates: list[dict],
                          time_range: dict, query_tokens: list[str]) -> list[dict]:
    candidate_keys = {
        (c.get("ws_app_key", ""), c.get("doc_group_id", ""))
        for c in candidates[:20]
    }
    scored: list[tuple[float, int, dict]] = []
    context_scored: list[tuple[float, int, dict]] = []
    context_hints = metric.get("context_hints") or []

    for app in apps:
        ws_app_key = app.get("ws_app_key", "")
        for dg in app.get("doc_groups", []):
            if not dg.get("fields"):
                continue

            filters = [[
                {"field": "ws_app.ws_app_key", "operator": "eq", "value": ws_app_key},
            ]]
            if dg.get("app_group_id"):
                filters[0].append(
                    {"field": "doc_group.app_group_id", "operator": "eq",
                     "value": dg["app_group_id"]}
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

            step = _build_aggregate_step(
                metric, app, dg, filters, query_tokens, 0.0
            )
            if not step:
                continue

            name_text = f"{app.get('title', '')} {dg.get('app_group_name', '')}"
            confidence = _score_match(query_tokens, name_text)
            if metric.get("group_hint") and metric["group_hint"] in name_text:
                confidence += 0.2
            is_context_match = any(h in name_text for h in context_hints)
            if is_context_match:
                confidence += 0.2
            if (ws_app_key, dg.get("app_group_id", "")) in candidate_keys:
                confidence += 0.1
            if step.get("metric_field"):
                confidence += 0.1
            if step.get("group_by_field"):
                confidence += 0.1
            step["confidence"] = round(min(confidence, 1.0), 2)
            bucket = context_scored if is_context_match else scored
            bucket.append((step["confidence"], dg.get("doc_count", 0), step))

    chosen = context_scored or scored
    chosen.sort(key=lambda item: (-item[0], -item[1]))
    return [step for _, _, step in chosen[:3]]


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
    metric = _detect_metric_intent(query)
    if metric:
        entities["metric_intent"] = metric

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

    aggregate_plan = []
    if metric:
        aggregate_plan = _build_aggregate_plan(
            metric, apps, candidates, time_range, query_tokens + topics
        )
        if not aggregate_plan:
            metric["note"] = "未在知识图谱字段中找到匹配的聚合字段，已回退为文档搜索"

    combined = aggregate_plan if aggregate_plan else plan
    for i, item in enumerate(combined, 1):
        item["step"] = i

    result = {
        "intent": query,
        "entities": entities,
        "query_type": "aggregate" if aggregate_plan else "search",
        "plan": combined,
    }
    if aggregate_plan:
        # Keep the document-search plan available for callers that want details.
        for i, item in enumerate(plan, 1):
            item["step"] = i
        result["fallback_plan"] = plan
    return result

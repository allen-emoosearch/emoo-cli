"""Skill runner: execute a parsed SkillDef against the EMOO API.

Flow: template substitution → app/doc_group name resolution → search → CSV export.
"""

import csv
import json
import os
import re
from datetime import datetime, timedelta
from typing import Any, Optional

from .loader import SkillDef

API_RESULT_CAP = 500


def _resolve_knowledge_map(km_path: str = "emoo_knowledge_map.json") -> Optional[dict]:
    """Load knowledge map JSON if it exists."""
    if os.path.exists(km_path):
        with open(km_path, encoding="utf-8") as f:
            return json.load(f)
    return None


def _match_app(knowledge_map: dict, app_name: str) -> Optional[str]:
    """Find ws_app_key by fuzzy-matching app title in knowledge map."""
    apps = knowledge_map.get("apps", [])
    # Exact match
    for a in apps:
        if a.get("title") == app_name:
            return a["ws_app_key"]
    # Substring match
    for a in apps:
        if app_name in a.get("title", ""):
            return a["ws_app_key"]
    return None


def _match_doc_group(knowledge_map: dict, ws_app_key: str,
                     group_name: str) -> Optional[str]:
    """Find app_group_id by fuzzy-matching doc group name within an app."""
    apps = knowledge_map.get("apps", [])
    for a in apps:
        if a.get("ws_app_key") != ws_app_key:
            continue
        for dg in a.get("doc_groups", []):
            if dg.get("app_group_name") == group_name:
                return dg["app_group_id"]
            if group_name in dg.get("app_group_name", ""):
                return dg["app_group_id"]
    return None


def _substitute(template: str, params: dict[str, str], defaults: dict[str, str]) -> str:
    """Replace {param} placeholders with values, using defaults for missing."""
    merged = {}
    for pname, pdef in defaults.items():
        default_val = pdef.get("default")
        if default_val is not None:
            merged[pname] = str(default_val)
    merged.update(params)

    result = template
    for key, val in merged.items():
        result = result.replace(f"{{{key}}}", str(val))
    return result.strip()


def _build_time_filters(time_str: str) -> list[dict]:
    """Build time filter conditions from a time string like '2026-03' or '2026-03-15'.

    '2026-03' → whole month range
    '2026-03-15' → single day
    '最近N天' → last N days (relative to today)
    """
    # "最近N天"
    m = re.match(r'最近(\d+)天', time_str)
    if m:
        n = int(m.group(1))
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start = today - timedelta(days=n)
        return [
            {"field": "app_created_at", "operator": "gte",
             "value": start.strftime("%Y-%m-%d") + "T00:00:00+08:00"},
            {"field": "app_created_at", "operator": "lte",
             "value": today.strftime("%Y-%m-%d") + "T23:59:59+08:00"},
        ]

    # "YYYY-MM-DD"
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', time_str)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return [
            {"field": "app_created_at", "operator": "gte",
             "value": f"{y}-{mo:02d}-{d:02d}T00:00:00+08:00"},
            {"field": "app_created_at", "operator": "lte",
             "value": f"{y}-{mo:02d}-{d:02d}T23:59:59+08:00"},
        ]

    # "YYYY-MM"
    m = re.match(r'^(\d{4})-(\d{2})$', time_str)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        last_day = 31
        if mo == 12:
            last_day = 31
        else:
            last_day = (datetime(y, mo + 1, 1) - timedelta(days=1)).day
        return [
            {"field": "app_created_at", "operator": "gte",
             "value": f"{y}-{mo:02d}-01T00:00:00+08:00"},
            {"field": "app_created_at", "operator": "lte",
             "value": f"{y}-{mo:02d}-{last_day:02d}T23:59:59+08:00"},
        ]

    # Unrecognized format — return empty (no time filter)
    return []


def run_skill(client, skill: SkillDef, user_params: dict[str, str],
              knowledge_map_path: str = "emoo_knowledge_map.json",
              max_results: int = 200) -> dict:
    """Execute a skill definition against the EMOO API.

    Args:
        client: EmooClient instance
        skill: parsed SkillDef
        user_params: user-provided parameter values
        knowledge_map_path: path to knowledge map JSON for name resolution
        max_results: max results to return

    Returns:
        dict with keys: skill_name, keyword, params, results[], total, errors[]
    """
    outcome = {
        "skill_name": skill.name,
        "keyword": "",
        "params": user_params,
        "results": [],
        "total": 0,
        "errors": [],
    }

    # Step 1: template substitution
    keyword = _substitute(skill.keyword, user_params, skill.params)
    outcome["keyword"] = keyword

    # Step 2: resolve app + doc_group names from knowledge map
    km = _resolve_knowledge_map(knowledge_map_path)
    ws_app_key = None
    doc_group_id = None

    if skill.app_name and km:
        ws_app_key = _match_app(km, skill.app_name)
        if not ws_app_key:
            outcome["errors"].append(f"未在知识图谱中找到应用: {skill.app_name}")

    if skill.doc_group_name and ws_app_key and km:
        doc_group_id = _match_doc_group(km, ws_app_key, skill.doc_group_name)
        if not doc_group_id:
            outcome["errors"].append(
                f"未在应用 {skill.app_name} 中找到文档组: {skill.doc_group_name}"
            )

    # Step 3: build filter conditions
    filters = []

    if ws_app_key:
        inner = [{"field": "ws_app.ws_app_key", "operator": "eq", "value": ws_app_key}]
        if doc_group_id:
            inner.append({
                "field": "doc_group.app_group_id", "operator": "eq",
                "value": doc_group_id,
            })
        filters.append(inner)  # avoid empty inner list

    # Static filters from skill def
    if skill.filters:
        if isinstance(skill.filters, list) and skill.filters:
            if isinstance(skill.filters[0], dict) and "field" in skill.filters[0]:
                # Flat dict list → append to inner if it exists
                if filters:
                    filters[0].extend(skill.filters)
                else:
                    filters.append(list(skill.filters))
            elif isinstance(skill.filters[0], list):
                filters.extend(skill.filters)

    # Step 4: time range from params (map_to: time_range)
    for pname, pdef in skill.params.items():
        if pdef.get("map_to") == "time_range":
            val = user_params.get(pname) or pdef.get("default")
            if val:
                time_filters = _build_time_filters(str(val))
                if time_filters and filters:
                    filters[0].extend(time_filters)
                elif time_filters:
                    filters.append(time_filters)

    # Step 5: execute search with auto-pagination
    page_size = min(skill.page_size, 200)
    body: dict[str, Any] = {
        "keyword": keyword,
        "page_size": min(page_size, max_results),
        "current_page": 1,
        "text_format": "plain",
    }
    if filters:
        body["filter_conditions"] = filters

    all_results: list[dict] = []
    api_total = 0
    page = 1

    try:
        while True:
            body["current_page"] = page
            resp = client.post("/search", body=body)
            data = resp.get("data", {})
            results = data.get("results", [])
            api_total = data.get("total", 0)

            if not results:
                break

            all_results.extend(results)

            if len(all_results) >= max_results:
                all_results = all_results[:max_results]
                break

            if len(all_results) >= api_total or len(results) < body["page_size"]:
                break

            page += 1

        outcome["results"] = all_results
        outcome["total"] = len(all_results)

        if page > 1:
            outcome["_paginated"] = True

        if api_total == API_RESULT_CAP and len(all_results) >= API_RESULT_CAP:
            outcome["_truncated"] = True
            outcome["errors"].append(
                f"search 端点硬上限 {API_RESULT_CAP} 条，自动翻页也无法突破。"
                f"建议用 emoo data get (游标翻页无此限制) 配合日期过滤分段拉取。"
            )
    except Exception as e:
        outcome["errors"].append(f"搜索执行失败: {e}")

    return outcome


def export_skill_csv(outcome: dict, csv_path: str) -> str:
    """Export skill run results to CSV."""
    results = outcome.get("results", [])
    if not results:
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            f.write("")
        return csv_path

    all_keys = set()
    for r in results:
        all_keys.update(r.keys())

    priority = ["title", "url", "app_created_at", "app_updated_at"]
    ordered = [k for k in priority if k in all_keys]
    remaining = sorted(all_keys - set(ordered))
    ordered += remaining

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(ordered)
        for r in results:
            row = []
            for k in ordered:
                v = r.get(k, "")
                if isinstance(v, (dict, list)):
                    v = json.dumps(v, ensure_ascii=False)
                row.append(v)
            writer.writerow(row)

    return csv_path

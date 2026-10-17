"""Search plan executor: run multi-step app searches and aggregate results."""

import csv
import json
import os
from typing import Optional


def _execute_aggregate_step(client, pstep: dict) -> dict:
    """Execute one aggregate plan step against /search/aggregate."""
    body = {
        "metric_type": pstep.get("metric_type", "count"),
        "metric_field": pstep.get("metric_field"),
        "group_by_field": pstep.get("group_by_field"),
        "group_by_interval": pstep.get("group_by_interval"),
        "max_groups": pstep.get("max_groups", 50),
        "max_values": pstep.get("max_values", 200),
        "filter_conditions": pstep.get("filters") or None,
    }
    body = {k: v for k, v in body.items() if v not in (None, "", [])}
    resp = client.post("/search/aggregate", body=body)
    return resp.get("data", {})


def execute_search_plan(
    client,
    plan: dict,
    step: Optional[int] = None,
    max_per_step: int = 200,
    fallback: bool = False,
):
    """Execute a search plan and return aggregated results.

    Args:
        client: EmooClient instance
        plan: search plan dict (from intent analysis or hand-crafted)
        step: execute only this step (None = all steps)
        max_per_step: max results per step (page_size)

    Args:
        fallback: when aggregate steps return no buckets, execute
            plan["fallback_plan"] (document search) automatically.

    Returns:
        dict with keys: intent, steps_executed, total_results, results[],
        aggregates[], errors[]
    """
    plan_steps = plan.get("plan", [])
    if not plan_steps:
        return {"intent": plan.get("intent", ""), "steps_executed": 0,
                "total_results": 0, "results": [], "aggregates": [],
                "errors": ["搜索方案中没有 plan 步骤"]}

    outcome = {
        "intent": plan.get("intent", ""),
        "entities": plan.get("entities", {}),
        "steps_executed": 0,
        "total_results": 0,
        "results": [],
        "aggregates": [],
        "errors": [],
    }

    for pstep in plan_steps:
        idx = pstep.get("step", 0)
        if step is not None and idx != step:
            continue

        step_type = pstep.get("type", "search")
        if step_type == "aggregate":
            try:
                data = _execute_aggregate_step(client, pstep)
                data["_step"] = idx
                data["_app_title"] = pstep.get("ws_app_title", "")
                data["_doc_group_name"] = pstep.get("doc_group_name", "")
                data["_metric_type"] = pstep.get("metric_type", "")
                data["_metric_field"] = pstep.get("metric_field")
                data["_group_by_field"] = pstep.get("group_by_field")
                outcome["aggregates"].append(data)
                outcome["steps_executed"] += 1
            except Exception as e:
                outcome["errors"].append(f"Step {idx} (aggregate): {e}")
            continue

        body = {
            "keyword": pstep.get("keyword", ""),
            "page_size": min(pstep.get("page_size", max_per_step), max_per_step),
            "current_page": pstep.get("current_page", 1),
            "text_format": pstep.get("text_format", "plain"),
        }

        filters = pstep.get("filters", [])
        if filters:
            body["filter_conditions"] = filters

        try:
            resp = client.post("/search", body=body)
            data = resp.get("data", {})
            step_results = data.get("results", [])
            total = data.get("total", len(step_results))

            for r in step_results:
                r["_step"] = idx
                r["_app_title"] = pstep.get("ws_app_title", "")
                r["_doc_group_name"] = pstep.get("doc_group_name", "")
                r["_match_reason"] = pstep.get("match_reason", "")

            outcome["results"].extend(step_results)
            outcome["steps_executed"] += 1

            # Fetch remaining pages if needed
            total_pages = data.get("total_pages", 1)
            current_page = body["current_page"]
            while total_pages > current_page and len(step_results) < max_per_step:
                current_page += 1
                body["current_page"] = current_page
                resp = client.post("/search", body=body)
                more = resp.get("data", {}).get("results", [])
                for r in more:
                    r["_step"] = idx
                    r["_app_title"] = pstep.get("ws_app_title", "")
                    r["_doc_group_name"] = pstep.get("doc_group_name", "")
                    r["_match_reason"] = pstep.get("match_reason", "")
                step_results.extend(more)
                # Stop if server says no more pages
                if not resp.get("data", {}).get("has_more"):
                    break

            outcome["total_results"] += len(step_results)

        except Exception as e:
            outcome["errors"].append(f"Step {idx}: {e}")

    if fallback and not outcome["results"]:
        has_useful_agg = any(
            agg.get("buckets") and not agg.get("note")
            for agg in outcome["aggregates"]
        )
        fallback_steps = plan.get("fallback_plan") or []
        if not has_useful_agg and fallback_steps:
            fb_plan = {"intent": plan.get("intent", ""), "plan": fallback_steps}
            fb = execute_search_plan(client, fb_plan, max_per_step=max_per_step)
            outcome["results"] = fb["results"]
            outcome["total_results"] = fb["total_results"]
            outcome["steps_executed"] += fb["steps_executed"]
            outcome["errors"].extend(fb["errors"])
            outcome["_fallback_used"] = True

    return outcome


def export_results_csv(outcome: dict, csv_path: str) -> str:
    """Export search results to CSV.  Handles both flat dicts and nested JSON content.

    Returns path to the generated CSV file.
    """
    results = outcome.get("results", [])
    if not results:
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            f.write("")
        return csv_path

    # Collect all keys
    all_keys = set()
    for r in results:
        all_keys.update(r.keys())

    # Prioritize important columns
    priority = ["title", "url", "_app_title", "_doc_group_name",
                "app_created_at", "app_updated_at", "_step", "_match_reason"]
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


def export_aggregates_csv(outcome: dict, csv_path: str) -> str:
    """Export aggregate buckets to CSV (one row per bucket)."""
    rows: list[dict] = []
    for agg in outcome.get("aggregates", []) or []:
        common = {
            "_step": agg.get("_step", ""),
            "_app_title": agg.get("_app_title", ""),
            "_doc_group_name": agg.get("_doc_group_name", ""),
            "_metric_type": agg.get("_metric_type", ""),
            "_metric_field": agg.get("_metric_field") or "",
            "_group_by_field": agg.get("_group_by_field") or "",
            "total_docs": agg.get("total_docs", 0),
            "truncated": agg.get("truncated", False),
        }
        buckets = agg.get("buckets") or []
        if not buckets:
            rows.append({**common, "key": "", "doc_count": agg.get("total_docs", 0),
                         "metric_value": "", "values": ""})
            continue
        for bucket in buckets:
            rows.append({
                **common,
                "key": bucket.get("key", ""),
                "doc_count": bucket.get("doc_count", ""),
                "metric_value": bucket.get("metric_value", ""),
                "values": json.dumps(bucket.get("values"), ensure_ascii=False)
                if bucket.get("values") is not None else "",
            })

    columns = ["_step", "_app_title", "_doc_group_name", "_metric_type",
               "_metric_field", "_group_by_field", "key", "doc_count",
               "metric_value", "values", "total_docs", "truncated"]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        for row in rows:
            writer.writerow([row.get(c, "") for c in columns])
    return csv_path

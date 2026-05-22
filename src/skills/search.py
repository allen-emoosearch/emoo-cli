"""Search plan executor: run multi-step app searches and aggregate results."""

import csv
import json
import os
from typing import Optional


def execute_search_plan(
    client,
    plan: dict,
    step: Optional[int] = None,
    max_per_step: int = 200,
):
    """Execute a search plan and return aggregated results.

    Args:
        client: EmooClient instance
        plan: search plan dict (from intent analysis or hand-crafted)
        step: execute only this step (None = all steps)
        max_per_step: max results per step (page_size)

    Returns:
        dict with keys: intent, steps_executed, total_results, results[], errors[]
    """
    plan_steps = plan.get("plan", [])
    if not plan_steps:
        return {"intent": plan.get("intent", ""), "steps_executed": 0,
                "total_results": 0, "results": [], "errors": ["搜索方案中没有 plan 步骤"]}

    outcome = {
        "intent": plan.get("intent", ""),
        "entities": plan.get("entities", {}),
        "steps_executed": 0,
        "total_results": 0,
        "results": [],
        "errors": [],
    }

    for pstep in plan_steps:
        idx = pstep.get("step", 0)
        if step is not None and idx != step:
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

"""Knowledge map generation: scan all apps + doc groups, sample content titles.

Produces two output files in the output directory:
  - emoo_knowledge_map.json  (machine-readable, consumed by intent analysis)
  - emoo_knowledge_map.md    (human-readable summary)
"""

import json
import os
import time
from typing import Optional


def _sample_titles(client, ws_app_key: str, doc_group_id: str,
                   group_name: str = "", limit: int = 5) -> list[str]:
    """Sample document titles from a doc group by searching with its group_id."""
    # Use group name (or first char) as keyword — the API requires non-empty keyword
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
    }

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

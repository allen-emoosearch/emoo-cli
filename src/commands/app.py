"""App overview: scan workspace and generate knowledge map of ws_app_key content."""

import time
from collections import defaultdict

import click

from ..client import EmooClient


@click.group()
@click.pass_context
def app(ctx):
    """应用与 Agent 管理 (浏览、概览)."""
    ctx.ensure_object(dict)


@app.command()
@click.option("--max-docs", default=500, help="扫描文档上限 (默认 500)")
@click.option("--output-file", "-o", default="emoo_knowledge_map.md", help="输出 Markdown 文件")
@click.pass_context
def overview(ctx, max_docs, output_file):
    """遍历文档，按 ws_app_key 分组生成知识地图，方便搜索前定位数据源。"""
    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))

    app_docs: dict[str, list[dict]] = {}
    total = 0
    cursor = ""
    page_size = 200

    click.echo(f"正在扫描文档 (每页 {page_size}, 上限 {max_docs})...")

    while total < max_docs:
        resp = client.post("/data", body={
            "page_size": page_size,
            "cursor": cursor,
            "text_format": "plain",
        })
        inner = resp.get("data", {})
        results = inner.get("results", [])

        for r in results:
            wa = r.get("ws_app", {})
            key = wa.get("ws_app_key", "")
            if key:
                if key not in app_docs:
                    app_docs[key] = []
                app_docs[key].append({
                    "title": r.get("title", ""),
                    "app_name": wa.get("app_name", ""),
                    "app_title": wa.get("title", ""),
                    "app_id": wa.get("id", ""),
                    "updated_at": r.get("app_updated_at", ""),
                })

        total += len(results)
        click.echo(f"  已扫描 {total} 篇...")

        if not inner.get("has_more") or not inner.get("next_cursor"):
            break
        cursor = inner["next_cursor"]

    click.echo(f"\n扫描完成: 共 {total} 篇文档, {len(app_docs)} 个 ws_app_key")

    # Build summaries
    app_summaries = []
    for key, docs in sorted(app_docs.items(), key=lambda x: -len(x[1])):
        titles = [d["title"] for d in docs[:20] if d["title"]]
        info = docs[0]
        app_summaries.append({
            "ws_app_key": key,
            "app_name": info["app_name"],
            "app_title": info["app_title"],
            "doc_count": len(docs),
            "sample_titles": titles[:10],
        })

    # Generate markdown
    gen_time = time.strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# EMOO 工作区知识地图",
        "",
        f"> 生成时间: {gen_time}  |  文档总数: {total}  |  ws_app_key 数: {len(app_summaries)}",
        "",
        "## 快速索引",
        "",
        "| ws_app_key | 应用名称 | 平台 | 文档数 | 主要内容 |",
        "|-----------|---------|------|--------|---------|",
    ]
    for s in app_summaries:
        key_short = s["ws_app_key"][:12] + "..."
        sample = "、".join(s["sample_titles"][:3]) if s["sample_titles"] else "—"
        lines.append(f"| {key_short} | {s['app_title']} | {s['app_name']} | {s['doc_count']} | {sample} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 各应用详情")
    lines.append("")

    for s in app_summaries:
        lines.append(f"### {s['app_title']}")
        lines.append("")
        lines.append(f"- **ws_app_key**: `{s['ws_app_key']}`")
        lines.append(f"- **平台**: {s['app_name']}")
        lines.append(f"- **文档数**: {s['doc_count']}")
        lines.append("")
        lines.append("**示例文档**:")
        lines.append("")
        for t in s["sample_titles"]:
            lines.append(f"- {t}")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("## 搜索建议")
    lines.append("")
    lines.append("在 `emoo data search` 中使用 `-f` 过滤 ws_app_key 缩小范围:")
    lines.append("")
    lines.append("```bash")
    for s in app_summaries[:5]:
        lines.append(f"# {s['app_title']}")
        lines.append(f"emoo data search -k \"关键词\" \\")
        lines.append(f"  -f '{{\"field\":\"ws_app.ws_app_key\",\"operator\":\"eq\",\"value\":\"{s['ws_app_key']}\"}}'")
        lines.append("")
    lines.append("```")

    with open(output_file, "w") as f:
        f.write("\n".join(lines))

    click.echo(f"知识地图已生成: {output_file}")

    # Print summary
    from rich.console import Console
    from rich.table import Table
    console = Console()
    table = Table(title="ws_app_key 概览")
    table.add_column("ws_app_key", style="cyan")
    table.add_column("应用名称")
    table.add_column("平台")
    table.add_column("文档数", justify="right")
    table.add_column("示例内容")
    for s in app_summaries:
        sample = s["sample_titles"][0] if s["sample_titles"] else "—"
        table.add_row(s["ws_app_key"], s["app_title"], s["app_name"], str(s["doc_count"]), sample[:60])
    console.print(table)


@app.command()
@click.pass_context
def list(ctx):
    """列出所有 ws_app_key。ws_agent_key 需在管理后台获取。"""
    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))

    seen: dict[str, dict] = {}
    cursor = ""
    scan_count = 0

    while scan_count < 600:
        resp = client.post("/data", body={"page_size": 200, "cursor": cursor, "text_format": "plain"})
        inner = resp.get("data", {})
        results = inner.get("results", [])

        for r in results:
            wa = r.get("ws_app", {})
            key = wa.get("ws_app_key", "")
            if key and key not in seen:
                seen[key] = {
                    "title": wa.get("title", ""),
                    "app_name": wa.get("app_name", ""),
                    "app_id": wa.get("id", ""),
                }

        scan_count += len(results)
        if not inner.get("has_more") or not inner.get("next_cursor"):
            break
        cursor = inner["next_cursor"]

    click.echo(f"\n发现 {len(seen)} 个 ws_app_key (扫描 {scan_count} 篇):\n")

    from rich.console import Console
    from rich.table import Table
    console = Console()
    table = Table(title="工作区应用 (ws_app_key)")
    table.add_column("ws_app_key", style="cyan")
    table.add_column("应用名称")
    table.add_column("平台")
    table.add_column("ws_app.id")
    for key in sorted(seen):
        info = seen[key]
        table.add_row(key, info["title"], info["app_name"], str(info["app_id"]))
    console.print(table)

    click.echo("\n[dim]ws_agent_key 需在 EMOO 管理后台 → Agent 管理 → 复制 Agent Key[/dim]")

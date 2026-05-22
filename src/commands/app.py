"""App overview: scan workspace and generate knowledge map of ws_app_key content."""

import time
from collections import defaultdict

import click

from ..client import EmooClient


def _progress(msg: str, **kwargs) -> None:
    """Write progress/info to stderr so stdout stays clean for JSON consumers."""
    click.echo(msg, err=True, **kwargs)


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

    _progress(f"正在扫描文档 (每页 {page_size}, 上限 {max_docs})...")

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
        _progress(f"  已扫描 {total} 篇...")

        if not inner.get("has_more") or not inner.get("next_cursor"):
            break
        cursor = inner["next_cursor"]

    _progress(f"\n扫描完成: 共 {total} 篇文档, {len(app_docs)} 个 ws_app_key")

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

    _progress(f"知识地图已生成: {output_file}")

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

    resp = client.get("/apps")
    apps = resp.get("data", [])

    if ctx.obj.get("as_json"):
        import json
        click.echo(json.dumps(apps, ensure_ascii=False, indent=2))
        return

    from rich.console import Console
    from rich.table import Table
    console = Console()
    table = Table(title="工作区应用 (ws_app_key)")
    table.add_column("ws_app_key", style="cyan")
    table.add_column("应用名称")
    table.add_column("文档组数", justify="right")
    table.add_column("文档数", justify="right")
    table.add_column("ws_app.id")
    for a in sorted(apps, key=lambda x: x.get("title", "")):
        table.add_row(
            a.get("ws_app_key", ""),
            a.get("title", ""),
            str(a.get("doc_group_count", "")),
            str(a.get("doc_count", "")),
            str(a.get("id", "")),
        )
    console.print(table)

    click.echo(f"\n共 {len(apps)} 个应用")
    click.echo("\n[dim]ws_agent_key 需在 EMOO 管理后台 → Agent 管理 → 复制 Agent Key[/dim]")


@app.command()
@click.option("--ws-app-key", "-k", required=True, help="ws_app_key (必填)")
@click.option("--page-size", default=100, help="每页数量 (默认 100, 最大 200)")
@click.option("--current-page", default=1, help="当前页码 (默认 1)")
@click.pass_context
def doc_groups(ctx, ws_app_key, page_size, current_page):
    """列出应用的文档组 (GET /v1/app/{ws_app_key}/doc-groups)."""
    if page_size > 200:
        raise click.BadParameter("page_size 最大 200")
    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))

    resp = client.get(f"/app/{ws_app_key}/doc-groups", params={
        "page_size": page_size,
        "current_page": current_page,
    })

    data = resp.get("data", {})
    results = data.get("results", [])
    total = data.get("total", len(results))

    if ctx.obj.get("as_json"):
        import json
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
        return

    from rich.console import Console
    from rich.table import Table
    console = Console()
    table = Table(title=f"文档组 (ws_app_key={ws_app_key})")
    table.add_column("app_group_id", style="cyan")
    table.add_column("名称")
    table.add_column("描述")
    table.add_column("文档数", justify="right")
    table.add_column("更新时间")
    for g in results:
        table.add_row(
            g.get("app_group_id", ""),
            g.get("app_group_name", ""),
            (g.get("app_group_desc") or "")[:60],
            str(g.get("doc_count", "")),
            (g.get("updated_at") or "")[:19],
        )
    console.print(table)

    click.echo(f"\n第 {current_page}/{data.get('total_pages', 1)} 页, 共 {total} 个文档组")

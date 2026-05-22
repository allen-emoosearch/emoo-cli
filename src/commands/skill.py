"""Skill commands: adaptive search pipeline (knowledge-map → intent → search)."""

import json
import os
import sys

import click

from ..client import EmooClient
from ..formatters import output
from ..skills import generate_knowledge_map, analyze_intent, execute_search_plan
from ..skills.search import export_results_csv


@click.group()
def skill():
    """自适应搜索技能 (知识图谱 → 意图分析 → 方案执行).

    三段式智能搜索流水线，自动适配不同客户的数据环境:
      knowledge-map  生成增强知识图谱 (JSON + MD)
      intent         分析搜索意图，输出搜索方案
      search         执行搜索方案，聚合多 app 结果
    """


@skill.command()
@click.option("--max-sample-per-group", default=5, help="每个文档组采样标题数 (默认5)")
@click.option("--max-doc-groups", default=200, help="最大采样文档组数 (默认200)")
@click.option("-o", "--output-dir", default=".", help="输出目录 (默认当前目录)")
@click.pass_context
def knowledge_map(ctx, max_sample_per_group, max_doc_groups, output_dir):
    """生成增强知识图谱，包含每个 app 的文档组详情和内容采样.

    输出两个文件:
      emoo_knowledge_map.json  — 机器可读 (供 intent 使用)
      emoo_knowledge_map.md    — 人类可读摘要

    \b
    示例:
      emoo skill knowledge-map
      emoo skill knowledge-map --max-sample-per-group 10 -o /tmp
    """
    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))

    click.echo("正在扫描工作区应用...")
    json_path = generate_knowledge_map(
        client,
        max_sample_per_group=max_sample_per_group,
        max_doc_groups=max_doc_groups,
        output_dir=output_dir,
    )

    # Load and display summary
    with open(json_path, encoding="utf-8") as f:
        km = json.load(f)

    apps = km.get("apps", [])
    total_docs = sum(a.get("doc_count", 0) for a in apps)
    total_groups = sum(len(a.get("doc_groups", [])) for a in apps)

    click.echo(f"\n知识图谱已生成:")
    click.echo(f"  JSON: {os.path.abspath(json_path)}")
    click.echo(f"  MD:   {os.path.abspath(os.path.join(output_dir, 'emoo_knowledge_map.md'))}")
    click.echo(f"  应用数: {len(apps)}")
    click.echo(f"  文档组数: {total_groups}")
    click.echo(f"  文档总数: {total_docs}")

    if ctx.obj.get("as_json"):
        click.echo(json.dumps(km, ensure_ascii=False, indent=2))
    else:
        from rich.console import Console
        from rich.table import Table
        console = Console()
        table = Table(title="应用概览")
        table.add_column("#", justify="right")
        table.add_column("应用名称")
        table.add_column("文档组数", justify="right")
        table.add_column("文档数", justify="right")
        table.add_column("示例内容")
        for i, a in enumerate(apps, 1):
            samples = "、".join(a.get("sample_titles", [])[:2]) or "—"
            table.add_row(str(i), a["title"],
                          str(len(a.get("doc_groups", []))),
                          str(a.get("doc_count", 0)),
                          samples[:60])
        console.print(table)


@skill.command()
@click.argument("query")
@click.option("-k", "--knowledge-map", "km_path", default="emoo_knowledge_map.json",
              help="知识图谱 JSON 路径 (默认 ./emoo_knowledge_map.json)")
@click.option("--top", default=5, help="最多输出几个搜索步骤 (默认5)")
@click.option("-o", "--output", "output_file", default=None, help="保存搜索方案到文件")
@click.pass_context
def intent(ctx, query, km_path, top, output_file):
    """分析搜索意图，输出结构化搜索方案.

    QUERY: 自然语言查询，如 "查美罗城店3月营收"

    \b
    示例:
      emoo skill intent "查美罗城店2026年3月营收"
      emoo skill intent "上周品项销售情况" --top 3
      emoo skill intent "最近7天员工考勤" -o plan.json
    """
    result = analyze_intent(query, knowledge_map_path=km_path)

    if result.get("error"):
        click.echo(f"[错误] {result['error']}", err=True)
        if "请先运行" in result.get("error", ""):
            raise click.UsageError(result["error"])
        return

    plan = result.get("plan", [])
    plan = plan[:top]

    if ctx.obj.get("as_json"):
        result["plan"] = plan
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        console = Console()

        # Entities
        entities = result.get("entities", {})
        ent_lines = []
        if entities.get("names"):
            ent_lines.append(f"  实体名称: {', '.join(entities['names'])}")
        if entities.get("topics"):
            ent_lines.append(f"  主题: {', '.join(entities['topics'])}")
        if entities.get("time_range"):
            tr = entities["time_range"]
            ent_lines.append(f"  时间: {tr.get('from', '')} ~ {tr.get('to', '')}")
        if ent_lines:
            console.print(Panel("\n".join(ent_lines), title="提取的实体"))

        # Search plan
        if not plan:
            console.print("[dim]未找到匹配的搜索方案，请检查知识图谱是否覆盖了查询内容[/dim]")
            return

        table = Table(title=f"搜索方案 ({len(plan)} 步)")
        table.add_column("步骤", justify="right")
        table.add_column("应用", style="cyan")
        table.add_column("文档组")
        table.add_column("关键词")
        table.add_column("置信度", justify="right")
        table.add_column("匹配理由")

        for p in plan:
            table.add_row(
                str(p["step"]),
                p["ws_app_title"],
                p.get("doc_group_name", "—") or "—",
                p["keyword"],
                f"{p['confidence']:.0%}",
                p.get("match_reason", ""),
            )
        console.print(table)

        # Search command hints
        console.print("\n[bold]可直接执行:[/bold]")
        for p in plan:
            filters_str = json.dumps(p["filters"], ensure_ascii=False)
            console.print(
                f"  [dim]# 步骤{p['step']}: {p['ws_app_title']} — {p.get('match_reason', '')}[/dim]\n"
                f"  emoo data search -k \"{p['keyword']}\" -f '{filters_str}'"
            )

    if output_file:
        result["plan"] = plan
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        click.echo(f"\n搜索方案已保存: {output_file}")


@skill.command()
@click.option("-p", "--plan-file", required=True,
              help="搜索方案 JSON 文件路径 (使用 '-' 从 stdin 读取)")
@click.option("--step", type=int, default=None, help="只执行某一步")
@click.option("--max-per-step", default=200, help="每步最多返回结果数 (默认200)")
@click.option("--csv", "csv_path", default=None, help="导出 CSV 文件路径")
@click.pass_context
def search(ctx, plan_file, step, max_per_step, csv_path):
    """执行搜索方案，聚合多 app 结果.

    接收 intent 命令输出的搜索方案 JSON，按顺序执行多应用搜索并聚合结果。

    \b
    示例:
      emoo skill search -p plan.json
      emoo skill search -p plan.json --csv output.csv
      emoo skill search -p plan.json --step 1
      emoo skill intent "营收" | emoo skill search -p -
    """
    # Load plan
    if plan_file == "-":
        plan = json.load(sys.stdin)
    elif os.path.exists(plan_file):
        with open(plan_file, encoding="utf-8") as f:
            plan = json.load(f)
    else:
        raise click.BadParameter(f"搜索方案文件不存在: {plan_file}")

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))

    click.echo(f"意图: {plan.get('intent', 'N/A')}")
    steps = plan.get("plan", [])
    if step is not None:
        steps = [s for s in steps if s.get("step") == step]
    click.echo(f"执行 {len(steps)} 个搜索步骤...")

    outcome = execute_search_plan(client, plan, step=step, max_per_step=max_per_step)

    if ctx.obj.get("as_json"):
        click.echo(json.dumps(outcome, ensure_ascii=False, indent=2))
    else:
        from rich.console import Console
        from rich.table import Table
        console = Console()

        if outcome.get("errors"):
            for err in outcome["errors"]:
                console.print(f"[red]错误: {err}[/red]")

        results = outcome.get("results", [])
        if not results:
            console.print("[dim]无结果[/dim]")
        else:
            console.print(f"\n共 {outcome['total_results']} 条结果 ({outcome['steps_executed']} 个步骤)")

            table = Table(title="搜索结果")
            table.add_column("#", justify="right")
            table.add_column("来源", style="cyan")
            table.add_column("标题")
            table.add_column("更新时间")
            for i, r in enumerate(results[:50], 1):
                table.add_row(
                    str(i),
                    r.get("_app_title", ""),
                    (r.get("title", "") or "")[:60],
                    (r.get("app_updated_at", "") or "")[:16],
                )
            console.print(table)

            if len(results) > 50:
                console.print(f"[dim]... 还有 {len(results) - 50} 条结果[/dim]")

    if csv_path:
        path = export_results_csv(outcome, csv_path)
        click.echo(f"CSV 已导出: {path}")

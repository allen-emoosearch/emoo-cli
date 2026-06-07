"""Skill commands: MD-driven adaptive search + Claude Code integration."""

import json
import os
import sys
import time

import click

from ..client import EmooClient
from ..formatters import output, _progress


def _default_km_namespace() -> str:
    """Get the KM namespace prefix for current workspace."""
    cfg = {}
    try:
        with open(os.path.expanduser("~/.emoo/config.json")) as f:
            cfg = json.load(f)
    except Exception:
        pass
    return (cfg.get("api_key") or cfg.get("client_id", "default"))[:12]


def _default_km_path() -> str:
    """Resolve the default knowledge map path, namespaced by API key."""
    cfg = {}
    try:
        with open(os.path.expanduser("~/.emoo/config.json")) as f:
            cfg = json.load(f)
    except Exception:
        pass
    api_prefix = (cfg.get("api_key", "") or cfg.get("client_id", "default"))[:12]
    return os.path.expanduser(f"~/.emoo/knowledge_map/{api_prefix}/emoo_knowledge_map.json")


from ..skills import generate_knowledge_map, analyze_intent, execute_search_plan
from ..skills.analyze import run_analyze
from ..skills.search import export_results_csv
from ..skills.loader import (
    load_all_skills, find_skill, validate_params,
)
from ..skills.runner import run_skill, export_skill_csv
from ..skills.registry import (
    ensure_skills_dir, register_symlink, is_registered, unregister,
)


# ── template for `emoo skill create` ────────────────────────────────────────

SKILL_TEMPLATE = """---
name: {name}
description: {description}
type: {skill_type}
category: {category}
tags: []
emoo:
  search:
    keyword: "{keyword}"
    page_size: 200
  params:
    keyword:
      description: 搜索关键词
      required: false
---

# {name}

## 使用方式

```bash
emoo skill run {name} --keyword "关键词"
```
"""

# ── top-level skill group ───────────────────────────────────────────────────

@click.group()
def skill():
    """MD 驱动的自适应搜索技能 + Claude Code 集成.

    一份 MD，两处运行 — skill 文件既是 Claude Code 能加载的 skill，也是 CLI 能执行的搜索模板.

    \b
    快速开始:
      emoo skill init                 初始化 + 注册到 Claude Code
      emoo skill list                 列出所有 skill
      emoo skill run <name>           执行 skill 搜索
      emoo skill pipeline knowledge-map  生成知识图谱
    """


# ── init ────────────────────────────────────────────────────────────────────

@skill.command()
@click.option("--no-register", is_flag=True, help="只创建目录，不注册到 Claude Code")
def init(no_register):
    """初始化 skills 目录并注册到 Claude Code.

    创建当前工作区专属 skills 目录: ~/.emoo/skills/<workspace>/
    建立 symlink: ~/.claude/skills/emoo/ → ~/.emoo/skills/<workspace>/

    注册后，Claude Code 即可加载当前工作区的 emoo skill 文件。
    \b
    提示: 使用 emoo skill create <name> 创建新 skill。
    """
    skills_dir = ensure_skills_dir()
    click.echo(f"Skills 目录: {skills_dir}")

    # Install built-in search guide skill
    import shutil
    pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # src/
    guide_src = os.path.join(pkg_dir, "skills", "emoo-search-guide.md")
    if not os.path.exists(guide_src):
        # Fallback: check relative to CWD (development mode)
        guide_src = os.path.join(os.getcwd(), "src", "skills", "emoo-search-guide.md")
    guide_dst = os.path.join(skills_dir, "emoo-search-guide.md")
    if os.path.exists(guide_src):
        shutil.copy2(guide_src, guide_dst)
        click.echo("已安装搜索指南: emoo-search-guide")

    if no_register:
        click.echo("\n已跳过 Claude Code 注册 (--no-register)")
        return

    ok, msg = register_symlink()
    if ok:
        click.echo(f"\n{msg}")
    else:
        click.echo(f"\n[警告] {msg}", err=True)

    click.echo("\n使用 emoo skill list 查看所有 skill")
    click.echo("使用 emoo skill run <name> 执行 skill")
    click.echo("\n💡 下一步: emoo skill pipeline knowledge-map  (生成知识图谱，1-2分钟)")


# ── register ────────────────────────────────────────────────────────────────

@skill.command()
@click.option("--unregister", "do_unregister", is_flag=True, help="取消注册")
def register(do_unregister):
    """注册/刷新 emoo skills 到 Claude Code.

    默认创建 symlink: ~/.claude/skills/emoo/ → ~/.emoo/skills/
    使用 --unregister 可取消注册。
    """
    if do_unregister:
        ok, msg = unregister()
        click.echo(msg if ok else f"[错误] {msg}", err=not ok)
        return

    if is_registered():
        click.echo(f"已注册: ~/.claude/skills/emoo/ → ~/.emoo/skills/")
    else:
        ok, msg = register_symlink()
        click.echo(msg if ok else f"[错误] {msg}", err=not ok)


# ── list ────────────────────────────────────────────────────────────────────

@skill.command("list")
@click.option("--category", "-c", default=None, help="按分类过滤")
@click.option("--type", "type_filter", default=None,
              help="按类型过滤 (scenario|dimension)")
@click.pass_context
def list_skills(ctx, category, type_filter):
    """列出所有已安装的 skill."""
    skills = load_all_skills()

    if category:
        skills = [s for s in skills if s.category == category]
    if type_filter:
        skills = [s for s in skills if s.type == type_filter]

    if ctx.obj.get("as_json"):
        click.echo(json.dumps([s.to_dict() for s in skills], ensure_ascii=False, indent=2))
        return

    if not skills:
        click.echo(f"[dim]Skills 目录为空 ({ensure_skills_dir()})[/dim]")
        click.echo("使用 emoo skill create <name> 创建新 skill")
        return

    from rich.console import Console
    from rich.table import Table

    # Group by category
    by_cat: dict[str, list] = {}
    for s in skills:
        by_cat.setdefault(s.category, []).append(s)

    console = Console()
    for cat, items in sorted(by_cat.items()):
        table = Table(title=f"📁 {cat} ({len(items)})", width=100)
        table.add_column("名称", style="cyan")
        table.add_column("类型")
        table.add_column("描述")
        table.add_column("参数")
        for s in items:
            type_tag = "[green]场景[/green]" if s.type == "scenario" else "[blue]维度[/blue]"
            param_names = ", ".join(s.params.keys()) if s.params else "—"
            table.add_row(s.name, type_tag, s.description[:50], param_names)
        console.print(table)
        console.print()


# ── show ────────────────────────────────────────────────────────────────────

@skill.command()
@click.argument("name")
@click.option("--params-only", is_flag=True, help="仅显示参数说明")
@click.pass_context
def show(ctx, name, params_only):
    """显示 skill 的完整 MD 内容和参数说明.

    NAME: skill 名称 (文件名或 frontmatter name)
    """
    sd = find_skill(name)
    if not sd:
        raise click.BadParameter(f"未找到 skill: {name}")

    if params_only or ctx.obj.get("as_json"):
        click.echo(json.dumps(sd.to_dict(), ensure_ascii=False, indent=2))
        return

    # Print the raw MD content with syntax highlighting
    with open(sd.filepath, encoding="utf-8") as f:
        content = f.read()

    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    console = Console()

    console.print(Panel(
        f"[bold]{sd.name}[/bold]  [dim]{sd.filepath}[/dim]",
        title="Skill 详情",
    ))

    # Show frontmatter summary
    console.print(f"[bold]类型:[/bold] {sd.type}  |  "
                  f"[bold]分类:[/bold] {sd.category}  |  "
                  f"[bold]CSV导出:[/bold] {'是' if sd.csv_export else '否'}")
    console.print(f"[bold]搜索关键词:[/bold] {sd.keyword}")
    if sd.app_name:
        console.print(f"[bold]目标应用:[/bold] {sd.app_name}")
    if sd.doc_group_name:
        console.print(f"[bold]文档组:[/bold] {sd.doc_group_name}")
    console.print()

    # Render markdown body
    md = Markdown(content)
    console.print(md)


# ── run ─────────────────────────────────────────────────────────────────────

@skill.command(context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
@click.argument("name")
@click.option("--csv", "csv_path", default=None, help="导出 CSV 文件路径")
@click.option("--max-results", default=200, help="最大结果数 (默认200)")
@click.option("-k", "--knowledge-map", "km_path", default=None,
              help="知识图谱路径 (默认 ~/.emoo/knowledge_map/emoo_knowledge_map.json)")
@click.pass_context
def run(ctx, name, csv_path, max_results, km_path):
    """执行 skill 搜索.

    NAME: skill 名称
    其他参数通过 --param value 格式传递，与 skill 定义的参数对应.

    \b
    示例:
      emoo skill run store-revenue --store "示例门店" --month "2026-03"
      emoo skill run store-revenue --store "示例门店" --csv output.csv
      emoo skill run item-analysis --item "红烧肉" --month "2026-03"
    """
    sd = find_skill(name)
    if not sd:
        raise click.BadParameter(f"未找到 skill: {name}")

    # Parse extra args (--param value pairs collected via allow_extra_args)
    params = {}
    extra_args = list(ctx.args)
    i = 0
    while i < len(extra_args):
        arg = extra_args[i]
        if arg.startswith("--"):
            key = arg[2:]
            if "=" in key:
                k, v = key.split("=", 1)
                params[k] = v
                i += 1
            elif i + 1 < len(extra_args) and not extra_args[i + 1].startswith("--"):
                params[key] = extra_args[i + 1]
                i += 2
            else:
                params[key] = "true"
                i += 1
        else:
            i += 1

    # Validate
    errors = validate_params(sd, params)
    if errors:
        for e in errors:
            click.echo(f"[错误] {e}", err=True)
        raise click.UsageError("参数校验失败，请检查后重试")

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))

    if km_path is None:
        default_km = _default_km_path()
        if os.path.exists(default_km):
            km_path = default_km

    _progress(f"执行 skill: {sd.name}")

    outcome = run_skill(client, sd, params, knowledge_map_path=km_path, max_results=max_results)

    if outcome.get("errors"):
        for err in outcome["errors"]:
            click.echo(f"[警告] {err}", err=True)

    if ctx.obj.get("as_json"):
        click.echo(json.dumps(outcome, ensure_ascii=False, indent=2))
    else:
        results = outcome.get("results", [])
        if not results:
            click.echo(f"无结果 — 关键词: '{outcome['keyword']}'")
            return

        flags = ""
        if outcome.get("_paginated"):
            flags += " | 自动翻页"
        if outcome.get("_truncated"):
            flags += " | ⚠ 已达API硬上限"
        click.echo(f"\n关键词: '{outcome['keyword']}' | 共 {outcome['total']} 条结果{flags}")

        from rich.console import Console
        from rich.table import Table
        console = Console()

        table = Table(title="搜索结果")
        table.add_column("#", justify="right")
        table.add_column("标题")
        table.add_column("创建时间")
        for i, r in enumerate(results[:50], 1):
            table.add_row(
                str(i),
                (r.get("title", "") or "")[:70],
                (r.get("app_created_at", "") or "")[:16],
            )
        console.print(table)

        if len(results) > 50:
            console.print(f"[dim]... 还有 {len(results) - 50} 条结果[/dim]")

    if csv_path:
        path = export_skill_csv(outcome, csv_path)
        _progress(f"CSV 已导出: {path}")
    elif sd.csv_export:
        csv_name = f"{sd.name}_{outcome['keyword'][:20]}.csv"
        path = export_skill_csv(outcome, csv_name)
        _progress(f"CSV 已自动导出: {path}")


# ── create ──────────────────────────────────────────────────────────────────

@skill.command()
@click.argument("name")
@click.option("--description", "-d", default="", help="一句话描述")
@click.option("--category", "-c", default="未分类", help="分类标签")
@click.option("--type", "skill_type", default="scenario",
              type=click.Choice(["scenario", "dimension"]),
              help="skill 类型 (默认 scenario)")
@click.option("--keyword", "-k", default="", help="搜索关键词模板 (支持 {param})")
def create(name, description, skill_type, category, keyword):
    """创建新 skill MD 文件 (脚手架).

    NAME: skill 名称 (用作文件名和标识)

    \b
    示例:
      emoo skill create store-revenue -c "门店营收" --keyword "{store} {month}"
      emoo skill create app-filter --type dimension -c "搜索维度"
    """
    skills_dir = ensure_skills_dir()
    filepath = os.path.join(skills_dir, f"{name}.md")

    if os.path.exists(filepath):
        raise click.BadParameter(f"skill 文件已存在: {filepath}")

    desc = description or name
    kw = keyword or f"{name} 搜索"
    content = SKILL_TEMPLATE.format(
        name=name, description=desc,
        skill_type=skill_type, category=category,
        keyword=kw,
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    click.echo(f"Skill 文件已创建: {filepath}")
    click.echo(f"  名称: {name}")
    click.echo(f"  分类: {category}")
    click.echo(f"  类型: {skill_type}")
    click.echo(f"\n编辑该文件以完善搜索参数和说明，然后使用:")
    click.echo(f"  emoo skill run {name}")


# ── pipeline sub-group ──────────────────────────────────────────────────────

@skill.group()
def pipeline():
    """自适应搜索流水线 (知识图谱 → 意图分析 → 方案执行).

    三段式智能搜索流水线，自动适配不同客户的数据环境。
    """


@pipeline.command()
@click.option("--max-sample-per-group", default=5, help="每个文档组采样标题数 (默认5)")
@click.option("--max-doc-groups", default=200, help="最大采样文档组数 (默认200)")
@click.option("-o", "--output-dir", default=None, help="输出目录 (默认 ~/.emoo/knowledge_map/)")
@click.option("--auto/--no-auto", "auto_mode", default=True, help="自动缓存模式: 24h内未过期则跳过生成 (默认开启)")
@click.option("--ttl", default="24h", help="缓存有效期 (格式: 24h/24h/30m, 默认 24h)")
@click.option("--refresh", "force_refresh", is_flag=True, default=False, help="强制重新生成，忽略缓存")
@click.pass_context
def knowledge_map(ctx, max_sample_per_group, max_doc_groups, output_dir, auto_mode, ttl, force_refresh):
    """生成增强知识图谱，包含 app 文档组详情、标题采样、Base 表嗅探.

    \b
    缓存策略:
      --auto (默认): 检查缓存，24h内有效则直接返回
      --refresh:     强制重新生成
      --ttl 6h:      自定义缓存有效期

    \b
    输出两个文件:
      emoo_knowledge_map.json  — 机器可读 (供 intent 使用)
      emoo_knowledge_map.md    — 人类可读摘要
    """
    # Parse TTL
    ttl_seconds = 86400  # default 24h
    if ttl.endswith("d"):
        ttl_seconds = int(ttl[:-1]) * 86400
    elif ttl.endswith("h"):
        ttl_seconds = int(ttl[:-1]) * 3600
    elif ttl.endswith("m"):
        ttl_seconds = int(ttl[:-1]) * 60

    # Default output dir — namespaced by API key to isolate workspaces
    if output_dir is None:
        cfg = {}
        try:
            with open(os.path.expanduser("~/.emoo/config.json")) as f:
                cfg = json.load(f)
        except Exception:
            pass
        api_prefix = (cfg.get("api_key", "") or cfg.get("client_id", "default"))[:12]
        output_dir = os.path.expanduser(f"~/.emoo/knowledge_map/{api_prefix}")
    os.makedirs(output_dir, exist_ok=True)

    cached_json = os.path.join(output_dir, "emoo_knowledge_map.json")
    cache_age = 0
    if os.path.exists(cached_json):
        cache_age = time.time() - os.path.getmtime(cached_json)

    # Auto mode: skip if cache is fresh
    if auto_mode and not force_refresh and cache_age > 0 and cache_age < ttl_seconds:
        _progress(f"📦 使用缓存知识图谱 (生成于 {cache_age/3600:.1f} 小时前, TTL={ttl})")
        with open(cached_json, encoding="utf-8") as f:
            km = json.load(f)
    else:
        if force_refresh and cache_age > 0:
            _progress(f"🔄 强制刷新 (缓存已存在 {cache_age/3600:.1f} 小时)")
        elif cache_age >= ttl_seconds and cache_age > 0:
            _progress(f"⏰ 缓存已过期 ({cache_age/3600:.1f} 小时前, TTL={ttl}), 重新生成...")
        else:
            _progress("正在扫描工作区应用...")

        client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
        generate_knowledge_map(
            client,
            max_sample_per_group=max_sample_per_group,
            max_doc_groups=max_doc_groups,
            output_dir=output_dir,
        )
        with open(cached_json, encoding="utf-8") as f:
            km = json.load(f)

    apps = km.get("apps", [])
    total_docs = sum(a.get("doc_count", 0) for a in apps)
    total_groups = sum(len(a.get("doc_groups", [])) for a in apps)
    base_tables = km.get("base_tables", [])
    base_records = sum(t.get("record_count", 0) for t in base_tables)

    _progress(f"\n知识图谱{' (缓存)' if auto_mode and not force_refresh and cache_age > 0 and cache_age < ttl_seconds else ''}:")
    _progress(f"  路径: {os.path.abspath(output_dir)}")
    _progress(f"  应用: {len(apps)} 个, 文档组: {total_groups} 个, 文档: {total_docs} 篇")
    if base_tables:
        _progress(f"  Base 表: {len(base_tables)} 个, 记录: {base_records} 条")

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


@pipeline.command()
@click.argument("query")
@click.option("-k", "--knowledge-map", "km_path", default=None,
              help="知识图谱 JSON 路径 (默认 ~/.emoo/knowledge_map/emoo_knowledge_map.json)")
@click.option("--top", default=5, help="最多输出几个搜索步骤 (默认5)")
@click.option("-o", "--output", "output_file", default=None, help="保存搜索方案到文件")
@click.pass_context
def intent(ctx, query, km_path, top, output_file):
    """分析搜索意图，输出结构化搜索方案.

    QUERY: 自然语言查询，如 "查示例门店店3月营收"

    \b
    示例:
      emoo skill pipeline intent "查示例门店店2026年3月营收"
      emoo skill pipeline intent "上周品项销售情况" --top 3
      emoo skill pipeline intent "最近7天员工考勤" -o plan.json
    """
    if km_path is None:
        default_km = _default_km_path()
        if os.path.exists(default_km):
            km_path = default_km

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
        _progress(f"\n搜索方案已保存: {output_file}")


@pipeline.command()
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
      emoo skill pipeline search -p plan.json
      emoo skill pipeline search -p plan.json --csv output.csv
      emoo skill pipeline search -p plan.json --step 1
      emoo skill pipeline intent "营收" | emoo skill pipeline search -p -
    """
    if plan_file == "-":
        plan = json.load(sys.stdin)
    elif os.path.exists(plan_file):
        with open(plan_file, encoding="utf-8") as f:
            plan = json.load(f)
    else:
        raise click.BadParameter(f"搜索方案文件不存在: {plan_file}")

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))

    _progress(f"意图: {plan.get('intent', 'N/A')}")
    steps = plan.get("plan", [])
    if step is not None:
        steps = [s for s in steps if s.get("step") == step]
    _progress(f"执行 {len(steps)} 个搜索步骤...")

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
        _progress(f"CSV 已导出: {path}")


@pipeline.command()
@click.argument("query")
@click.option("-k", "--knowledge-map", "km_path", default=None,
              help="知识图谱路径 (默认自动查找缓存)")
@click.option("--max-results", default=500, help="最多返回结果数 (默认500)")
@click.option("--compact", is_flag=True, default=False, help="精简输出 (仅保留 time/from/content/group)")
@click.option("--no-probe-filter", is_flag=True, default=False, help="不过滤探针数据")
@click.option("--summarize", is_flag=True, default=False, help="AI自动总结 (拉全量无关键词过滤, 送模型总结)")
@click.pass_context
def analyze(ctx, query, km_path, max_results, compact, no_probe_filter, summarize):
    """智能分析: KM匹配群 → 定向搜索 → 多群聚合.

    \b
    QUERY: 自然语言查询，如 "最近一周发货情况"
    自动: 解析时间 → 匹配聊天群 → 搜索 → 去重聚合

    \b
    示例:
      emoo skill pipeline analyze "最近一周发货情况"
      emoo skill pipeline analyze "今天裹包运输" --max-results 200
    """
    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    as_json = ctx.obj.get("as_json", False)

    if km_path is None:
        default_km = _default_km_path()
        if os.path.exists(default_km):
            km_path = default_km

    _progress(f"🧠 智能分析: {query}")

    result = run_analyze(client, query, km_path=km_path, compact=compact,
                         exclude_probe=not no_probe_filter, max_results=max_results,
                         summarize=summarize)

    if as_json:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        lines = []
        lines.append(f"\n{'='*60}")
        lines.append(f"📊 分析结果: {result.get('query', query)}")
        t0, t1 = result.get('time_range', ['?', '?'])
        lines.append(f"   时间: {t0} ~ {t1}")
        lines.append(f"   匹配群: {len(result.get('matched_rooms', []))} 个")
        for r in result.get('matched_rooms', []):
            gid = r.get('group_id', '?')
            reasons = r.get('reasons', r.get('matched_keywords', []))
            lines.append(f"   ✅ {gid[:24]}... ({'; '.join(reasons[:2]) if reasons else ''})")
        sampling = result.get('sampling', 'full')
        sampling_note = f" ({sampling})" if sampling != 'full' else ''
        lines.append(f"   结果: {result.get('total', 0)} 条{sampling_note}")

        if result.get('daily_summary'):
            lines.append(f"\n   每日消息量 (原始):")
            for d, c in sorted(result['daily_summary'].items())[:10]:
                bar = '█' * min(c, 30)
                lines.append(f"     {d}: {bar} {c}")

        if result.get('by_date'):
            lines.append(f"\n   样本分布:")
            for d, c in result.get('by_date', {}).items():
                bar = '█' * min(c, 30)
                lines.append(f"     {d}: {bar} {c}")

        if result.get('top_people'):
            lines.append(f"\n   关键人物:")
            for p in result.get('top_people', [])[:5]:
                lines.append(f"     {p['user']}: {p['count']}条")

        if result.get('ai_summary'):
            lines.append(f"\n   🤖 AI总结:")
            for line in result['ai_summary'].split('\n'):
                lines.append(f"     {line}")

        if result.get('samples'):
            lines.append(f"\n   样本消息:")
            for s in result.get('samples', [])[:5]:
                lines.append(f"     [{s['time']}] {s['user']}: {s['content'][:120]}")

        click.echo('\n'.join(lines))

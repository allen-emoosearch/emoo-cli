#!/usr/bin/env python3
"""Fast unit checks for the KM v2 / aggregate intent pipeline (no network)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.skills.intent import (  # noqa: E402
    _build_aggregate_plan,
    _build_aggregate_step,
    _detect_metric_intent,
    _parse_time,
    _pick_group_field,
    _pick_numeric_field,
)
from src.skills.knowledge_map import _extract_fields  # noqa: E402
from src.skills.search import execute_search_plan  # noqa: E402


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    print(f"✅ {name}")


def test_time_parsing():
    week = _parse_time("近一周")
    check("近一周 parsed", week and week["from"] < week["to"])
    month = _parse_time("近一个月")
    check("近一个月 parsed", month and month["from"] < month["to"])
    quarter = _parse_time("上个季度")
    check("上个季度 parsed", quarter and quarter["from"].endswith("-01"))


def test_metric_detection():
    m = _detect_metric_intent("各门店采购金额合计")
    check("sum + 门店", m and m["metric_type"] == "sum" and m["group_hint"] == "门店")

    m = _detect_metric_intent("近一周各门店单量")
    check("count + 门店", m and m["metric_type"] == "count" and m["group_hint"] == "门店")

    m = _detect_metric_intent("按月统计各门店消费总额")
    check("trend/month", m and m["trend"] and m["interval"] == "month")

    check("plain query is not aggregate", _detect_metric_intent("近一周发货") is None)

    m = _detect_metric_intent("平均客单价")
    check("avg + 客单价 synonyms", m and m["metric_type"] == "avg"
          and "客单价" in m["field_hints"])


def test_field_picking():
    fields = [
        {"path": "优惠金额", "name": "优惠金额", "type": "number", "distinct_count": 10},
        {"path": "实收金额", "name": "实收金额", "type": "number", "distinct_count": 10},
        {"path": "菜品明细.*.金额", "name": "金额", "type": "number", "distinct_count": 10},
        {"path": "门店ID", "name": "门店ID", "type": "string", "distinct_count": 5},
        {"path": "门店名称", "name": "门店名称", "type": "string", "distinct_count": 5},
    ]
    metric = _pick_numeric_field(fields, ["金额", "总额"])
    check("prefer primary amount", metric and metric["path"] == "实收金额")

    group = _pick_group_field(fields, ["门店"])
    check("prefer readable group over ID", group and group["path"] == "门店名称")


def test_field_extraction():
    docs = [{
        "title": "PO-1",
        "content": {
            "金额": 100.5,
            "门店": "A店",
            "明细": [{"物料": "foo", "金额": 10.5}],
        },
    }]
    fields = {f["path"]: f for f in _extract_fields(docs)}
    check("top-level number", fields["金额"]["type"] == "number")
    check("nested list path", fields["明细.*.金额"]["type"] == "number")
    check("string group values", fields["门店"]["values"] == ["A店"])


def test_aggregate_plan():
    app = {
        "ws_app_key": "app1",
        "title": "金石-订单",
        "fields": [
            {"path": "实收金额", "name": "实收金额", "type": "number", "distinct_count": 10},
            {"path": "门店名称", "name": "门店名称", "type": "string", "distinct_count": 5},
        ],
        "doc_groups": [{
            "app_group_id": "order",
            "app_group_name": "订单",
            "doc_count": 100,
            "fields": [
                {"path": "实收金额", "name": "实收金额", "type": "number", "distinct_count": 10},
                {"path": "门店名称", "name": "门店名称", "type": "string", "distinct_count": 5},
            ],
        }],
    }
    metric = _detect_metric_intent("各门店金额合计")
    step = _build_aggregate_step(metric, app, app["doc_groups"][0],
                                 [[{"field": "ws_app.ws_app_key", "operator": "eq", "value": "app1"}]],
                                 ["门店"], 0.5)
    check("aggregate step built", step and step["metric_field"] == "实收金额"
          and step["group_by_field"] == "门店名称")

    plan = _build_aggregate_plan(metric, [app], [], None, ["门店"])
    check("aggregate plan built", len(plan) == 1 and plan[0]["type"] == "aggregate")


class FakeClient:
    def __init__(self, aggregate_note=None):
        self.aggregate_note = aggregate_note

    def post(self, path, body=None):
        if path == "/search/aggregate":
            return {"data": {
                "total_docs": 10,
                "buckets": [{"key": "A店", "doc_count": 10, "metric_value": 100.0}],
                "note": self.aggregate_note,
            }}
        if path == "/search":
            return {"data": {
                "total": 1,
                "results": [{"title": "fallback doc"}],
                "total_pages": 1,
            }}
        raise AssertionError(f"unexpected path {path}")


def test_execution():
    plan = {"intent": "test", "plan": [{
        "step": 1, "type": "aggregate", "metric_type": "sum",
        "metric_field": "金额", "group_by_field": "门店名称",
        "filters": [[{"field": "ws_app.ws_app_key", "operator": "eq", "value": "app1"}]],
    }]}
    outcome = execute_search_plan(FakeClient(), plan)
    check("aggregate executed", outcome["aggregates"][0]["buckets"][0]["key"] == "A店")

    bad_plan = {
        "intent": "test",
        "plan": plan["plan"],
        "fallback_plan": [{"step": 1, "keyword": "test", "filters": []}],
    }
    outcome = execute_search_plan(FakeClient(aggregate_note="数值列无匹配值"),
                                  bad_plan, fallback=True)
    check("fallback on aggregate note", outcome.get("_fallback_used")
          and outcome["results"][0]["title"] == "fallback doc")


if __name__ == "__main__":
    test_time_parsing()
    test_metric_detection()
    test_field_picking()
    test_field_extraction()
    test_aggregate_plan()
    test_execution()
    print("\n全部测试通过")

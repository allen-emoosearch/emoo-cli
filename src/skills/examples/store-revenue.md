---
name: store-revenue
description: 查询指定门店的营业数据，支持时间范围过滤
type: scenario
category: 门店营收
tags: [营收, POS, 门店]
emoo:
  search:
    keyword: "{store} {month} 营业情况"
    app: 天财·POS系统
    doc_group: 营业情况汇总
    page_size: 200
  params:
    store:
      description: 门店名称（如 美罗城）
      required: true
      example: 美罗城
    month:
      description: 月份（如 2026-03）
      required: false
      default: "2026-03"
      map_to: time_range
  csv_export: true
---

# 门店营收查询

## 使用方式

```bash
emoo skill run store-revenue --store "美罗城" --month "2026-03"
```

## 说明

查询天财POS系统中指定门店的每日营收明细。
返回：实收合计、应收合计、市别分布（早/午/晚市）、品类销售明细。

## 典型场景

- 单店月度营收趋势分析
- 多店营收对比
- 周末vs工作日营收差异

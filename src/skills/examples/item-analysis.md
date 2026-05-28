---
name: item-analysis
description: 品项销售数据分析，按品项名称搜索销售记录
type: scenario
category: 品项分析
tags: [品项, 销售, POS]
emoo:
  search:
    keyword: "{item} {month} 销售"
    app: 天财·POS系统
    doc_group: 品项销售明细
    page_size: 200
  params:
    item:
      description: 品项名称（如 红烧肉）
      required: true
      example: 红烧肉
    month:
      description: 月份（如 2026-03）
      required: false
      default: "2026-03"
      map_to: time_range
  csv_export: true
---

# 品项销售分析

## 使用方式

```bash
emoo skill run item-analysis --item "红烧肉" --month "2026-03"
```

## 说明

查询指定品项在各门店的销售数据。
返回：品项名称、销售数量、销售金额、所属门店、日期。

## 典型场景

- 单品销售趋势分析
- 畅销/滞销品项识别
- 品项销售额排行

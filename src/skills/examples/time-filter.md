---
name: time-filter
description: 按时间范围过滤搜索结果，支持月份、日期、相对时间
type: dimension
category: 搜索维度
tags: [维度, 时间, 过滤]
emoo:
  search:
    keyword: "{keyword}"
    page_size: 200
  params:
    keyword:
      description: 搜索关键词
      required: true
      example: 营业数据
    time_range:
      description: 时间范围（YYYY-MM / YYYY-MM-DD / 最近N天）
      required: false
      default: "2026-03"
      map_to: time_range
      example: "2026-03"
---

# 按时间筛选

## 使用方式

```bash
emoo skill run time-filter --keyword "营业数据" --time_range "2026-03"
emoo skill run time-filter --keyword "周报" --time_range "最近7天"
emoo skill run time-filter --keyword "日报" --time_range "2026-03-15"
```

## 说明

维度类 skill，为搜索添加时间范围过滤。
支持三种时间格式：月份、具体日期、相对天数。

## 时间格式

| 格式 | 示例 | 含义 |
|------|------|------|
| YYYY-MM | `2026-03` | 整个月 |
| YYYY-MM-DD | `2026-03-15` | 精确到天 |
| 最近Nd天 | `最近7天` | 相对当前日期往前 N 天 |

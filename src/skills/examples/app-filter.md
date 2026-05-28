---
name: app-filter
description: 限定在指定应用内搜索，可与其他 skill 组合使用
type: dimension
category: 搜索维度
tags: [维度, 过滤, app]
emoo:
  search:
    keyword: "{keyword}"
    app: "{app_name}"
    page_size: 200
  params:
    keyword:
      description: 搜索关键词
      required: true
      example: 报表
    app_name:
      description: 目标应用名称（知识图谱中匹配）
      required: true
      example: 天财·POS系统
---

# 按应用筛选

## 使用方式

```bash
emoo skill run app-filter --app_name "天财·POS系统" --keyword "月度汇总"
```

## 说明

维度类 skill，限定搜索范围在指定应用内。
可与其他搜索条件组合，精确命中目标数据源。

## 典型场景

- 只查 POS 系统的数据
- 只查 OA 系统的数据
- 只查某个业务系统的数据

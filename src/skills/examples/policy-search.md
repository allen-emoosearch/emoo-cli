---
name: policy-search
description: 搜索公司制度、政策、规范文件
type: scenario
category: 制度政策
tags: [制度, 政策, 规范, 合规]
emoo:
  search:
    keyword: "{keyword}"
    page_size: 200
  params:
    keyword:
      description: 搜索关键词（如 年假/报销/加班）
      required: true
      example: 年假
  csv_export: false
---

# 制度政策搜索

## 使用方式

```bash
emoo skill run policy-search --keyword "年假"
emoo skill run policy-search --keyword "报销"
emoo skill run policy-search --keyword "加班"
```

## 说明

搜索公司内部的制度、政策、规范文件，不限定特定应用。
覆盖全企业所有数据源的制度类文档。

## 典型场景

- 查询年假/病假政策
- 查询报销标准和流程
- 查询加班规定
- 查询社保公积金政策

---
name: employee-search
description: 搜索员工考勤、排班、绩效相关信息
type: scenario
category: 人力资源
tags: [员工, 考勤, 排班, HR]
emoo:
  search:
    keyword: "{employee} {month} {topic}"
    app: 人力资源管理
    page_size: 200
  params:
    employee:
      description: 员工姓名
      required: false
      example: 张三
    month:
      description: 月份（如 2026-03）
      required: false
      default: "2026-03"
      map_to: time_range
    topic:
      description: 搜索主题（考勤/排班/绩效/工资）
      required: false
      default: 考勤
      choices: [考勤, 排班, 绩效, 工资, 请假]
  csv_export: false
---

# 员工信息查询

## 使用方式

```bash
emoo skill run employee-search --employee "张三" --month "2026-03" --topic "考勤"
emoo skill run employee-search --employee "李四" --topic "排班"
```

## 说明

搜索员工考勤记录、排班表、绩效考核等信息。
返回：员工姓名、日期、考勤状态、排班时间等。

## 典型场景

- 员工月考勤汇总
- 排班表查询
- 绩效数据检索

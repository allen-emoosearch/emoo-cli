# 文件管理流程说明

emoo 文件采用**客户端直传对象存储**模式，避免大文件占用后端带宽。本文件只描述跨接口的**流程**与**调用方实现**；各接口（upload-credentials / confirm / download-url）的字段定义与错误码见 [openapi_kb_file.swagger.json](openapi_kb_file.swagger.json)。

## 上传流程（5 步）

```
1. 客户端 → POST /data/files/upload-credentials   拿到 file_key + 统一 upload 指令
2. 客户端 → 按 upload.method 直传文件到对象存储（不经过 emoo 后端）
3. 客户端 → POST /data/files/confirm              通知 emoo 上传完成，创建文件元数据
4. 客户端 → 把 file_key 写入 record 的 FILE 类型字段（走 [数据操作](openapi_kb_table_record.swagger.json)）
5. 后续展示 / 下载：GET /data/files/download-url  拿 24h 有效下载链接
```

**约束**：
- 单文件最大 100 MB
- 单次批量上传凭证/确认最多 20 个文件
- 上传凭证 1h 过期，下载链接 24h 过期

---

## 调用方最简实现（强烈推荐）

`upload-credentials` 返回的 `upload` 字段是**统一指令**，调用方**无需关心底层是 MinIO / OSS / S3 / 其他**，按下面这段代码无脑处理即可：

```javascript
async function uploadToStorage(file, upload) {
  if (upload.method === 'PUT') {
    // 直接 PUT 文件二进制
    const resp = await fetch(upload.url, {
      method: 'PUT',
      body: file,
      headers: upload.headers || {},
    });
    if (!resp.ok) throw new Error(`upload failed: ${resp.status}`);
  } else if (upload.method === 'POST') {
    // multipart 表单：先加 form_fields，最后追加文件
    const fd = new FormData();
    Object.entries(upload.form_fields || {}).forEach(([k, v]) => fd.append(k, v));
    fd.append(upload.file_field || 'file', file);
    const resp = await fetch(upload.url, { method: 'POST', body: fd });
    if (!resp.ok) throw new Error(`upload failed: ${resp.status}`);
  } else {
    throw new Error(`unsupported method: ${upload.method}`);
  }
}
```

### upload 字段统一结构

| 字段 | 类型 | 说明 |
|---|---|---|
| method | string | `PUT` 或 `POST` |
| url | string | 直传目标 URL |
| headers | object | 调用方需附加的 HTTP headers（一般为空） |
| form_fields | object | POST 时的附加 multipart 字段（不含文件本身），PUT 时为 `{}` |
| file_field | string \| null | POST 时文件在 form 里的字段名（默认 `file`）；PUT 时为 `null` |

> 未来 emoo 切换或新增 storage provider（S3、COS 等）只会在后端翻译层加分支，调用方零改动。

---

## FILE 类型字段写入示例（配合数据操作接口）

confirm 拿到 `file_key` 后，可写入记录的 FILE 类型字段（走 [数据操作](openapi_kb_table_record.swagger.json) 的 insert / update 接口）：

**单值 FILE 字段**

```json
{
  "table_key": "tbl_xxx",
  "records": [
    {"attachment": "fk_xxx1"}
  ]
}
```

**多值 FILE 字段**

```json
{
  "table_key": "tbl_xxx",
  "records": [
    {"attachments": ["fk_xxx1", "fk_xxx2"]}
  ]
}
```

**list / get record 的返回**

FILE 类型字段会被展开为对象（多值字段返回对象数组），不是裸 file_key：

```json
{
  "attachments": [
    {"file_key": "fk_xxx1", "name": "report.pdf", "size": 102400, "url": "https://minio.example.com/dl/fk_xxx1?signature=..."}
  ]
}
```

`url` 是 24h 签名下载链接，可直接用于展示/预览。需要刷新时再走 `GET /data/files/download-url`。

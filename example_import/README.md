# 题目批量导入示例

本文件夹包含三种格式的题目导入示例，附带占位图片。

## 支持的文件格式

| 格式 | 文件 | 说明 |
|------|------|------|
| YAML | `examples.yaml` | 适合人工编辑，结构清晰 |
| JSON | `examples.json` | 适合程序生成，API 对接 |
| Markdown | `examples.md` | 适合混合文档，题干用 Markdown 书写 |

## 题目字段一览

| 字段 | 必填 | 说明 |
|------|------|------|
| `type` | ✅ | `single`（单选题）、`multiple`（多选题）、`true_false`（判断题）、`subjective`（主观题） |
| `content` | ✅ | 题干，支持 **Markdown** 和 LaTeX（`$...$` 行内 / `$$...$$` 块级） |
| `options` | 选择/判断 | 选项列表，如 `["A", "B", "C", "D"]` |
| `answer` | ✅ | 单选用索引 `"0"`；多选用 `"0,1"`；判断用 `"true"`/`"false"`；主观题写参考答案 |
| `explanation` | 否 | 答案解析 |
| `difficulty` | 否 | `easy` / `medium` / `hard`，默认 `medium` |
| `source` | 否 | 来源/书籍名称 |
| `chapter` | 否 | 所属章节 |
| `tags` | 否 | 标签列表，如 `["python", "基础"]` |
| `image` | 否 | 图片文件名（需上传至 `static/uploads/`） |

## 使用方式

### 1. 通过 Web 界面导入

1. 启动应用：`python app.py`
2. 登录后进入「题目管理」→「导入题目」
3. 选择 `.yaml`、`.json` 或 `.md` 文件上传

### 2. 图片处理

导入文件中的 `image` 字段引用图片文件名，图片需额外上传：

- **Web 界面**：在创建/编辑题目时，通过表单上传图片到 `static/uploads/`
- **手动方式**：将图片文件放入 `static/uploads/` 目录，然后在导入文件中用 `image` 字段引用文件名

支持格式：`png`、`jpg`、`jpeg`、`gif`、`webp`

### 3. 在题干中引用图片

题干（`content`）支持 Markdown 语法，可以直接嵌入图片：

```markdown
![描述](image_filename.png)
```

> **注意**：导入时 `image` 字段目前仅作为元数据保存，不会自动关联到题干的图片引用。
> 如需在题干中显示图片，请同时使用 Markdown 图片语法引用已上传的图片。

## 生成占位图片

运行以下脚本生成示例占位图（纯 Python 标准库，无需额外依赖）：

```bash
python example_import/generate_images.py
```

生成的图片可直接用于测试导入功能。

## 示例内容概览

三个示例文件包含相同的 6 道不同类型题目：

1. **单选题** — 计算机基础（附带图片）
2. **多选题** — CSS 布局（无图）
3. **判断题** — 二分查找复杂度
4. **主观题** — 动态规划（含 LaTeX）
5. **单选题** — 网络安全/HTTPS（附带图片）
6. **多选题** — Docker 容器（无图）

覆盖了全部 4 种题型（single / multiple / true_false / subjective）和 3 个难度级别（easy / medium / hard）。

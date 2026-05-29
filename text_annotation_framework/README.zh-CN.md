# Text Annotation Framework 中文说明

这是一个从旧版英文阅读助手中抽象出来的“通用文本标注框架”示例项目。它的目标不是只做生词翻译，而是提供一套可复用的能力：

```text
输入任意文本
  ↓
根据 profile 选择提取策略
  ↓
调用 LLM 或 mock annotator 生成结构化 annotations
  ↓
流式返回进度和结果
  ↓
前端把原文 + annotations 渲染成可点击的阅读层
```

当前项目是一个独立新项目，不修改旧项目代码。

## 核心定位

框架核心关注“文本增强”能力：

- 关键词提取
- 术语解释
- 短语标注
- 实体识别
- 概念提示
- 可点击文本渲染

第一版提供一个英文阅读参考应用，用来验证框架是否能端到端跑通。旧项目里的生词本、历史记录、已掌握词过滤等能力暂时不进入框架核心，可以后续作为应用层插件继续扩展。

## 项目结构

```text
text_annotation_framework/
├── backend/
│   ├── pyproject.toml
│   ├── src/text_annotation_framework/
│   │   ├── models.py       # Document、TextChunk、Annotation、AnnotationResult、AnnotationEvent
│   │   ├── profiles.py     # profile 定义和 registry
│   │   ├── prompts.py      # 通用 system prompt 和 user prompt 构造
│   │   ├── llm.py          # mock client 和 OpenAI 兼容 client
│   │   ├── engine.py       # 标注引擎：调用 LLM、解析 JSON、归一化结果
│   │   ├── chunking.py     # 长文本切分
│   │   ├── streaming.py    # 并发处理和流式事件
│   │   └── api.py          # FastAPI 接口
│   └── tests/
│
└── frontend/
    ├── package.json
    ├── src/
    │   ├── App.vue         # 英文阅读 reference app
    │   ├── api.js          # POST SSE 客户端
    │   ├── renderer.js     # 通用 annotated text renderer
    │   └── styles.css
    └── src/renderer.test.js
```

## 快速开始

### 1. 启动后端

```bash
cd text_annotation_framework/backend
uv sync
uv run uvicorn text_annotation_framework.api:app --reload --port 8010
```

后端健康检查：

```text
http://127.0.0.1:8010/api/health
```

### 2. 启动前端

```bash
cd text_annotation_framework/frontend
npm install
npm run dev
```

打开：

```text
http://localhost:5174
```

默认情况下，即使没有 API Key，项目也会使用内置的 mock annotator，因此可以离线跑通 demo。

## 使用真实 LLM

如果希望调用真实模型，启动后端前配置环境变量：

```env
LLM_API_KEY=sk-your-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_ID=gpt-4.1-mini
LLM_TIMEOUT=60
```

只要服务兼容 OpenAI chat-completions 格式，就可以通过 `LLM_BASE_URL` 接入。

## 核心数据结构

`Annotation` 是框架最重要的数据结构：

```json
{
  "surface": "resilient",
  "label": "有韧性的",
  "type": "keyword",
  "context": "The resilient framework can annotate...",
  "start_index": 4,
  "end_index": 13,
  "metadata": {}
}
```

字段含义：

| 字段 | 说明 |
| ---- | ---- |
| `surface` | 原文中被标注的文本片段 |
| `label` | 简短解释、标签或翻译 |
| `type` | 标注类型，如 `keyword`、`term`、`phrase`、`entity`、`concept` |
| `context` | 原文上下文 |
| `start_index` / `end_index` | 标注片段在原文中的字符范围 |
| `metadata` | profile 或应用层自定义扩展 |

`AnnotationResult` 以结构化 annotations 为主，同时保留 `annotated_text` 作为兼容展示字段。

## 内置 Profiles

当前内置三个 profile：

| profile | 用途 |
| ------- | ---- |
| `english_reading` | 英文阅读标注，关注生词、短语、上下文含义和阅读障碍 |
| `technical_terms` | 技术文档标注，关注 API、配置、错误、架构和工程术语 |
| `general_keywords` | 通用关键词提取，关注摘要性关键词、实体和概念 |

后续扩展新场景时，优先在 `profiles.py` 中新增 profile，而不是修改 engine。

## API

### 获取 profile 列表

```http
GET /api/profiles
```

### 单次标注

```http
POST /api/annotate
Content-Type: application/json
```

```json
{
  "text": "The resilient framework recovered after a timeout.",
  "profile": "english_reading",
  "options": {}
}
```

### 流式标注

```http
POST /api/annotate-stream
Content-Type: application/json
```

返回 Server-Sent Events：

```text
data: {"type":"start","current":0,"total":1,...}

data: {"type":"chunk_completed","current":1,"total":1,...}

data: {"type":"progress","current":1,"total":1,...}

data: {"type":"completed","current":1,"total":1,...}
```

## 前端渲染器

`frontend/src/renderer.js` 提供一个通用渲染函数：

```js
renderAnnotatedText(text, annotations)
```

它只依赖原文和结构化 annotations，不关心业务是“生词”“技术术语”还是“实体”。这让渲染层可以复用于不同文本标注场景。

为了安全，renderer 会先进行 HTML 转义，再插入可点击标注按钮。

## 测试

后端：

```bash
cd text_annotation_framework/backend
uv run ruff check src tests
uv run pytest
```

前端：

```bash
cd text_annotation_framework/frontend
npm test
npm run build
```

当前覆盖：

- schema 默认值、序列化和 metadata
- profile registry
- mock LLM + engine
- chunking
- streaming events
- renderer HTML 转义、点击标记和重叠标注处理

## 后续演进建议

1. 增加更多 profile，例如法律文本、新闻事件、论文阅读、小说人物关系。
2. 支持 profile 外部配置文件，让应用层不必改源码即可扩展策略。
3. 增加 annotation 审核/编辑能力。
4. 支持 React renderer 或纯 Web Component renderer。
5. 把旧项目的生词本、历史记录、已掌握词过滤作为 reference app 的可选插件迁移进来。

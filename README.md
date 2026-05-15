# HP-Agent

哈利波特英文阅读助手 — 输入英文段落，LLM 自动标注生词并插入中文翻译，流式渲染到羊皮纸风格的阅读页面。

## 功能概述

- 输入英文文本 → LLM 自动识别生词/短语/魔法术语 → 插入中文翻译
- 前端羊皮纸主题渲染，生词暗金色高亮，中文翻译次视觉层级
- 流式 SSE 推送处理进度，chunk 并行加速
- 三级阅读水平（初级/中级/高级），控制标注密度
- 生词本：跨会话累积，搜索/标记已掌握/忽略，已掌握词按时间排序
- 翻译历史记录：自动保存，可回看可删除
- Bookerly 衬线字体，阅读体验贴近纸质书

## 技术栈

| 层 | 技术 |
|------|------|
| 后端框架 | Python FastAPI |
| AI Agent | hello_agents (SimpleAgent) |
| LLM | DeepSeek v4-pro (via OpenAI 兼容 API) |
| 前端框架 | Vue 3 + Vite |
| 字体 | Bookerly (Regular + Bold) |

## 项目结构

```
hp_agent/
├── backend/
│   ├── .env                    # API 密钥、模型配置
│   ├── pyproject.toml          # Python 依赖
│   └── src/hp_agent/
│       ├── main.py             # FastAPI 入口 + SSE 接口 + REST API
│       ├── agent1.py           # AnnotatorService + 系统提示词 + 分级规则
│       ├── sse_service.py      # DocumentProcessor：分块 + 并行 + 流式
│       ├── vocab_db.py         # SQLite 持久化：生词 + 历史记录
│       └── tobecontinued/      # 待开发模块
├── frontend/
│   ├── index.html
│   ├── vite.config.js          # Vite 配置 + API 代理
│   ├── public/fonts/           # Bookerly 字体文件
│   └── src/
│       ├── main.js             # Vue 入口
│       ├── App.vue             # 根组件（全局背景 + Tab 导航）
│       ├── router/
│       │   └── index.js        # 三路由：/ /vocabulary /history
│       ├── views/
│       │   ├── ReadingPage.vue # 阅读页面（含水平选择器）
│       │   ├── VocabularyPage.vue  # 生词本（生词/已掌握子 Tab）
│       │   └── HistoryPage.vue     # 历史记录（展开/删除）
│       ├── composables/
│       │   └── useReadingStream.js  # SSE 连接 + 状态管理
│       ├── utils/
│       │   └── formatText.js   # 标记解析 + 已掌握词过滤
│       └── api/
│           ├── reading.js      # POST 创建任务
│           ├── vocabulary.js   # 生词 CRUD
│           └── history.js      # 历史 CRUD
```

## 快速开始

**前置要求：** Python 3.10+, Node.js 18+

**后端：**

```bash
cd backend
cp .env.example .env    # 填写 LLM_API_KEY
uv sync
uvicorn hp_agent.main:app --reload
```

**前端：**

```bash
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173`，输入英文文本，按 Enter 开始处理。

## 数据流

```
用户输入文本 + 选择水平
  → POST /api/create-process-task (task_id + level)
  → EventSource /api/process-stream?task_id=...
  → 从 SQLite 查询 mastered_words → 传入 LLM prompt
  → DocumentProcessor 分段落 → 合并 chunk (max 300 词)
  → asyncio.Semaphore(3) 并行请求 LLM
  → AnnotatorService → 分级提示词 → DeepSeek API (thinking=disabled)
  → LLM 输出 [[word|翻译]] 标记的 annotated_text
  → SSE 流式推送 progress + completed 事件
  → _maybe_save_completed() 自动写入 SQLite（生词 upsert + 历史保存）
  → 前端 formatText.js 解析 [[...|...]] + masteredWords 过滤
  → ReadingPage.vue 渲染 (Bookerly 字体 + 暗金色高亮)
```

## 关键设计决策

| 决策 | 说明 |
|------|------|
| **标记格式 `[[word\|翻译]]`** | LLM 直接输出标记，前端不再用词表反向匹配，消除漏词问题 |
| **并行 chunk 处理** | `asyncio.Semaphore(3)` 替代顺序 for 循环，N chunk 从 N 轮降为 ceil(N/3) 轮 |
| **关闭 thinking mode** | `extra_body={"thinking": {"type": "disabled"}}`，翻译标注无需深度推理，单次调用从 ~40s 降至 ~10s |
| **Bookerly 字体** | Amazon 定制衬线体，Regular + Bold 双字重避免 faux bold |
| **SQLite 持久化** | 生词 upsert 去重累加，历史记录自动保存，零额外依赖 |
| **三级标注密度** | `beginner`/`intermediate`/`advanced` 三套英文规则，控制标注阈值，不影响翻译字数 |
| **已掌握渲染过滤** | `annotated_text` 原样存储，渲染时根据 `masteredWords` 集合决定是否显示标注，可逆 |
| **生词本 + 历史子页面** | vue-router 三路由，Tab 导航切换，生词本内分子 Tab（生词/已掌握） |

## 配置参考 (.env)

```
LLM_MODEL_ID=deepseek-v4-pro
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://api.deepseek.com
LLM_TIMEOUT=60
LLM_TEMPERATURE=0.2
HOST=127.0.0.1
PORT=8000
VOCAB_DB_PATH=./data/harry_potter_vocab.db
DATA_DIR=./data
MAX_MASTERED_WORDS_IN_PROMPT=300
```

`LLM_TEMPERATURE` 设 0.2 保证翻译输出稳定一致。`MAX_MASTERED_WORDS_IN_PROMPT` 限制传入 LLM 的已掌握词数量上限，防止 prompt 过长。

## 更新日志

- 2026-05-10: 羊皮纸背景 + Bookerly 字体 + 生词暗金色高亮样式
- 2026-05-10: 标记化生词标注（`[[word|中文]]` 替代括号格式），解决前端正则匹配漏词
- 2026-05-10: chunk 并行处理 (`asyncio.Semaphore`) + 增大 chunk 上限 (180→300 词)
- 2026-05-10: 关闭 DeepSeek v4-pro 思考模式 (`extra_body`)
- 2026-05-10: SQLite 持久化（vocab_db.py）+ 5 个 REST API 端点
- 2026-05-10: 前端三页面导航（vue-router）+ Tab 栏
- 2026-05-11: 生词本：搜索/标记已掌握/忽略，已掌握词按时间排序
- 2026-05-11: 已掌握词汇渲染过滤（存储不变，渲染时按集合过滤，可逆）
- 2026-05-14: 翻译历史记录自动保存 + 列表/详情/删除
- 2026-05-14: 三级阅读水平（初级/中级/高级）控制标注密度

## 待开发

- 生词本侧边栏（vocabulary 已通过 SSE `completed` 事件下发，前端暂未展示）
- 已掌握词汇记忆与过滤（`mastered_words` 接口已就绪）
- `tobecontinued/` 目录下的 agent2、dictionary_service、config、utils 模块

"""
HP-Agent FastAPI 后端入口。

提供 7 个 REST API 端点 + 1 个 SSE 流式接口：
- POST   /api/create-process-task      创建标注任务
- GET    /api/process-stream           SSE 流式返回处理结果
- GET    /api/vocabulary                生词列表
- POST   /api/vocabulary                添加生词
- PATCH  /api/vocabulary/{id}/master    标记已掌握/取消
- DELETE /api/vocabulary/{id}           删除生词
- POST   /api/word-lookup              点击查词
- POST   /api/vocabulary/mark-by-word  按单词标记已掌握
- GET    /api/history                   历史记录列表
- GET    /api/history/{task_id}        历史记录详情
- DELETE /api/history/{task_id}        删除历史记录
"""

import asyncio
import json
import logging
import os
import threading
import uuid
from datetime import datetime, timedelta

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from hello_agents import HelloAgentsLLM
from pydantic import BaseModel, Field

from hp_agent.agent1 import AnnotatorService
from hp_agent.agent2 import WordLookupService
from hp_agent.prompt_profiles import PROFILE_PATTERN
from hp_agent.settings_store import SettingsStore
from hp_agent.sse_service import DocumentProcessor
from hp_agent.utils import sse_event
from hp_agent.vocab_db import VocabDB

# ==============================
# 基础配置
# ==============================
load_dotenv()

# 后端运行日志，不需要用 print() 打印调试信息
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hp-agent-backend")


app = FastAPI(title="HP-Agent Backend")


# ==============================
# CORS 配置
# ==============================
# 允许 Vue3 前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================
# 初始化服务
# ==============================
data_dir = os.getenv("DATA_DIR", "./data")
settings_store = SettingsStore(data_dir)
vocab_db = VocabDB(os.getenv("VOCAB_DB_PATH", "./data/harry_potter_vocab.db"))

service_lock = threading.RLock()
llm: HelloAgentsLLM | None = None
annotator_svc: AnnotatorService | None = None
lookup_svc: WordLookupService | None = None
doc_processor: DocumentProcessor | None = None


def rebuild_llm_services():
    global llm, annotator_svc, lookup_svc, doc_processor

    settings = settings_store.get_effective_llm_settings()
    if not settings.get("api_key"):
        raise HTTPException(status_code=400, detail="请先在设置页配置 DeepSeek API Key")

    with service_lock:
        llm = HelloAgentsLLM(
            model=settings["model_id"],
            api_key=settings["api_key"],
            base_url=settings["base_url"],
            provider="deepseek",
            temperature=settings["temperature"],
            timeout=settings["timeout"],
        )
        annotator_svc = AnnotatorService(llm)
        lookup_svc = WordLookupService(llm)
        doc_processor = DocumentProcessor(annotator_svc)


def ensure_llm_services():
    if doc_processor and lookup_svc:
        return
    rebuild_llm_services()


@app.on_event("startup")
async def startup():
    if settings_store.get_public_status()["configured"]:
        try:
            rebuild_llm_services()
        except Exception:
            logger.exception("初始化 LLM 服务失败，请检查 API Key 配置")

    async def periodic_cleanup():
        while True:
            await asyncio.sleep(300)
            cleanup_expired_tasks()
    asyncio.create_task(periodic_cleanup())


@app.on_event("shutdown")
async def shutdown():
    vocab_db._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    vocab_db.close()


# ==============================
# 请求模型
# ==============================
class CreateProcessTaskRequest(BaseModel):
    text: str = Field(..., max_length=500000, description="需要处理的长文本（上限约 50000 词）")
    level: str = Field(default="intermediate", pattern="^(beginner|intermediate|advanced)$", description="读者水平")
    profile: str = Field(default="general", pattern=PROFILE_PATTERN, description="阅读场景预设")


class SetMasteredRequest(BaseModel):
    mastered: bool = Field(..., description="是否已掌握")


class WordLookupRequest(BaseModel):
    word: str = Field(..., description="要查询的单词")
    sentence: str = Field(..., description="单词所在的句子上下文")


class AddVocabRequest(BaseModel):
    word: str = Field(..., description="生词")
    translation: str = Field(..., description="中文翻译")
    context: str = Field(default="", description="上下文句子")


class SaveSettingsRequest(BaseModel):
    api_key: str = Field(..., min_length=1, description="DeepSeek API Key")
    base_url: str = Field(default="https://api.deepseek.com", description="OpenAI 兼容接口地址")
    timeout: int = Field(default=60, ge=5, le=300, description="请求超时时间")
    temperature: float = Field(default=0.2, ge=0, le=2, description="输出随机性")


# ==============================
# 简单任务缓存
# 开发阶段可以先用内存字典
# 生产环境建议换成 Redis / 数据库
# ==============================
process_tasks: dict[str, dict] = {}
TASK_EXPIRE_MINUTES = 30

def _maybe_save_completed(event: str, task_id: str, original_text: str):
    """
    检测 SSE completed 事件并自动保存到 SQLite。

    仅在事件类型为 completed 时才执行：
    1. 遍历 total_vocab，逐词 upsert 到生词表
    2. 将 annotated_text 写入历史记录
    异常静默捕获，避免阻塞 SSE 流。
    """
    if not event.startswith("data: "):
        return
    try:
        data = json.loads(event[6:].strip())
    except json.JSONDecodeError:
        return

    if data.get("type") != "completed":
        return

    total_vocab = data.get("total_vocab", [])
    annotated_text = data.get("annotated_text", "")
    try:
        for v in total_vocab:
            vocab_db.upsert_vocabulary(
                v.get("word", ""), v.get("translation", ""), v.get("context", "")
            )
        vocab_db.save_history(task_id, original_text, annotated_text)
        logger.info(f"已保存历史记录: task_id={task_id}, vocab_count={len(total_vocab)}")
    except Exception:
        logger.exception(f"保存翻译结果失败: task_id={task_id}")


def cleanup_expired_tasks():
    """
    清理长时间没有被消费的任务，避免内存堆积。
    """
    now = datetime.now()
    expired_task_ids = []

    for task_id, task in process_tasks.items():
        created_at = task.get("created_at")

        if created_at and now - created_at > timedelta(minutes=TASK_EXPIRE_MINUTES):
            expired_task_ids.append(task_id)

    for task_id in expired_task_ids:
        process_tasks.pop(task_id, None)

    if expired_task_ids:
        logger.info(f"已清理过期任务数量: {len(expired_task_ids)}")

@app.get("/")
async def root():
    """
    后端启动测试接口。
    """
    return {
        "message": "HP-Agent Backend is running"
    }


@app.get("/api/health")
async def health_check():
    """
    健康检查接口。
    """
    return {
        "status": "ok"
    }


@app.get("/api/settings")
async def get_settings():
    return settings_store.get_public_status()


@app.post("/api/settings")
async def save_settings(request: SaveSettingsRequest):
    settings_store.save_llm_settings(
        api_key=request.api_key,
        base_url=request.base_url,
        timeout=request.timeout,
        temperature=request.temperature,
    )
    rebuild_llm_services()
    return {"ok": True, **settings_store.get_public_status()}


@app.post("/api/create-process-task")
async def create_process_task(request: CreateProcessTaskRequest):
    """
    第一步：
    前端通过 fetch POST 提交原始文本。
    后端创建一个任务，并返回 task_id。
    """
    cleanup_expired_tasks()
    text = request.text.strip()

    if not text:
        raise HTTPException(status_code=400, detail="文本内容不能为空")

    ensure_llm_services()

    
    task_id = str(uuid.uuid4())

    process_tasks[task_id] = {
        "text": text,
        "level": request.level,
        "profile": request.profile,
        "created_at": datetime.now(),
    }

    logger.info(
        "创建文本处理任务成功: task_id=%s, text_length=%s, level=%s, profile=%s",
        task_id,
        len(text),
        request.level,
        request.profile,
    )

    return {
        "task_id": task_id
    }


# ==============================
# 生词本 API
# ==============================

@app.get("/api/vocabulary")
async def list_vocabulary(
    search: str = Query(default="", description="搜索关键词"),
    mastered: int | None = Query(default=None, description="已掌握筛选: 0/1"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0)
):
    items, total = vocab_db.list_vocabulary(
        search=search, mastered=mastered, limit=limit, offset=offset
    )
    return {"items": items, "total": total}


@app.patch("/api/vocabulary/{vocab_id}/master")
async def set_mastered(vocab_id: int, body: SetMasteredRequest):
    existing = vocab_db.get_vocab_by_id(vocab_id)
    if not existing:
        raise HTTPException(status_code=404, detail="生词不存在")
    vocab_db.set_mastered(vocab_id, body.mastered)
    return {"ok": True}


@app.delete("/api/vocabulary/{vocab_id}")
async def delete_vocabulary(vocab_id: int):
    existing = vocab_db.get_vocab_by_id(vocab_id)
    if not existing:
        raise HTTPException(status_code=404, detail="生词不存在")
    vocab_db.delete_vocabulary(vocab_id)
    return {"ok": True}


@app.post("/api/word-lookup")
async def word_lookup(request: WordLookupRequest):
    ensure_llm_services()
    result = await asyncio.to_thread(
        lookup_svc.lookup,
        request.word,
        request.sentence,
    )
    return result


@app.post("/api/vocabulary")
async def add_vocabulary(request: AddVocabRequest):
    vocab_id = vocab_db.upsert_vocabulary(
        request.word, request.translation, request.context
    )
    return {"id": vocab_id, "ok": True}


class MarkByWordRequest(BaseModel):
    word: str = Field(..., description="生词")
    mastered: bool = Field(..., description="是否已掌握")


@app.post("/api/vocabulary/mark-by-word")
async def mark_by_word(request: MarkByWordRequest):
    found = vocab_db.set_mastered_by_word(request.word, request.mastered)
    return {"ok": True, "found": found}


# ==============================
# 历史记录 API
# ==============================

@app.get("/api/history")
async def list_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    items, total = vocab_db.list_history(limit=limit, offset=offset)
    return {"items": items, "total": total}


@app.get("/api/history/{task_id}")
async def get_history(task_id: str):
    record = vocab_db.get_history(task_id)
    if not record:
        raise HTTPException(status_code=404, detail="历史记录不存在")
    return record


@app.delete("/api/history/{task_id}")
async def delete_history(task_id: str):
    existing = vocab_db.get_history(task_id)
    if not existing:
        raise HTTPException(status_code=404, detail="历史记录不存在")
    vocab_db.delete_history(task_id)
    return {"ok": True}


@app.get("/api/process-stream")
async def process_stream(task_id: str = Query(...)):
    """
    SSE 流式处理接口（前端通过 EventSource 连接）。

    流程：
    1. 从 SQLite 读取已掌握词汇，截取上限条数防止 prompt 过长
    2. 异步迭代 DocumentProcessor 的 chunk 并行处理流
    3. 每收到一个事件即检测 completed 并触发自动保存
    4. finally 块清理 process_tasks 缓存，避免内存堆积
    """

    task = process_tasks.get(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")

    text = task["text"]
    level = task.get("level", "intermediate")
    profile = task.get("profile", "general")
    ensure_llm_services()

    async def event_generator():
        try:
            # 从 SQLite 中读取已掌握词汇
            mastered_all = vocab_db.get_mastered_words()
            max_mastered = int(os.getenv("MAX_MASTERED_WORDS_IN_PROMPT", "300"))
            mastered_list = mastered_all[:max_mastered]

            async for event in doc_processor.process_chapter_stream(
                long_text=text,
                mastered_words=mastered_list,
                level=level,
                profile=profile,
            ):
                _maybe_save_completed(event, task_id, text)
                yield event

        except Exception as e:
            logger.exception(f"SSE 处理失败: {e}")

            # 即使出错，也尽量给前端返回一条 SSE 错误消息
            yield sse_event({
                        "type": "error",
                        "message": "后端处理失败，请稍后重试"
                            })

        finally:
            # 任务处理完成后清理缓存，避免内存越来越大
            process_tasks.pop(task_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

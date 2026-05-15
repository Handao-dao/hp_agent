import os
import uuid
import json
import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from hello_agents import HelloAgentsLLM
from hp_agent.agent1 import AnnotatorService
from hp_agent.sse_service import DocumentProcessor
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
llm = HelloAgentsLLM()
annotator_svc = AnnotatorService(llm)
doc_processor = DocumentProcessor(annotator_svc)
vocab_db = VocabDB(os.getenv("VOCAB_DB_PATH", "./data/harry_potter_vocab.db"))


# ==============================
# 请求模型
# ==============================
class CreateProcessTaskRequest(BaseModel):
    text: str = Field(..., description="需要处理的长文本")
    level: str = Field(default="intermediate", description="读者水平: beginner/intermediate/advanced")


class SetMasteredRequest(BaseModel):
    mastered: bool = Field(..., description="是否已掌握")


# ==============================
# 简单任务缓存
# 开发阶段可以先用内存字典
# 生产环境建议换成 Redis / 数据库
# ==============================
process_tasks: Dict[str, dict] = {}
TASK_EXPIRE_MINUTES = 30

def sse_event(payload: dict) -> str:
    """
    统一封装 SSE 数据格式。
    """
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _maybe_save_completed(event: str, task_id: str, original_text: str):
    """检测 SSE completed 事件并自动保存到 SQLite"""
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
    for v in total_vocab:
        vocab_db.upsert_vocabulary(
            v.get("word", ""), v.get("translation", ""), v.get("context", "")
        )
    vocab_db.save_history(task_id, original_text, annotated_text)
    logger.info(f"已保存历史记录: task_id={task_id}, vocab_count={len(total_vocab)}")


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

    
    task_id = str(uuid.uuid4())

    process_tasks[task_id] = {
        "text": text,
        "level": request.level,
        "created_at": datetime.now(),
    }

    logger.info(f"创建文本处理任务成功: task_id={task_id}, text_length={len(text)}, level={request.level}")

    return {
        "task_id": task_id
    }


# ==============================
# 生词本 API
# ==============================

@app.get("/api/vocabulary")
async def list_vocabulary(
    search: str = Query(default="", description="搜索关键词"),
    mastered: Optional[int] = Query(default=None, description="已掌握筛选: 0/1"),
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
    第二步：
    前端通过 EventSource 连接该接口。
    后端根据 task_id 找到文本，然后流式返回处理结果。
    """

    task = process_tasks.get(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")

    text = task["text"]
    level = task.get("level", "intermediate")

    async def event_generator():
        try:
            # 从 SQLite 中读取已掌握词汇
            mastered_all = vocab_db.get_mastered_words()
            max_mastered = int(os.getenv("MAX_MASTERED_WORDS_IN_PROMPT", "300"))
            mastered_list = mastered_all[:max_mastered]

            async for event in doc_processor.process_chapter_stream(
                long_text=text,
                mastered_words=mastered_list,
                level=level
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
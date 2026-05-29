import json

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from text_annotation_framework.engine import TextAnnotationEngine
from text_annotation_framework.llm import create_llm_client_from_env
from text_annotation_framework.profiles import default_profile_registry
from text_annotation_framework.streaming import StreamingAnnotationService

load_dotenv()

profile_registry = default_profile_registry()
# API 层只负责装配依赖；核心能力仍然在 engine/streaming 中。
engine = TextAnnotationEngine(
    llm=create_llm_client_from_env(),
    profiles=profile_registry,
)
streaming_service = StreamingAnnotationService(engine)

app = FastAPI(title="Text Annotation Framework")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnnotateRequest(BaseModel):
    """统一请求模型：text 是输入，profile 决定提取策略，options 留给调用方扩展。"""

    text: str = Field(..., max_length=500000)
    profile: str = "english_reading"
    options: dict = Field(default_factory=dict)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/profiles")
async def profiles():
    return {
        "profiles": [
            {
                "key": profile.key,
                "label": profile.label,
                "annotation_types": profile.annotation_types,
                "instructions": profile.instructions,
            }
            for profile in profile_registry.list_profiles()
        ]
    }


@app.post("/api/annotate")
async def annotate(request: AnnotateRequest):
    return engine.annotate(request.text, request.profile, request.options)


@app.post("/api/annotate-stream")
async def annotate_stream(request: AnnotateRequest):
    async def events():
        async for event in streaming_service.annotate_stream(
            request.text,
            request.profile,
            request.options,
        ):
            # 使用最简单的 SSE wire format，前端可以逐条解析 data 行。
            yield f"data: {json.dumps(event.model_dump(), ensure_ascii=False)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")

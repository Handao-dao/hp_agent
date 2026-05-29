import asyncio

from text_annotation_framework.engine import TextAnnotationEngine
from text_annotation_framework.llm import MockLLMClient
from text_annotation_framework.profiles import default_profile_registry
from text_annotation_framework.streaming import StreamingAnnotationService


def test_streaming_events_complete_in_order_shape():
    events = asyncio.run(_collect_events())

    assert events[0].type == "start"
    assert events[-1].type == "completed"
    assert events[-1].result is not None
    assert events[-1].result.annotations


async def _collect_events():
    engine = TextAnnotationEngine(MockLLMClient(), default_profile_registry())
    service = StreamingAnnotationService(engine)
    return [
        event
        async for event in service.annotate_stream(
            "The resilient framework recovered after a timeout.",
            "english_reading",
        )
    ]

import asyncio

from dotenv import load_dotenv
from hello_agents import HelloAgentsLLM

from hp_agent.agent1 import AnnotatorService
from hp_agent.sse_service import DocumentProcessor


async def run_stream():
    text = """
'How's yer brother Charlie?' Hagrid asked Ron. 'I liked him a lot - great with animals.'
"""

    mastered_words = ["hello", "apple"]

    llm = HelloAgentsLLM()
    annotator_svc = AnnotatorService(llm)
    doc_processor = DocumentProcessor(annotator_svc)

    async for event in doc_processor.process_chapter_stream(
        long_text=text,
        mastered_words=mastered_words,
    ):
        print(event)


def main():
    load_dotenv()
    asyncio.run(run_stream())


if __name__ == "__main__":
    main()

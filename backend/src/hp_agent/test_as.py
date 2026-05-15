from dotenv import load_dotenv
import asyncio

from hp_agent.agent1 import AnnotatorService
from hp_agent.sse_service import DocumentProcessor
from hello_agents import HelloAgentsLLM


def main():
    load_dotenv()

    llm = HelloAgentsLLM()
    annotator_svc = AnnotatorService(llm)
    doc_processor = DocumentProcessor(annotator_svc)

    async def main():
        text = """
‘How’s yer brother Charlie?’ Hagrid asked Ron. ‘I liked him a lot – great with animals.’
    """

        mastered_words = ["hello", "apple"]

        async for event in doc_processor.process_chapter_stream(
            long_text=text,
            mastered_words=mastered_words
        ):
            print(event)

    asyncio.run(main())


if __name__ == "__main__":
    main()
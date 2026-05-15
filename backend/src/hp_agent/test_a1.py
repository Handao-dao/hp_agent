from dotenv import load_dotenv

from hp_agent.agent1 import AnnotatorService
from hello_agents import HelloAgentsLLM


def main():
    load_dotenv()

    llm = HelloAgentsLLM()
    annotator_svc = AnnotatorService(llm)

    text = """
‘How’s yer brother Charlie?’ Hagrid asked Ron. ‘I liked him a lot – great with animals.’
"""

    mastered_words = ["hello", "apple"]

    result = annotator_svc.annotate_text(text, mastered_words)

    print("===== annotated_text =====")
    print(result.annotated_text)

    print("\n===== vocabulary =====")
    for item in result.vocabulary:
        print(item.word, item.translation, item.context)


if __name__ == "__main__":
    main()
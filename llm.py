import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from openai import APIConnectionError, OpenAI

load_dotenv()

MODEL = os.getenv("LLM_MODEL")

# Any OpenAI-compatible server works: Ollama locally, or a cloud provider.
client = OpenAI(
    base_url=os.getenv("LLM_BASE_URL"),
    api_key=os.getenv("LLM_API_KEY"),
    max_retries=5,   # retried with exponential backoff on 429, 5xx and dropped connections
    timeout=120,
)


def chat(messages, **options):
    """Send a list of messages to the model and return the full response."""
    return client.chat.completions.create(model=MODEL, messages=messages, **options)


def langchain_model():
    """Same model and settings, in the form LangChain expects."""
    return ChatOpenAI(
        model=MODEL,
        base_url=os.getenv("LLM_BASE_URL"),
        api_key=os.getenv("LLM_API_KEY"),
        temperature=0,
    )


if __name__ == "__main__":
    try:
        response = chat([{"role": "user", "content": "Define a supplier invoice in one sentence."}])
        print(response.choices[0].message.content)
        print("Input tokens:", response.usage.prompt_tokens)
        print("Output tokens:", response.usage.completion_tokens)
    except APIConnectionError:
        print("Model server unreachable: check that Ollama is running.")

import os

from langchain_ollama import ChatOllama


def get_chat_model(timeout: float | None = None) -> ChatOllama:
    return ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0,
        client_kwargs={"timeout": timeout} if timeout else {},
    )

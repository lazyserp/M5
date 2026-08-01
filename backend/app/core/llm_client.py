from typing import Iterator

import requests

class LocalLLMClient:
    """
    A REST client class to communicate with locally running Ollama instance.
    """
    def __init__(self,base_url: str = "http://localhost:11434",model_name: str = "qwen2.5-coder:1.5b",timeout_seconds: float = 30.0,) -> None:
        self.chat_url = f"{base_url.rstrip('/')}/api/chat"
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False
        }
        try:
            response = requests.post(self.chat_url, json=payload, timeout=self.timeout_seconds)
            response.raise_for_status()
            return response.json()["message"]["content"]
        except (KeyError, TypeError, requests.RequestException, ValueError) as error:
            raise RuntimeError("The local model service did not return a usable response.") from error

    def chat_stream(self, system_prompt: str, user_prompt: str) -> Iterator[str]:
        import json
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": True
        }
        try:
            response = requests.post(
                self.chat_url, json=payload, stream=True, timeout=self.timeout_seconds
            )
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    data = json.loads(line.decode("utf-8"))
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content
        except (ValueError, requests.RequestException) as error:
            raise RuntimeError("The local model service did not return a usable response.") from error

class LangChainGroqClient:
    """Groq client built with a LangChain prompt/model/parser chain."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "llama-3.3-70b-versatile",
        timeout_seconds: float = 60.0,
    ) -> None:
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import PromptTemplate
        from langchain_groq import ChatGroq

        self.llm = ChatGroq(
            model=model_name,
            groq_api_key=api_key,
        )
        self.prompt = PromptTemplate.from_template(
            "{system_prompt}\n\nUser question: {user_prompt}"
        )
        self.chain = self.prompt | self.llm | StrOutputParser()

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        try:
            return str(
                self.chain.invoke(
                    {"system_prompt": system_prompt, "user_prompt": user_prompt}
                )
            )
        except Exception as error:
            raise RuntimeError(f"Groq model service error: {error}") from error

    def chat_stream(self, system_prompt: str, user_prompt: str) -> Iterator[str]:
        try:
            yield from self.chain.stream(
                {"system_prompt": system_prompt, "user_prompt": user_prompt}
            )
        except Exception as error:
            raise RuntimeError(f"Groq model service error: {error}") from error

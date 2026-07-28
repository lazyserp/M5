from typing import Iterator

import requests

class LocalLLMClient:
    """
    A REST client class to communicate with locally running Ollama instance.
    This encapsulates the network HTTP POST call so we can call the model in 
    a clean, single-line method elsewhere in our application.
    """
    def __init__(self, base_url: str, model_name: str, timeout_seconds: float = 30.0) -> None:
        self.chat_url = f"{base_url.rstrip('/')}/api/chat"
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        """
        Sends a query to the local model and returns the text response.
        
        Parameters:
        - system_prompt (str): Instructions guiding the behavior/personality of the AI.
        - user_prompt (str): The actual question or code logic task from the user.
        """
        # The payload is the JSON structured data we send to the Ollama server.
        payload = {
            # specify local CPU-optimized model (Qwen 2.5 Coder 1.5B)
            "model": self.model_name,
            # structure the conversation history using standard roles:
            # - 'system': Sets the context (e.g. "You are a code parser")
            # - 'user': The query inputs
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            # 'stream': False tells Ollama to wait until the full answer is generated
            # before returning it, rather than sending it back word-by-word (streaming).
            "stream": False
        }
        
        # use the requests library to send an HTTP POST request with our payload.
        try:
            response = requests.post(self.chat_url, json=payload, timeout=self.timeout_seconds)
            response.raise_for_status()
            return response.json()["message"]["content"]
        except (KeyError, TypeError, requests.RequestException, ValueError) as error:
            raise RuntimeError("The local model service did not return a usable response.") from error

    def chat_stream(self, system_prompt: str, user_prompt: str) -> Iterator[str]:
        """
        Streams response tokens live from Ollama as a generator.
        """
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

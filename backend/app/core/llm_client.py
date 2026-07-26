import requests
from typing import Dict, Any

class LocalLLMClient:
    """
    A REST client class to communicate with our locally running Ollama instance.
    This encapsulates the network HTTP POST call so we can call the model in 
    a clean, single-line method elsewhere in our application.
    """
    def __init__(self, base_url: str = None, model_name: str = None):
        import os
        env_host = os.getenv("OLLAMA_HOST")
        if env_host and "ollama" in env_host:
            base_url = base_url or env_host
        else:
            base_url = base_url or os.getenv("OLLAMA_HOST", "http://localhost:11435")
            
        self.chat_url = f"{base_url}/api/chat"
        self.model_name = model_name or os.getenv("OLLAMA_MODEL", "qwen2.5-coder:1.5b")

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        """
        Sends a query to the local model and returns the text response.
        
        Parameters:
        - system_prompt (str): Instructions guiding the behavior/personality of the AI.
        - user_prompt (str): The actual question or code logic task from the user.
        """
        # The payload is the JSON structured data we send to the Ollama server.
        payload = {
            # specify our local CPU-optimized model (Qwen 2.5 Coder 1.5B)
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
        response = requests.post(self.chat_url, json=payload)
        
        # raise_for_status() immediately throws an error if the server is offline
        # or if Ollama returns an error code (e.g., model not found / 500 server error).
        response.raise_for_status()
        
        # convert the raw server response into a Python dictionary (JSON)
        # and pull the generated message text content.
        response_data = response.json()
        return response_data["message"]["content"]

    def chat_stream(self, system_prompt: str, user_prompt: str):
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
        response = requests.post(self.chat_url, json=payload, stream=True)
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                data = json.loads(line.decode("utf-8"))
                content = data.get("message", {}).get("content", "")
                if content:
                    yield content

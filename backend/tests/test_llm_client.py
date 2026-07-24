import sys
import os

# We append the parent path (backend/ folder) to our Python search path (sys.path).
# This tells Python where to look when we write "from app.core.llm_client import ..."
# otherwise Python would throw a ModuleNotFoundError.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# pyrefly: ignore [missing-import]
from app.core.llm_client import LocalLLMClient

def test_client():
    print("[+] Initializing LocalLLMClient...")
    # Instantiate our newly created HTTP client class
    client = LocalLLMClient()
    
    system_prompt = "You are a helpful programming assistant. Keep your response very short (under 10 words)."
    user_prompt = "Say hello!"
    
    print(f"[+] Sending request: '{user_prompt}'")
    try:
        # Call the chat function which triggers requests.post
        response = client.chat(system_prompt, user_prompt)
        print(f"[+] Response from local model: '{response}'")
    except Exception as e:
        # If the server is offline or fails, print the error details
        print(f"[ERROR] Failed to communicate with local model: {e}")

if __name__ == "__main__":
    test_client()

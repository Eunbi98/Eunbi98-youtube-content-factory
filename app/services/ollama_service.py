import os
import httpx
from dotenv import load_dotenv

load_dotenv()


class OllamaService:

    def __init__(self):
        self.model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
        self.url = "http://localhost:11434/api/generate"

    def generate(self, prompt: str) -> str:
        try:
            response = httpx.post(
                self.url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120
            )

            response.raise_for_status()

            data = response.json()

            return data.get("response", "").strip()

        except Exception as e:
            print("Ollama 호출 실패")
            print(e)
            return ""
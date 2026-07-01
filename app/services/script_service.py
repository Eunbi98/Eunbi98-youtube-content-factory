from app.services.ollama_service import OllamaService


class ScriptService:

    def __init__(self):
        self.llm = OllamaService()

    def create_script(self, article) -> str:
        base_text = article.summary or article.cleaned_content or article.content

        if not base_text:
            return ""

        prompt = f"""
You are a YouTube Shorts script writer.

Create a 30-second Korean news shorts script.

Rules:
- Korean only.
- 5 short lines.
- Line 1 must be a strong hook.
- Lines 2-4 explain the news simply.
- Line 5 explains why viewers should care.
- Do not use markdown.
- Do not add facts not included in the source.

Source:
{base_text[:1500]}

Script:
"""

        return self.llm.generate(prompt)
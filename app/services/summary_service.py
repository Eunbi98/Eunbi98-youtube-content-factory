from app.services.ollama_service import OllamaService


class SummaryService:

    def __init__(self):
        self.llm = OllamaService()

    def summarize(self, article) -> str:
        content = article.cleaned_content or article.content

        if not content:
            return ""

        prompt = f"""
You are a strict Korean translator and news summarizer.

Task:
Read the English article and write a Korean summary.

Output rules:
- Korean only.
- Exactly 3 bullet points.
- Each bullet point must be one short sentence.
- Do not use Japanese, Chinese, Vietnamese, Thai, or mixed language.
- Do not write an introduction.
- Do not repeat the title.
- Do not include markdown bold.

Article:
{content[:1800]}

Output:
- 
"""

        return self.llm.generate(prompt)
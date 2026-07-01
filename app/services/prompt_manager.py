from config.settings import PROMPT_DIR


class PromptManager:

    def __init__(self, prompt_dir=None):
        self.prompt_dir = prompt_dir or PROMPT_DIR

    def load(self, prompt_name: str) -> str:
        prompt_path = self.prompt_dir / prompt_name

        if not prompt_path.exists():
            raise FileNotFoundError(
                f"프롬프트 파일을 찾을 수 없습니다: {prompt_path}"
            )

        return prompt_path.read_text(encoding="utf-8")
import json

from config.settings import TEMPLATE_DIR


class TemplateLoader:
    def __init__(self):
        self.template_dir = TEMPLATE_DIR

    def load(self, template_name: str) -> dict:
        template_path = self.template_dir / f"{template_name}.json"

        if not template_path.exists():
            raise FileNotFoundError(
                f"템플릿 파일을 찾을 수 없습니다: {template_path}"
            )

        with open(template_path, "r", encoding="utf-8") as f:
            return json.load(f)
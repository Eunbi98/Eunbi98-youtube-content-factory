from pathlib import Path


class VideoAssets:
    def __init__(self):
        self.font_path = self._find_korean_font()

    def _find_korean_font(self) -> str | None:
        candidates = [
            Path("C:/Windows/Fonts/malgunbd.ttf"),
            Path("C:/Windows/Fonts/malgun.ttf"),
            Path("C:/Windows/Fonts/NanumGothicBold.ttf"),
            Path("C:/Windows/Fonts/NotoSansKR-Bold.ttf"),
        ]

        for path in candidates:
            if path.exists():
                return str(path)

        return None
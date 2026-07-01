import asyncio
from pathlib import Path

import edge_tts


class AudioService:

    def __init__(self):

        self.output_dir = Path("output/audio")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 한국어 여성 음성
        self.voice = "ko-KR-SunHiNeural"

    async def _create_audio(self, text: str, output_path: str):

        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate="+0%"
        )

        await communicate.save(output_path)

    def create_audio(self, article):

        text = article.script

        if not text:
            return None

        filename = "news.mp3"

        output_path = self.output_dir / filename

        asyncio.run(
            self._create_audio(
                text,
                str(output_path)
            )
        )

        return str(output_path)
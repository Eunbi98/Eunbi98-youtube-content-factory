import asyncio

import edge_tts

from app.services.final_output_guard import FinalOutputGuard
from config.settings import AUDIO_DIR, DEFAULT_AUDIO_FILENAME, TTS_VOICE


class AudioService:
    def __init__(self):
        self.output_dir = AUDIO_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.voice = TTS_VOICE
        self.final_output_guard = FinalOutputGuard()

    async def _create_audio(self, text: str, output_path: str):
        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate="+0%"
        )

        await communicate.save(output_path)

    def create_audio(self, article):
        diagnostics = self.final_output_guard.enforce_article(article)
        text = article.script

        if not text:
            return None

        print("\nTTS Korean Guard")
        print(f"final_tts_preview: {diagnostics['final_tts_preview']}")
        print(f"korean_ratio: {diagnostics['korean_ratio']:.2f}")
        print(f"english_ratio: {diagnostics['english_ratio']:.2f}")

        output_path = self.output_dir / DEFAULT_AUDIO_FILENAME

        asyncio.run(
            self._create_audio(
                text=text,
                output_path=str(output_path)
            )
        )

        return str(output_path)

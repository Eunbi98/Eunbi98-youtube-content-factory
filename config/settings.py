from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

OUTPUT_DIR = BASE_DIR / "output"
PROMPT_DIR = BASE_DIR / "prompts"
SOURCE_DIR = BASE_DIR / "sources"

IMAGE_DIR = OUTPUT_DIR / "images"
AUDIO_DIR = OUTPUT_DIR / "audio"
VIDEO_DIR = OUTPUT_DIR / "video"
SUBTITLE_DIR = OUTPUT_DIR / "subtitles"

SOURCE_FILE = SOURCE_DIR / "interesting_sources.json"

MAX_CONTENT_LENGTH = 2500

CANDIDATE_LIMIT = 5
AI_TARGET_COUNT = 3
PROCESS_LIMIT = 10

CHANNEL_NAME = "세계의 신기한 이야기"
LANGUAGE = "ko"

OLLAMA_MODEL = "gemma2:2b"
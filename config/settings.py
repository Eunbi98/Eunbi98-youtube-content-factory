from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
PROMPT_DIR = BASE_DIR / "prompts"
SOURCE_DIR = BASE_DIR / "sources"
TEMPLATE_DIR = BASE_DIR / "templates"

IMAGE_DIR = OUTPUT_DIR / "images"
AUDIO_DIR = OUTPUT_DIR / "audio"
VIDEO_DIR = OUTPUT_DIR / "video"
SUBTITLE_DIR = OUTPUT_DIR / "subtitles"

DATABASE_PATH = DATA_DIR / "articles.db"
SOURCE_FILE = SOURCE_DIR / "interesting_sources.json"

MAX_CONTENT_LENGTH = 2500

PROCESS_LIMIT = 10
CANDIDATE_LIMIT = 5
AI_TARGET_COUNT = 3

CHANNEL_NAME = "해외 흥미 콘텐츠 이야기"
LANGUAGE = "ko"

OLLAMA_MODEL = "gemma2:2b"

ENABLE_AUDIO = True
ENABLE_SUBTITLE = True
ENABLE_VIDEO = True
ENABLE_IMAGE_DOWNLOAD = True

DEFAULT_AUDIO_FILENAME = "news.mp3"
DEFAULT_SUBTITLE_FILENAME = "news.srt"
DEFAULT_VIDEO_FILENAME = "news.mp4"
DEFAULT_IMAGE_FILENAME = "news.jpg"

TTS_VOICE = "ko-KR-SunHiNeural"

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30

VIDEO_TEMPLATE_NAME = "news_dark"
VIDEO_FILENAME_PREFIX = "shorts"
VIDEO_REMOVE_TEMP_FILES = True


def ensure_directories():
    for path in [
        DATA_DIR,
        OUTPUT_DIR,
        IMAGE_DIR,
        AUDIO_DIR,
        VIDEO_DIR,
        SUBTITLE_DIR,
        PROMPT_DIR,
        SOURCE_DIR,
        TEMPLATE_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)
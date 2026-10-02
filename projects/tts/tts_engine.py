from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import edge_tts

from tts_config import (
    TTSConfig,
    TTSConfigError,
)


DEFAULT_TEST_TEXT: Final[str] = (
    "사람이 절대 들어갈 수 없는 장소가 "
    "실제로 존재한다는 사실, 알고 계셨나요?"
)


class TTSEngineError(RuntimeError):
    """TTS 음성 생성 과정에서 발생하는 예외입니다."""


@dataclass(
    frozen=True,
    slots=True,
)
class TTSWordBoundary:
    text: str
    offset_seconds: float
    duration_seconds: float
    end_seconds: float

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "text": self.text,
            "offset": self.offset_seconds,
            "duration": self.duration_seconds,
            "end": self.end_seconds,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class TTSGenerationResult:
    scene_id: str
    text: str
    output_path: Path
    metadata_path: Path
    voice: str
    rate: str
    volume: str
    pitch: str
    file_size_bytes: int
    word_boundaries: tuple[
        TTSWordBoundary,
        ...,
    ]

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "scene_id": self.scene_id,
            "text": self.text,
            "output_path": str(
                self.output_path
            ),
            "metadata_path": str(
                self.metadata_path
            ),
            "voice": self.voice,
            "rate": self.rate,
            "volume": self.volume,
            "pitch": self.pitch,
            "file_size_bytes": (
                self.file_size_bytes
            ),
            "word_boundary_count": len(
                self.word_boundaries
            ),
            "word_boundaries": [
                boundary.to_dict()
                for boundary
                in self.word_boundaries
            ],
        }


class EdgeTTSEngine:
    """
    Microsoft Edge TTS 음성 생성 엔진입니다.

    장면별 MP3와 함께 단어별 발화 시간 정보가 담긴
    timing.json 파일을 생성합니다.
    """

    def __init__(
        self,
        config: TTSConfig | None = None,
    ) -> None:
        self.config = (
            config
            if config is not None
            else TTSConfig.from_environment()
        )

        if self.config.provider != "edge":
            raise TTSEngineError(
                "EdgeTTSEngine은 provider가 "
                "'edge'일 때만 사용할 수 있습니다."
            )

    async def generate(
        self,
        *,
        scene_id: str,
        text: str,
        output_dir: Path,
    ) -> TTSGenerationResult:
        normalized_scene_id = (
            self._normalize_scene_id(
                scene_id
            )
        )

        normalized_text = (
            self._normalize_text(
                text
            )
        )

        output_dir = output_dir.resolve()

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path = (
            self.config.build_scene_path(
                output_dir=output_dir,
                scene_id=normalized_scene_id,
            )
        )

        metadata_path = (
            self._build_metadata_path(
                output_dir=output_dir,
                scene_id=normalized_scene_id,
            )
        )

        cache_is_valid = (
            output_path.exists()
            and output_path.stat().st_size > 0
            and metadata_path.exists()
            and metadata_path.stat().st_size > 0
        )

        if (
            cache_is_valid
            and not self.config.overwrite
        ):
            word_boundaries = (
                self._load_word_boundaries(
                    metadata_path
                )
            )

            print(
                "[건너뜀] 기존 TTS 및 "
                "타이밍 파일 사용: "
                f"{output_path}"
            )

            return TTSGenerationResult(
                scene_id=(
                    normalized_scene_id
                ),
                text=normalized_text,
                output_path=output_path,
                metadata_path=metadata_path,
                voice=self.config.voice,
                rate=self.config.rate,
                volume=self.config.volume,
                pitch=self.config.pitch,
                file_size_bytes=(
                    output_path
                    .stat()
                    .st_size
                ),
                word_boundaries=(
                    word_boundaries
                ),
            )

        if output_path.exists():
            output_path.unlink()

        if metadata_path.exists():
            metadata_path.unlink()

        temporary_audio_path = (
            output_path.with_suffix(
                f"{output_path.suffix}.part"
            )
        )

        temporary_metadata_path = (
            metadata_path.with_suffix(
                f"{metadata_path.suffix}.part"
            )
        )

        for temporary_path in (
            temporary_audio_path,
            temporary_metadata_path,
        ):
            if temporary_path.exists():
                temporary_path.unlink()

        try:
            communicate = edge_tts.Communicate(
                text=normalized_text,
                voice=self.config.voice,
                rate=self.config.rate,
                volume=self.config.volume,
                pitch=self.config.pitch,

                # 단어별 시작 시각을 받습니다.
                boundary="WordBoundary",
            )

            await communicate.save(
                str(temporary_audio_path),
                str(temporary_metadata_path),
            )

            self._validate_generated_file(
                temporary_audio_path
            )

            word_boundaries = (
                self._convert_metadata_file(
                    source_path=(
                        temporary_metadata_path
                    ),
                    destination_path=(
                        metadata_path
                    ),
                    scene_id=(
                        normalized_scene_id
                    ),
                    narration=(
                        normalized_text
                    ),
                )
            )

            temporary_audio_path.replace(
                output_path
            )

            if (
                temporary_metadata_path
                .exists()
            ):
                temporary_metadata_path.unlink()

        except Exception as exc:
            for temporary_path in (
                temporary_audio_path,
                temporary_metadata_path,
            ):
                if temporary_path.exists():
                    temporary_path.unlink()

            if metadata_path.exists():
                metadata_path.unlink()

            raise TTSEngineError(
                "TTS 음성 및 발화 타이밍 "
                "생성에 실패했습니다.\n"
                f"scene_id: "
                f"{normalized_scene_id}\n"
                f"voice: "
                f"{self.config.voice}\n"
                f"output: "
                f"{output_path}\n"
                f"원인: {exc}"
            ) from exc

        file_size = (
            output_path
            .stat()
            .st_size
        )

        return TTSGenerationResult(
            scene_id=normalized_scene_id,
            text=normalized_text,
            output_path=output_path,
            metadata_path=metadata_path,
            voice=self.config.voice,
            rate=self.config.rate,
            volume=self.config.volume,
            pitch=self.config.pitch,
            file_size_bytes=file_size,
            word_boundaries=word_boundaries,
        )

    def generate_sync(
        self,
        *,
        scene_id: str,
        text: str,
        output_dir: Path,
    ) -> TTSGenerationResult:
        """
        일반 Python 코드에서 사용하는 동기 실행 함수입니다.
        """

        try:
            asyncio.get_running_loop()

        except RuntimeError:
            return asyncio.run(
                self.generate(
                    scene_id=scene_id,
                    text=text,
                    output_dir=output_dir,
                )
            )

        raise TTSEngineError(
            "이미 실행 중인 asyncio 이벤트 루프가 "
            "있습니다. 비동기 환경에서는 "
            "await engine.generate(...)를 "
            "사용하세요."
        )

    @staticmethod
    def _build_metadata_path(
        *,
        output_dir: Path,
        scene_id: str,
    ) -> Path:
        return (
            output_dir
            / f"{scene_id}.timing.json"
        )

    @staticmethod
    def _convert_ticks_to_seconds(
        ticks: float,
    ) -> float:
        """
        Edge TTS 시간 단위는 100나노초 tick입니다.

        10,000,000 tick = 1초
        """

        return round(
            float(ticks)
            / 10_000_000,
            3,
        )

    def _convert_metadata_file(
        self,
        *,
        source_path: Path,
        destination_path: Path,
        scene_id: str,
        narration: str,
    ) -> tuple[
        TTSWordBoundary,
        ...,
    ]:
        if not source_path.exists():
            raise TTSEngineError(
                "TTS 발화 메타데이터 파일이 "
                "생성되지 않았습니다:\n"
                f"{source_path}"
            )

        boundaries: list[
            TTSWordBoundary
        ] = []

        try:
            lines = source_path.read_text(
                encoding="utf-8"
            ).splitlines()

        except OSError as exc:
            raise TTSEngineError(
                "TTS 발화 메타데이터를 "
                "읽지 못했습니다.\n"
                f"파일: {source_path}\n"
                f"원인: {exc}"
            ) from exc

        for line_number, line in enumerate(
            lines,
            start=1,
        ):
            normalized_line = line.strip()

            if not normalized_line:
                continue

            try:
                raw_data = json.loads(
                    normalized_line
                )

            except json.JSONDecodeError as exc:
                raise TTSEngineError(
                    "TTS 발화 메타데이터 JSON이 "
                    "올바르지 않습니다.\n"
                    f"파일: {source_path}\n"
                    f"줄: {line_number}\n"
                    f"원인: {exc}"
                ) from exc

            if not isinstance(
                raw_data,
                dict,
            ):
                continue

            boundary_type = raw_data.get(
                "type"
            )

            if (
                boundary_type
                != "WordBoundary"
            ):
                continue

            raw_text = raw_data.get(
                "text"
            )
            raw_offset = raw_data.get(
                "offset"
            )
            raw_duration = raw_data.get(
                "duration"
            )

            if not isinstance(
                raw_text,
                str,
            ):
                continue

            if not isinstance(
                raw_offset,
                (int, float),
            ):
                continue

            if not isinstance(
                raw_duration,
                (int, float),
            ):
                continue

            text = raw_text.strip()

            if not text:
                continue

            offset_seconds = (
                self
                ._convert_ticks_to_seconds(
                    raw_offset
                )
            )

            duration_seconds = (
                self
                ._convert_ticks_to_seconds(
                    raw_duration
                )
            )

            end_seconds = round(
                offset_seconds
                + duration_seconds,
                3,
            )

            boundaries.append(
                TTSWordBoundary(
                    text=text,
                    offset_seconds=(
                        offset_seconds
                    ),
                    duration_seconds=(
                        duration_seconds
                    ),
                    end_seconds=end_seconds,
                )
            )

        if not boundaries:
            raise TTSEngineError(
                "단어별 TTS 타이밍 정보가 "
                "생성되지 않았습니다.\n"
                f"파일: {source_path}"
            )

        payload = {
            "version": "1.0",
            "sceneId": scene_id,
            "narration": narration,
            "voice": self.config.voice,
            "rate": self.config.rate,
            "volume": self.config.volume,
            "pitch": self.config.pitch,
            "wordCount": len(
                boundaries
            ),
            "words": [
                boundary.to_dict()
                for boundary
                in boundaries
            ],
        }

        try:
            destination_path.write_text(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

        except OSError as exc:
            raise TTSEngineError(
                "정리된 TTS 타이밍 파일을 "
                "저장하지 못했습니다.\n"
                f"파일: {destination_path}\n"
                f"원인: {exc}"
            ) from exc

        return tuple(boundaries)

    @staticmethod
    def _load_word_boundaries(
        metadata_path: Path,
    ) -> tuple[
        TTSWordBoundary,
        ...,
    ]:
        try:
            raw_data = json.loads(
                metadata_path.read_text(
                    encoding="utf-8"
                )
            )

        except (
            OSError,
            json.JSONDecodeError,
        ) as exc:
            raise TTSEngineError(
                "기존 TTS 타이밍 파일을 "
                "읽지 못했습니다.\n"
                f"파일: {metadata_path}\n"
                f"원인: {exc}"
            ) from exc

        if not isinstance(
            raw_data,
            dict,
        ):
            raise TTSEngineError(
                "TTS 타이밍 파일의 "
                "최상위 데이터가 객체가 아닙니다."
            )

        raw_words = raw_data.get(
            "words"
        )

        if not isinstance(
            raw_words,
            list,
        ):
            raise TTSEngineError(
                "TTS 타이밍 파일에 "
                "words 배열이 없습니다."
            )

        boundaries: list[
            TTSWordBoundary
        ] = []

        for raw_word in raw_words:
            if not isinstance(
                raw_word,
                dict,
            ):
                continue

            text = raw_word.get(
                "text"
            )
            offset = raw_word.get(
                "offset"
            )
            duration = raw_word.get(
                "duration"
            )
            end = raw_word.get(
                "end"
            )

            if not isinstance(
                text,
                str,
            ):
                continue

            if not isinstance(
                offset,
                (int, float),
            ):
                continue

            if not isinstance(
                duration,
                (int, float),
            ):
                continue

            if not isinstance(
                end,
                (int, float),
            ):
                end = (
                    float(offset)
                    + float(duration)
                )

            boundaries.append(
                TTSWordBoundary(
                    text=text,
                    offset_seconds=round(
                        float(offset),
                        3,
                    ),
                    duration_seconds=round(
                        float(duration),
                        3,
                    ),
                    end_seconds=round(
                        float(end),
                        3,
                    ),
                )
            )

        if not boundaries:
            raise TTSEngineError(
                "기존 TTS 타이밍 파일에 "
                "사용 가능한 단어 정보가 없습니다:\n"
                f"{metadata_path}"
            )

        return tuple(boundaries)

    @staticmethod
    def _normalize_scene_id(
        scene_id: str,
    ) -> str:
        normalized = scene_id.strip()

        if not normalized:
            raise TTSEngineError(
                "scene_id가 비어 있습니다."
            )

        invalid_characters = {
            "<",
            ">",
            ":",
            '"',
            "/",
            "\\",
            "|",
            "?",
            "*",
        }

        found_invalid = sorted(
            character
            for character
            in invalid_characters
            if character in normalized
        )

        if found_invalid:
            raise TTSEngineError(
                "scene_id에 파일명으로 사용할 수 "
                "없는 문자가 포함되어 있습니다: "
                + ", ".join(
                    found_invalid
                )
            )

        return normalized

    @staticmethod
    def _normalize_text(
        text: str,
    ) -> str:
        normalized = " ".join(
            text
            .replace("\r", " ")
            .replace("\n", " ")
            .split()
        )

        if not normalized:
            raise TTSEngineError(
                "TTS로 변환할 문장이 "
                "비어 있습니다."
            )

        if len(normalized) > 5000:
            raise TTSEngineError(
                "한 장면의 TTS 문장은 "
                "5000자를 초과할 수 없습니다."
            )

        return normalized

    @staticmethod
    def _validate_generated_file(
        output_path: Path,
    ) -> None:
        if not output_path.exists():
            raise TTSEngineError(
                "TTS 출력 파일이 "
                "생성되지 않았습니다: "
                f"{output_path}"
            )

        file_size = (
            output_path
            .stat()
            .st_size
        )

        if file_size <= 0:
            raise TTSEngineError(
                "생성된 TTS 파일의 "
                "크기가 0입니다: "
                f"{output_path}"
            )


def build_argument_parser(
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "YouTube Content Factory "
            "Edge TTS 및 단어 타이밍 테스트"
        )
    )

    parser.add_argument(
        "--episode",
        default="ep008",
        help=(
            "에피소드 ID입니다. "
            "기본값: ep008"
        ),
    )

    parser.add_argument(
        "--scene-id",
        default="scene_001",
        help=(
            "장면 ID입니다. "
            "기본값: scene_001"
        ),
    )

    parser.add_argument(
        "--text",
        default=DEFAULT_TEST_TEXT,
        help=(
            "음성과 타이밍을 생성할 "
            "문장입니다."
        ),
    )

    parser.add_argument(
        "--output-dir",
        default=None,
        help=(
            "TTS 저장 폴더입니다. 생략하면 "
            "projects/episodes/{episode}/audio를 "
            "사용합니다."
        ),
    )

    return parser


def resolve_output_dir(
    *,
    episode: str,
    output_dir_argument: str | None,
) -> Path:
    if output_dir_argument:
        return Path(
            output_dir_argument
        )

    project_root = (
        Path(__file__)
        .resolve()
        .parents[2]
    )

    return (
        project_root
        / "projects"
        / "episodes"
        / episode
        / "audio"
    )


def print_result(
    result: TTSGenerationResult,
) -> None:
    print("=" * 62)
    print(
        " YouTube Content Factory "
        "TTS Word Timing"
    )
    print("=" * 62)
    print(
        f"{'scene_id':>18}: "
        f"{result.scene_id}"
    )
    print(
        f"{'voice':>18}: "
        f"{result.voice}"
    )
    print(
        f"{'rate':>18}: "
        f"{result.rate}"
    )
    print(
        f"{'file_size':>18}: "
        f"{result.file_size_bytes:,} bytes"
    )
    print(
        f"{'word_count':>18}: "
        f"{len(result.word_boundaries)}"
    )
    print(
        f"{'audio':>18}: "
        f"{result.output_path}"
    )
    print(
        f"{'timing':>18}: "
        f"{result.metadata_path}"
    )
    print("-" * 62)

    for boundary in (
        result.word_boundaries
    ):
        print(
            f"{boundary.offset_seconds:>7.3f}s "
            f"~ {boundary.end_seconds:>7.3f}s "
            f"| {boundary.text}"
        )

    print("-" * 62)
    print(
        "[성공] TTS 음성 및 "
        "단어 타이밍 생성 완료"
    )


def main() -> int:
    parser = build_argument_parser()
    arguments = parser.parse_args()

    try:
        config = (
            TTSConfig.from_environment()
        )

        engine = EdgeTTSEngine(
            config=config
        )

        output_dir = resolve_output_dir(
            episode=arguments.episode,
            output_dir_argument=(
                arguments.output_dir
            ),
        )

        result = engine.generate_sync(
            scene_id=arguments.scene_id,
            text=arguments.text,
            output_dir=output_dir,
        )

    except (
        TTSConfigError,
        TTSEngineError,
    ) as exc:
        print(
            f"[실패] {exc}",
            file=sys.stderr,
        )
        return 1

    print_result(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())